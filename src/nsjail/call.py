"""Jailed Python execution: call functions inside nsjail sandboxes."""

from __future__ import annotations

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
    """Get the best available serializer."""
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


def _deserialize_output(output_path: Path) -> Any:
    """Read and deserialize the result from output.pkl."""
    pkl = _get_serializer()

    if not output_path.exists():
        raise JailedExecutionError(
            "Sandboxed process did not produce output. "
            "It may have been killed (timeout/OOM) before writing results."
        )

    with open(output_path, "rb") as f:
        is_error, result = pkl.load(f)

    if is_error:
        if isinstance(result, BaseException):
            raise result
        raise JailedExecutionError(f"Sandboxed function failed: {result}")

    return result


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
) -> NsJailConfig:
    """Build an NsJailConfig for running the worker module."""
    python_bin = python_path or sys.executable

    cfg = (
        Jail()
        .command(python_bin, "-m", "nsjail._worker", io_dir)
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
    _io_dir: Path | None = None,
) -> Any:
    """Call a function inside an nsjail sandbox.

    Security note: Uses pickle for serialization between parent and child
    processes within the same trust domain (like multiprocessing). The sandbox
    is the security boundary, not pickle.
    """
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

        output_path = io_dir / "output.pkl"
        return _deserialize_output(output_path)

    finally:
        if own_io_dir:
            shutil.rmtree(io_dir, ignore_errors=True)
