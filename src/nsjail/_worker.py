"""Worker process for jailed Python execution.

This module runs inside the nsjail sandbox. It reads a serialized callable
and arguments from an input file, executes the function, and writes the
serialized result (or exception) to an output file.

Usage inside nsjail:
    python -m nsjail._worker <io_dir> [output_format]

Trust model:
    * INPUT (``input.pkl``) flows parent -> jail. The parent is trusted and
      must be able to send arbitrary callables, so it is pickled. Unpickling
      it inside the jail cannot harm the parent.
    * OUTPUT flows jail -> parent. The jailed process is the *untrusted*
      party, so its output must never be able to execute code in the parent.
      By default the worker writes a non-executing JSON document
      (``output.json``). The ``pickle`` output format is opt-in and UNSAFE:
      it must only be selected when the caller fully trusts the jailed code
      (see ``jail_call(..., unsafe_pickle_output=True)``).
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

DEFAULT_OUTPUT_FORMAT = "json"


def _get_serializer():
    """Get the best available serializer for the *input* channel."""
    try:
        import cloudpickle
        return cloudpickle
    except ImportError:
        import pickle
        return pickle


def _error_dict(exc: BaseException) -> dict:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }


def _write_pickle_output(output_path: Path, is_error: bool, payload) -> None:
    """UNSAFE output path: pickle the result for a fully-trusted jail.

    Selected only via ``output_format == "pickle"``. The parent will unpickle
    this, so it must never be used for untrusted jailed code.
    """
    pkl = _get_serializer()
    with open(output_path, "wb") as f:
        pkl.dump((is_error, payload), f)


def _write_json_output(output_path: Path, document: dict) -> None:
    with open(output_path, "w") as f:
        json.dump(document, f)


def run_worker(io_dir: Path, output_format: str = DEFAULT_OUTPUT_FORMAT) -> None:
    """Execute the serialized function from ``io_dir/input.pkl``.

    In the default (``json``) mode, writes a non-executing JSON document to
    ``io_dir/output.json``. In the opt-in (``pickle``) mode, writes
    ``io_dir/output.pkl`` (UNSAFE for untrusted code).
    """
    pkl = _get_serializer()

    input_path = io_dir / "input.pkl"
    with open(input_path, "rb") as f:
        func, args, kwargs = pkl.load(f)

    try:
        result = func(*args, **kwargs)
        error = None
    except BaseException as e:  # noqa: BLE001 - report any failure to parent
        result = None
        error = _error_dict(e)

    if output_format == "pickle":
        output_path = io_dir / "output.pkl"
        if error is not None:
            _write_pickle_output(output_path, True, error)
        else:
            _write_pickle_output(output_path, False, result)
        return

    # Default: safe, non-executing JSON transport.
    output_path = io_dir / "output.json"
    if error is not None:
        _write_json_output(output_path, {"ok": False, "error": error})
        return

    try:
        json.dumps(result)
    except (TypeError, ValueError) as e:
        _write_json_output(
            output_path,
            {
                "ok": False,
                "error": {
                    "type": "UnserializableResult",
                    "message": (
                        f"Jailed function returned a value that is not "
                        f"JSON-serializable ({type(result).__name__}): {e}. "
                        f"To receive rich Python objects, opt in with "
                        f"jail_call(..., unsafe_pickle_output=True) -- but note "
                        f"that unpickles jail-controlled bytes in the parent "
                        f"and is only safe for fully-trusted jailed code."
                    ),
                    "traceback": "",
                },
            },
        )
        return

    _write_json_output(output_path, {"ok": True, "value": result})


def main() -> None:
    """Entry point when run as ``python -m nsjail._worker <io_dir> [format]``."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m nsjail._worker <io_dir> [output_format]",
            file=sys.stderr,
        )
        sys.exit(1)

    io_dir = Path(sys.argv[1])
    output_format = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_FORMAT
    run_worker(io_dir, output_format)


if __name__ == "__main__":
    main()
