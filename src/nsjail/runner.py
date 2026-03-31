"""Runner for executing nsjail sandboxes."""

from __future__ import annotations

import asyncio
import copy
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, fields as dc_fields
from pathlib import Path
from typing import Any

from nsjail.cgroup import CgroupMonitor, CgroupStats
from nsjail.config import NsJailConfig
from nsjail.exceptions import NsjailNotFound
from nsjail.serializers import to_file


def _try_companion_binary() -> Path | None:
    """Try to find the nsjail binary from companion packages."""
    for module_name in ("nsjail_bin", "nsjail_bin_build"):
        try:
            mod = __import__(module_name)
            return mod.binary_path()
        except (ImportError, AttributeError, FileNotFoundError):
            continue
    return None


def resolve_nsjail_path(explicit_path: str | None) -> Path:
    """Resolve the nsjail binary path.

    Precedence: explicit path > system PATH > companion package > error.
    """
    if explicit_path is not None:
        return Path(explicit_path)

    system = shutil.which("nsjail")
    if system is not None:
        return Path(system)

    companion = _try_companion_binary()
    if companion is not None:
        return companion

    raise NsjailNotFound()


def merge_configs(
    base: NsJailConfig,
    overrides: NsJailConfig,
    *,
    override_fields: set[str],
    extra_args: list[str] | None = None,
) -> NsJailConfig:
    """Merge an override config into a base config.

    Scalars in override_fields replace the base value.
    Lists in override_fields are appended.
    extra_args are appended to exec_bin.arg.
    """
    merged = copy.deepcopy(base)

    for f in dc_fields(NsJailConfig):
        if f.name not in override_fields:
            continue

        override_val = getattr(overrides, f.name)
        base_val = getattr(merged, f.name)

        if isinstance(base_val, list):
            base_val.extend(override_val)
        else:
            setattr(merged, f.name, override_val)

    if extra_args and merged.exec_bin is not None:
        merged.exec_bin.arg.extend(extra_args)

    return merged


@dataclass
class NsJailResult:
    """Result of running nsjail."""

    returncode: int
    stdout: bytes
    stderr: bytes
    config_path: Path | None
    nsjail_args: list[str]
    timed_out: bool
    oom_killed: bool
    signaled: bool
    inner_returncode: int | None
    cgroup_stats: CgroupStats | None = None


class Runner:
    """Configurable nsjail executor with optional baked-in config."""

    def __init__(
        self,
        *,
        nsjail_path: str | None = None,
        base_config: NsJailConfig | None = None,
        render_mode: str = "textproto",
        capture_output: bool = True,
        keep_config: bool = False,
        collect_cgroup_stats: bool = False,
        cgroup_poll_interval: float = 0.1,
    ) -> None:
        self._nsjail_path = nsjail_path
        self._base_config = copy.deepcopy(base_config) if base_config else NsJailConfig()
        self._render_mode = render_mode
        self._capture_output = capture_output
        self._keep_config = keep_config
        self._collect_cgroup_stats = collect_cgroup_stats
        self._cgroup_poll_interval = cgroup_poll_interval

    def _prepare_run(
        self,
        overrides: NsJailConfig | None,
        override_fields: set[str] | None,
        extra_args: list[str] | None,
    ) -> tuple[list[str], Path | None, NsJailConfig]:
        """Resolve binary, merge configs, and render to args.

        Returns (nsjail_args, config_path, merged_cfg).
        config_path is None when render_mode is 'cli'.
        """
        nsjail_bin = resolve_nsjail_path(self._nsjail_path)

        if overrides is not None and override_fields:
            cfg = merge_configs(
                self._base_config, overrides,
                override_fields=override_fields, extra_args=extra_args,
            )
        elif extra_args:
            cfg = merge_configs(
                self._base_config, NsJailConfig(),
                override_fields=set(), extra_args=extra_args,
            )
        else:
            cfg = copy.deepcopy(self._base_config)

        config_path: Path | None = None
        if self._render_mode == "textproto":
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".cfg", delete=False, prefix="nsjail_"
            )
            config_path = Path(tmp.name)
            to_file(cfg, config_path)
            tmp.close()
            nsjail_args = [str(nsjail_bin), "--config", str(config_path)]
        else:
            from nsjail.serializers.cli import to_cli_args
            cli_args = to_cli_args(cfg, on_unsupported="skip")
            nsjail_args = [str(nsjail_bin)] + cli_args

        if cfg.exec_bin and self._render_mode == "cli":
            nsjail_args.append("--")
            nsjail_args.append(cfg.exec_bin.path)
            nsjail_args.extend(cfg.exec_bin.arg)

        return nsjail_args, config_path, cfg

    def _make_result(
        self,
        returncode: int,
        stdout: bytes,
        stderr: bytes,
        config_path: Path | None,
        nsjail_args: list[str],
        cgroup_stats: CgroupStats | None = None,
    ) -> NsJailResult:
        """Build an NsJailResult from raw subprocess output."""
        timed_out = returncode == 109
        signaled = returncode > 100 and not timed_out
        oom_killed = returncode == 137

        return NsJailResult(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            config_path=config_path,
            nsjail_args=nsjail_args,
            timed_out=timed_out,
            oom_killed=oom_killed,
            signaled=signaled,
            inner_returncode=returncode if returncode < 100 else None,
            cgroup_stats=cgroup_stats,
        )

    def _start_cgroup_monitor(self, cfg: NsJailConfig, pid: int) -> CgroupMonitor:
        """Create and start a CgroupMonitor for the given nsjail process."""
        use_v2 = cfg.use_cgroupv2 or cfg.detect_cgroupv2
        if use_v2:
            cgroup_path = Path(cfg.cgroupv2_mount) / cfg.cgroup_mem_parent / f"NSJAIL.{pid}"
            monitor = CgroupMonitor(
                cgroup_path=cgroup_path,
                poll_interval=self._cgroup_poll_interval,
                use_v2=True,
            )
        else:
            monitor = CgroupMonitor(
                cgroup_path=Path("/dev/null"),
                poll_interval=self._cgroup_poll_interval,
                use_v2=False,
                v1_memory_path=Path(cfg.cgroup_mem_mount) / cfg.cgroup_mem_parent / f"NSJAIL.{pid}" if cfg.cgroup_mem_max else None,
                v1_cpu_path=Path(cfg.cgroup_cpu_mount) / cfg.cgroup_cpu_parent / f"NSJAIL.{pid}" if cfg.cgroup_cpu_ms_per_sec else None,
                v1_pids_path=Path(cfg.cgroup_pids_mount) / cfg.cgroup_pids_parent / f"NSJAIL.{pid}" if cfg.cgroup_pids_max else None,
            )
        monitor.start()
        return monitor

    def run(
        self,
        overrides: NsJailConfig | None = None,
        *,
        override_fields: set[str] | None = None,
        extra_args: list[str] | None = None,
        timeout: float | None = None,
    ) -> NsJailResult:
        nsjail_args, config_path, cfg = self._prepare_run(overrides, override_fields, extra_args)

        cgroup_monitor = None
        cgroup_stats = None

        try:
            proc = subprocess.Popen(
                nsjail_args,
                stdout=subprocess.PIPE if self._capture_output else None,
                stderr=subprocess.PIPE if self._capture_output else None,
            )

            if self._collect_cgroup_stats:
                cgroup_monitor = self._start_cgroup_monitor(cfg, proc.pid)

            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        finally:
            if cgroup_monitor:
                cgroup_stats = cgroup_monitor.stop()
            if config_path and not self._keep_config:
                config_path.unlink(missing_ok=True)
                config_path = None

        return self._make_result(
            returncode=proc.returncode,
            stdout=stdout if self._capture_output else b"",
            stderr=stderr if self._capture_output else b"",
            config_path=config_path,
            nsjail_args=nsjail_args,
            cgroup_stats=cgroup_stats,
        )

    async def async_run(
        self,
        overrides: NsJailConfig | None = None,
        *,
        override_fields: set[str] | None = None,
        extra_args: list[str] | None = None,
        timeout: float | None = None,
    ) -> NsJailResult:
        """Run nsjail asynchronously."""
        nsjail_args, config_path, cfg = self._prepare_run(
            overrides, override_fields, extra_args
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *nsjail_args,
                stdout=asyncio.subprocess.PIPE if self._capture_output else None,
                stderr=asyncio.subprocess.PIPE if self._capture_output else None,
            )
            if timeout is not None:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            else:
                stdout, stderr = await proc.communicate()
        finally:
            if config_path and not self._keep_config:
                config_path.unlink(missing_ok=True)
                config_path = None

        return self._make_result(
            proc.returncode,
            stdout if self._capture_output else b"",
            stderr if self._capture_output else b"",
            config_path,
            nsjail_args,
        )

    def fork(
        self,
        *,
        overrides: NsJailConfig | None = None,
        override_fields: set[str] | None = None,
        nsjail_path: str | None = None,
    ) -> Runner:
        if overrides and override_fields:
            new_base = merge_configs(
                self._base_config, overrides, override_fields=override_fields
            )
        else:
            new_base = copy.deepcopy(self._base_config)

        return Runner(
            nsjail_path=nsjail_path or self._nsjail_path,
            base_config=new_base,
            render_mode=self._render_mode,
            capture_output=self._capture_output,
            keep_config=self._keep_config,
            collect_cgroup_stats=self._collect_cgroup_stats,
            cgroup_poll_interval=self._cgroup_poll_interval,
        )
