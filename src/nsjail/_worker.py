"""Worker process for jailed Python execution.

This module runs inside the nsjail sandbox. It reads a serialized callable
and arguments from an input file, executes the function, and writes the
serialized result (or exception) to an output file.

Usage inside nsjail:
    python -m nsjail._worker <io_dir>

Security note: Uses pickle for serialization between parent and child
processes within the same trust domain (like multiprocessing). The sandbox
is the security boundary, not pickle.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _get_serializer():
    """Get the best available serializer (cloudpickle > pickle)."""
    try:
        import cloudpickle
        return cloudpickle
    except ImportError:
        import pickle
        return pickle


def run_worker(io_dir: Path) -> None:
    """Execute the serialized function from io_dir/input.pkl.

    Writes (is_error, result_or_exception) to io_dir/output.pkl.
    """
    pkl = _get_serializer()

    input_path = io_dir / "input.pkl"
    output_path = io_dir / "output.pkl"

    with open(input_path, "rb") as f:
        func, args, kwargs = pkl.load(f)

    try:
        result = func(*args, **kwargs)
        payload = (False, result)
    except BaseException as e:
        payload = (True, e)

    with open(output_path, "wb") as f:
        pkl.dump(payload, f)


def main() -> None:
    """Entry point when run as python -m nsjail._worker <io_dir>."""
    if len(sys.argv) < 2:
        print("Usage: python -m nsjail._worker <io_dir>", file=sys.stderr)
        sys.exit(1)

    io_dir = Path(sys.argv[1])
    run_worker(io_dir)


if __name__ == "__main__":
    main()
