"""Runner for executing nsjail sandboxes."""

from __future__ import annotations

import copy
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, fields as dc_fields
from pathlib import Path
from typing import Any

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
    ) -> None:
        self._nsjail_path = nsjail_path
        self._base_config = copy.deepcopy(base_config) if base_config else NsJailConfig()
        self._render_mode = render_mode
        self._capture_output = capture_output
        self._keep_config = keep_config

    def run(
        self,
        overrides: NsJailConfig | None = None,
        *,
        override_fields: set[str] | None = None,
        extra_args: list[str] | None = None,
        timeout: float | None = None,
    ) -> NsJailResult:
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

        try:
            result = subprocess.run(
                nsjail_args,
                capture_output=self._capture_output,
                timeout=timeout,
            )
        finally:
            if config_path and not self._keep_config:
                config_path.unlink(missing_ok=True)
                config_path = None

        timed_out = result.returncode == 109
        signaled = result.returncode > 100 and not timed_out
        oom_killed = result.returncode == 137

        return NsJailResult(
            returncode=result.returncode,
            stdout=result.stdout if self._capture_output else b"",
            stderr=result.stderr if self._capture_output else b"",
            config_path=config_path,
            nsjail_args=nsjail_args,
            timed_out=timed_out,
            oom_killed=oom_killed,
            signaled=signaled,
            inner_returncode=result.returncode if result.returncode < 100 else None,
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
        )
