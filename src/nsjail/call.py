"""Jailed Python execution: call functions inside nsjail sandboxes."""

from __future__ import annotations

import functools
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Literal

from nsjail.builder import Jail
from nsjail.config import MountPt, NsJailConfig
from nsjail.exceptions import JailedExecutionError
from nsjail.mounts import system_libs, dev_minimal, python_env, proc_mount
from nsjail.presets import apply_cgroup_limits
from nsjail.runner import Runner


def _get_serializer():
    """Get the best available serializer for the *input* channel."""
    try:
        import cloudpickle
        return cloudpickle
    except ImportError:
        import pickle
        return pickle


def _serialize_input(io_dir: Path, func: Callable, args: tuple, kwargs: dict | None) -> Path:
    """Serialize function and arguments to io_dir/input.pkl."""
    pkl = _get_serializer()
    input_path = io_dir / "input.pkl"
    with open(input_path, "wb") as f:
        pkl.dump((func, args, kwargs or {}), f)
    return input_path


def _raise_jailed_error(payload: Any) -> None:
    """Raise a JailedExecutionError describing a failure reported by the jail."""
    if isinstance(payload, dict):
        etype = payload.get("type", "Error")
        emsg = payload.get("message", "")
        raise JailedExecutionError(
            f"Sandboxed function raised {etype}: {emsg}",
            original_traceback=payload.get("traceback") or None,
        )
    raise JailedExecutionError(f"Sandboxed function failed: {payload}")


def _deserialize_output(output_path: Path, *, unsafe_pickle: bool = False) -> Any:
    """Read the jailed process's result from ``output_path``.

    Security invariant: the jailed process is untrusted, so by default its
    output is read via a non-executing JSON transport -- nothing it writes can
    cause code execution in the parent. ``unsafe_pickle=True`` restores the
    legacy pickle transport and MUST only be used for fully-trusted jailed
    code (it unpickles jail-controlled bytes in the parent).
    """
    if not output_path.exists():
        raise JailedExecutionError(
            "Sandboxed process did not produce output. "
            "It may have been killed (timeout/OOM) before writing results."
        )

    if unsafe_pickle:
        pkl = _get_serializer()
        with open(output_path, "rb") as f:
            is_error, payload = pkl.load(f)
        if is_error:
            if isinstance(payload, BaseException):
                raise payload
            _raise_jailed_error(payload)
        return payload

    # Default: safe JSON transport. Jail-controlled bytes cannot execute code.
    try:
        with open(output_path, "rb") as f:
            document = json.loads(f.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise JailedExecutionError(
            f"Could not parse sandboxed output as JSON ({e}). The jailed "
            f"process may have crashed or written malformed output."
        )

    if not isinstance(document, dict) or "ok" not in document:
        raise JailedExecutionError("Sandboxed output was malformed.")

    if document.get("ok"):
        return document.get("value")

    _raise_jailed_error(document.get("error", {}))


def _build_jail_config(
    io_dir: str,
    timeout_sec: int = 600,
    memory_mb: int | None = None,
    cpu_ms_per_sec: int | None = None,
    pids_max: int | None = None,
    network: bool = False,
    writable_dirs: list[str] | None = None,
    extra_mounts: list[MountPt] | None = None,
    python_path: str | None = None,
    output_format: str = "json",
) -> NsJailConfig:
    """Build an NsJailConfig for running the worker module."""
    python_bin = python_path or sys.executable

    cfg = (
        Jail()
        .command(python_bin, "-m", "nsjail._worker", io_dir, output_format)
        .timeout(timeout_sec)
        .readonly_root()
        .mounts(system_libs())
        .mounts(dev_minimal())
        .mounts(python_env())
        .mounts(proc_mount())
        .writable(io_dir)
        .build()
    )

    if network:
        cfg.clone_newnet = False
    else:
        cfg.clone_newnet = True

    apply_cgroup_limits(
        cfg,
        memory_mb=memory_mb,
        cpu_ms_per_sec=cpu_ms_per_sec,
        pids_max=pids_max,
    )

    for d in writable_dirs or []:
        cfg.mount.append(MountPt(src=d, dst=d, is_bind=True, rw=True))

    if extra_mounts:
        cfg.mount.extend(extra_mounts)

    return cfg


def jail_call(
    func: Callable,
    args: tuple = (),
    kwargs: dict | None = None,
    *,
    memory_mb: int | None = None,
    timeout_sec: int = 600,
    cpu_ms_per_sec: int | None = None,
    pids_max: int | None = None,
    network: bool = False,
    writable_dirs: list[str] | None = None,
    extra_mounts: list[MountPt] | None = None,
    nsjail_path: str | None = None,
    transport: Literal["tmpfs", "pipe"] = "tmpfs",
    python_path: str | None = None,
    unsafe_pickle_output: bool = False,
    _io_dir: Path | None = None,
) -> Any:
    """Call a function inside an nsjail sandbox.

    The function and its arguments are pickled *into* the jail (the parent is
    trusted, and rich callables must cross the boundary). The result is
    returned via a safe, non-executing JSON transport by default: nothing the
    jailed code writes can execute in the parent.

    Because JSON is the return transport, results must be JSON-serializable.
    To return rich Python objects, set ``unsafe_pickle_output=True`` -- but
    this unpickles jail-controlled bytes in the parent and is only safe when
    the jailed code is fully trusted (a jailed attacker can then escape the
    sandbox via a malicious ``__reduce__``). Off by default; see
    GHSA-w6j4-3xhv-r968.
    """
    output_format = "pickle" if unsafe_pickle_output else "json"
    output_name = "output.pkl" if unsafe_pickle_output else "output.json"

    own_io_dir = _io_dir is None
    io_dir = _io_dir or Path(tempfile.mkdtemp(prefix="nsjail_call_"))

    try:
        _serialize_input(io_dir, func, args, kwargs)

        cfg = _build_jail_config(
            io_dir=str(io_dir),
            timeout_sec=timeout_sec,
            memory_mb=memory_mb,
            cpu_ms_per_sec=cpu_ms_per_sec,
            pids_max=pids_max,
            network=network,
            writable_dirs=writable_dirs,
            extra_mounts=extra_mounts,
            python_path=python_path,
            output_format=output_format,
        )

        runner = Runner(nsjail_path=nsjail_path)
        result = runner.run(
            overrides=cfg,
            override_fields=set(vars(cfg).keys()),
        )

        if result.timed_out:
            raise JailedExecutionError(
                f"Sandboxed function timed out after {timeout_sec}s"
            )

        output_path = io_dir / output_name
        return _deserialize_output(output_path, unsafe_pickle=unsafe_pickle_output)

    finally:
        if own_io_dir:
            shutil.rmtree(io_dir, ignore_errors=True)


def jailed(**jail_kwargs: Any) -> Callable:
    """Decorator that runs the function inside an nsjail sandbox on each call."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return jail_call(func, args, kwargs, **jail_kwargs)
        return wrapper
    return decorator


class JailContext:
    """Context manager for multiple sandboxed function calls."""

    def __init__(self, **jail_kwargs: Any) -> None:
        self._jail_kwargs = jail_kwargs
        self._io_dir: Path | None = None

    def __enter__(self) -> JailContext:
        self._io_dir = Path(tempfile.mkdtemp(prefix="nsjail_ctx_"))
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._io_dir:
            shutil.rmtree(self._io_dir, ignore_errors=True)
            self._io_dir = None

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call a function inside the sandbox."""
        return jail_call(
            func, args=args, kwargs=kwargs,
            _io_dir=self._io_dir,
            **self._jail_kwargs,
        )
