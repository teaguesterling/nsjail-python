# v0.1.x Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add async_run, builder .run(), to_protobuf serializer, and complete code generator emission to nsjail-python.

**Architecture:** Four independent enhancements to existing modules. async_run extracts shared prep logic from Runner.run(). Builder .run() delegates to Runner. to_protobuf piggybacks on textproto serializer. Code generator adds emitter functions to the existing parser.

**Tech Stack:** Python 3.12+, asyncio, protobuf (optional), dataclasses

**Spec:** `docs/superpowers/specs/2026-03-29-v01x-enhancements-design.md`

---

### Task 1: Extract _prepare_run from Runner.run()

**Files:**
- Modify: `src/nsjail/runner.py`
- Modify: `tests/test_runner.py`

This refactor extracts the config merging and rendering logic into a shared `_prepare_run()` method, keeping `run()` behavior identical. This prepares for `async_run()` in Task 2.

- [ ] **Step 1: Write test for _prepare_run**

Add to `tests/test_runner.py`:

```python
class TestPrepareRun:
    def test_prepare_run_returns_args_and_path(self):
        base = NsJailConfig(hostname="test", time_limit=30, exec_bin=Exe(path="/bin/sh"))
        runner = Runner(base_config=base, nsjail_path="/usr/bin/nsjail")
        nsjail_args, config_path, cfg = runner._prepare_run(None, None, None)
        assert nsjail_args[0] == "/usr/bin/nsjail"
        assert "--config" in nsjail_args
        assert config_path is not None
        assert config_path.exists()
        config_path.unlink()

    def test_prepare_run_with_overrides(self):
        base = NsJailConfig(time_limit=60, exec_bin=Exe(path="/bin/sh"))
        runner = Runner(base_config=base, nsjail_path="/usr/bin/nsjail")
        nsjail_args, config_path, cfg = runner._prepare_run(
            NsJailConfig(time_limit=120), {"time_limit"}, None
        )
        assert cfg.time_limit == 120
        if config_path:
            config_path.unlink()

    def test_prepare_run_with_extra_args(self):
        base = NsJailConfig(exec_bin=Exe(path="python", arg=["main.py"]))
        runner = Runner(base_config=base, nsjail_path="/usr/bin/nsjail")
        _, config_path, cfg = runner._prepare_run(None, None, ["--verbose"])
        assert cfg.exec_bin.arg == ["main.py", "--verbose"]
        if config_path:
            config_path.unlink()

    def test_prepare_run_cli_mode(self):
        base = NsJailConfig(hostname="test", exec_bin=Exe(path="/bin/sh"))
        runner = Runner(base_config=base, nsjail_path="/usr/bin/nsjail", render_mode="cli")
        nsjail_args, config_path, cfg = runner._prepare_run(None, None, None)
        assert config_path is None
        assert "--hostname" in nsjail_args
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_runner.py::TestPrepareRun -v`
Expected: FAIL with AttributeError.

- [ ] **Step 3: Extract _prepare_run and _make_result from run()**

Replace the `Runner` class in `src/nsjail/runner.py` with this refactored version. The `__init__`, `merge_configs`, `resolve_nsjail_path`, `_try_companion_binary`, and `NsJailResult` stay unchanged. Only the Runner class body changes:

```python
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

    def _prepare_run(
        self,
        overrides: NsJailConfig | None,
        override_fields: set[str] | None,
        extra_args: list[str] | None,
    ) -> tuple[list[str], Path | None, NsJailConfig]:
        """Merge config, resolve binary, render.

        Returns (nsjail_args, config_path, merged_cfg).
        Caller is responsible for cleaning up config_path.
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
        self, returncode: int, stdout: bytes, stderr: bytes,
        config_path: Path | None, nsjail_args: list[str],
    ) -> NsJailResult:
        """Build NsJailResult from subprocess output."""
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
        )

    def run(
        self,
        overrides: NsJailConfig | None = None,
        *,
        override_fields: set[str] | None = None,
        extra_args: list[str] | None = None,
        timeout: float | None = None,
    ) -> NsJailResult:
        nsjail_args, config_path, cfg = self._prepare_run(
            overrides, override_fields, extra_args
        )

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

        return self._make_result(
            result.returncode,
            result.stdout if self._capture_output else b"",
            result.stderr if self._capture_output else b"",
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
        )
```

- [ ] **Step 4: Run all tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/ -v`
Expected: All 108+ tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/runner.py tests/test_runner.py
git commit -m "refactor: extract _prepare_run and _make_result from Runner.run()"
```

---

### Task 2: Add async_run() to Runner

**Files:**
- Modify: `src/nsjail/runner.py`
- Modify: `tests/test_runner.py`

- [ ] **Step 1: Write tests for async_run**

Add `import asyncio` to the top of `tests/test_runner.py`, then add:

```python
class TestAsyncRun:
    def test_async_run_returns_result(self):
        base = NsJailConfig(exec_bin=Exe(path="/bin/echo", arg=["hello"]))
        runner = Runner(base_config=base, nsjail_path="/bin/echo")

        mock_proc = MagicMock()
        mock_proc.communicate = asyncio.coroutine(lambda: (b"hello\n", b""))
        mock_proc.returncode = 0

        async def mock_create(*args, **kwargs):
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_create):
            result = asyncio.run(runner.async_run())

        assert isinstance(result, NsJailResult)
        assert result.returncode == 0
        assert result.stdout == b"hello\n"

    def test_async_run_with_extra_args(self):
        base = NsJailConfig(exec_bin=Exe(path="python", arg=["main.py"]))
        runner = Runner(base_config=base, nsjail_path="/usr/bin/nsjail")

        mock_proc = MagicMock()
        mock_proc.communicate = asyncio.coroutine(lambda: (b"", b""))
        mock_proc.returncode = 0

        async def mock_create(*args, **kwargs):
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_create):
            result = asyncio.run(runner.async_run(extra_args=["--verbose"]))

        assert result.returncode == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_runner.py::TestAsyncRun -v`
Expected: FAIL with AttributeError.

- [ ] **Step 3: Implement async_run**

Add `import asyncio` to the imports at the top of `src/nsjail/runner.py`.

Add this method to the `Runner` class, after `run()`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_runner.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/runner.py tests/test_runner.py
git commit -m "feat: add async_run() to Runner"
```

---

### Task 3: Add .run() and .async_run() to Jail Builder

**Files:**
- Modify: `src/nsjail/builder.py`
- Modify: `tests/test_builder.py`

- [ ] **Step 1: Write tests**

Add these imports to the top of `tests/test_builder.py`:

```python
from unittest.mock import MagicMock, patch
from nsjail.runner import NsJailResult, Runner
```

Then add:

```python
class TestBuilderRun:
    def test_run_with_default_runner(self):
        mock_result = NsJailResult(
            returncode=0, stdout=b"ok", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        with patch.object(Runner, "run", return_value=mock_result):
            result = Jail().sh("echo hi").timeout(10).run()
        assert result.returncode == 0

    def test_run_with_explicit_runner(self):
        runner = Runner(nsjail_path="/custom/nsjail", render_mode="cli")
        mock_result = NsJailResult(
            returncode=0, stdout=b"", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        with patch.object(Runner, "run", return_value=mock_result):
            result = Jail().sh("true").run(runner=runner)
        assert result.returncode == 0

    def test_run_passes_kwargs(self):
        mock_result = NsJailResult(
            returncode=0, stdout=b"", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        with patch.object(Runner, "run", return_value=mock_result) as mock_run:
            Jail().sh("true").run(extra_args=["--verbose"])
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs.get("extra_args") == ["--verbose"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_builder.py::TestBuilderRun -v`
Expected: FAIL with AttributeError.

- [ ] **Step 3: Implement .run() and .async_run()**

Add `TYPE_CHECKING` import and the two methods to `src/nsjail/builder.py`.

At the top, change the imports to:

```python
from __future__ import annotations

from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from nsjail.runner import Runner, NsJailResult
```

Add at the end of the `Jail` class:

```python
    # --- Execution ---

    def run(self, *, runner: Runner | None = None, **run_kwargs: object) -> NsJailResult:
        """Execute the built config via a Runner."""
        from nsjail.runner import Runner as _Runner

        r = runner or _Runner()
        temp = _Runner(
            base_config=self._cfg,
            nsjail_path=r._nsjail_path,
            render_mode=r._render_mode,
            capture_output=r._capture_output,
            keep_config=r._keep_config,
        )
        return temp.run(**run_kwargs)

    async def async_run(self, *, runner: Runner | None = None, **run_kwargs: object) -> NsJailResult:
        """Execute the built config asynchronously via a Runner."""
        from nsjail.runner import Runner as _Runner

        r = runner or _Runner()
        temp = _Runner(
            base_config=self._cfg,
            nsjail_path=r._nsjail_path,
            render_mode=r._render_mode,
            capture_output=r._capture_output,
            keep_config=r._keep_config,
        )
        return await temp.async_run(**run_kwargs)
```

- [ ] **Step 4: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_builder.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/builder.py tests/test_builder.py
git commit -m "feat: add .run() and .async_run() to Jail builder"
```

---

### Task 4: Compile config.proto and add to_protobuf serializer

**Files:**
- Create: `src/nsjail/_proto/__init__.py`
- Create: `src/nsjail/_proto/config_pb2.py` (generated by protoc)
- Create: `src/nsjail/serializers/protobuf.py`
- Create: `tests/test_protobuf_serializer.py`

- [ ] **Step 1: Compile config.proto**

```bash
cd /mnt/aux-data/teague/Projects/nsjail-python
mkdir -p src/nsjail/_proto
touch src/nsjail/_proto/__init__.py
/home/teague/.local/share/venv/bin/python -m grpc_tools.protoc \
    --python_out=src/nsjail/_proto/ \
    --proto_path=_vendor/nsjail/ \
    config.proto
```

Verify: `ls src/nsjail/_proto/config_pb2.py`

- [ ] **Step 2: Write tests**

Create `tests/test_protobuf_serializer.py`:

```python
import pytest

pytest.importorskip("google.protobuf")

from google.protobuf import text_format

from nsjail.config import NsJailConfig, MountPt, Exe, IdMap
from nsjail.serializers.protobuf import to_protobuf
from nsjail.serializers.textproto import to_textproto


class TestToProtobuf:
    def test_empty_config(self):
        cfg = NsJailConfig()
        msg = to_protobuf(cfg)
        assert msg is not None

    def test_simple_fields(self):
        cfg = NsJailConfig(hostname="sandbox", time_limit=30)
        msg = to_protobuf(cfg)
        assert msg.hostname == "sandbox"
        assert msg.time_limit == 30

    def test_mount(self):
        cfg = NsJailConfig(mount=[
            MountPt(src="/", dst="/", is_bind=True, rw=False),
        ])
        msg = to_protobuf(cfg)
        assert len(msg.mount) == 1
        assert msg.mount[0].src == "/"
        assert msg.mount[0].is_bind is True

    def test_exec_bin(self):
        cfg = NsJailConfig(exec_bin=Exe(path="/bin/sh", arg=["-c", "echo hi"]))
        msg = to_protobuf(cfg)
        assert msg.exec_bin.path == "/bin/sh"
        assert list(msg.exec_bin.arg) == ["-c", "echo hi"]

    def test_round_trip_matches_textproto(self):
        cfg = NsJailConfig(
            hostname="test",
            time_limit=60,
            envar=["A=1"],
            mount=[MountPt(src="/lib", dst="/lib", is_bind=True)],
            exec_bin=Exe(path="/bin/sh"),
        )
        our_text = to_textproto(cfg)
        msg = to_protobuf(cfg)
        from nsjail._proto import config_pb2
        msg_from_ours = config_pb2.NsJailConfig()
        text_format.Parse(our_text, msg_from_ours)
        assert msg_from_ours == msg
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_protobuf_serializer.py -v`
Expected: FAIL (no protobuf module).

- [ ] **Step 4: Implement to_protobuf**

Create `src/nsjail/serializers/protobuf.py`:

```python
"""Convert NsJailConfig dataclass to compiled protobuf message.

Requires the [proto] extra: pip install nsjail-python[proto]
"""

from __future__ import annotations

from typing import Any

from google.protobuf import text_format

from nsjail.serializers.textproto import to_textproto


def to_protobuf(cfg: Any) -> Any:
    """Convert a NsJailConfig to a compiled protobuf message."""
    from nsjail._proto import config_pb2

    text = to_textproto(cfg)
    msg = config_pb2.NsJailConfig()
    text_format.Parse(text, msg)
    return msg
```

- [ ] **Step 5: Install protobuf and run tests**

```bash
/home/teague/.local/share/venv/bin/pip install "protobuf>=4.0"
/home/teague/.local/share/venv/bin/pytest tests/test_protobuf_serializer.py -v
```

Expected: All pass.

- [ ] **Step 6: Run full test suite**

Run: `/home/teague/.local/share/venv/bin/pytest tests/ -v`
Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add src/nsjail/_proto/ src/nsjail/serializers/protobuf.py tests/test_protobuf_serializer.py
git commit -m "feat: add to_protobuf serializer with compiled proto"
```

---

### Task 5: Code Generator — Enum Emission

**Files:**
- Modify: `_codegen/generate.py`
- Create: `tests/test_codegen.py`

- [ ] **Step 1: Write tests**

Create `tests/test_codegen.py`:

```python
from _codegen.generate import (
    parse_proto,
    ProtoEnum,
    ProtoMessage,
)


SAMPLE_PROTO = """
syntax = "proto2";
package nsjail;

enum Mode {
    LISTEN = 0;
    ONCE = 1;
    RERUN = 2;
    EXECVE = 3;
}

enum LogLevel {
    DEBUG = 0;
    INFO = 1;
    WARNING = 2;
    ERROR = 3;
    FATAL = 4;
}

message NsJailConfig {
    enum RLimit {
        VALUE = 0;
        SOFT = 1;
        HARD = 2;
        INF = 3;
    }
    optional string hostname = 8 [default = "NSJAIL"];
    optional uint32 time_limit = 14 [default = 600];
    optional bool clone_newnet = 60 [default = true];
    repeated string envar = 19;
    optional RLimit rlimit_as_type = 36 [default = VALUE];
}
"""


class TestParseProto:
    def test_parses_top_level_enums(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        assert len(enums) == 2
        assert enums[0].name == "Mode"

    def test_parses_nested_enum(self):
        items = parse_proto(SAMPLE_PROTO)
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        cfg = messages[0]
        assert len(cfg.enums) == 1
        assert cfg.enums[0].name == "RLimit"

    def test_parses_fields_with_defaults(self):
        items = parse_proto(SAMPLE_PROTO)
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        cfg = messages[0]
        hostname = next(f for f in cfg.fields if f.name == "hostname")
        assert hostname.default == '"NSJAIL"'

    def test_parses_repeated_fields(self):
        items = parse_proto(SAMPLE_PROTO)
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        cfg = messages[0]
        envar = next(f for f in cfg.fields if f.name == "envar")
        assert envar.label == "repeated"
```

- [ ] **Step 2: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_codegen.py -v`
Expected: All pass (parser already works).

- [ ] **Step 3: Add emit_enums**

Add to `_codegen/generate.py` (after the parser functions, before `main()`):

```python
PROMOTED_ENUMS: dict[tuple[str, str], str] = {
    ("NsJailConfig", "RLimit"): "RLimitType",
}


def emit_enums(top_level_enums: list[ProtoEnum], messages: list[ProtoMessage]) -> str:
    """Generate enums.py content."""
    lines = [HEADER, "from enum import IntEnum\n"]

    for enum in top_level_enums:
        lines.append(f"\nclass {enum.name}(IntEnum):")
        for name, value in enum.values:
            lines.append(f"    {name} = {value}")
        lines.append("")

    for msg in messages:
        for nested_enum in msg.enums:
            key = (msg.name, nested_enum.name)
            python_name = PROMOTED_ENUMS.get(key)
            if python_name:
                lines.append(f"\nclass {python_name}(IntEnum):")
                for name, value in nested_enum.values:
                    lines.append(f"    {name} = {value}")
                lines.append("")

    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Write test for emit_enums**

Add to `tests/test_codegen.py`:

```python
from _codegen.generate import emit_enums


class TestEmitEnums:
    def test_emit_top_level_enums(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_enums(enums, messages)
        assert "class Mode(IntEnum):" in output
        assert "LISTEN = 0" in output
        assert "class LogLevel(IntEnum):" in output
        assert "class RLimitType(IntEnum):" in output
        assert "VALUE = 0" in output
```

- [ ] **Step 5: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_codegen.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add _codegen/generate.py tests/test_codegen.py
git commit -m "feat: add enum emission to code generator"
```

---

### Task 6: Code Generator — Config and Field Meta Emission + main()

**Files:**
- Modify: `_codegen/generate.py`
- Modify: `tests/test_codegen.py`

This is the largest task. It adds `emit_config()`, `emit_field_meta()`, and updates `main()` to write all three files. Because the emitters are complex and tightly coupled (emit_config populates type registries that emit_field_meta uses), they're implemented together.

- [ ] **Step 1: Implement emit_config and emit_field_meta**

Add these to `_codegen/generate.py` (the code is substantial — see the spec for the type mapping table). The implementer should:

1. Add `PROTO_TYPE_MAP` dict mapping proto types to Python types
2. Add `KNOWN_MESSAGES` set and `KNOWN_ENUMS` dict (populated by emit_config)
3. Add `_python_type(field, parent_msg)` helper
4. Add `_python_default(field, python_type)` helper
5. Add `_emit_dataclass(msg)` helper
6. Add `emit_config(messages, top_enums)` function
7. Add `emit_field_meta(messages, cli_flags)` function
8. Update `main()` to call all three emitters and write to `src/nsjail/`

The key challenge: the generated config.py must produce output that passes all 108+ existing tests. Use the existing hand-written `src/nsjail/config.py` as the reference for correct field types, defaults, and ordering.

- [ ] **Step 2: Write tests**

Add to `tests/test_codegen.py`:

```python
from _codegen.generate import emit_config, emit_field_meta
from _codegen.cli_flags import CLI_FLAGS
from pathlib import Path
import pytest


class TestEmitConfig:
    def test_emit_produces_valid_python(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_config(messages, enums)
        compile(output, "<test>", "exec")

    def test_emit_has_dataclass(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_config(messages, enums)
        assert "@dataclass" in output
        assert "class NsJailConfig:" in output

    def test_emit_has_correct_defaults(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_config(messages, enums)
        assert 'hostname: str = "NSJAIL"' in output
        assert "time_limit: int = 600" in output
        assert "clone_newnet: bool = True" in output

    def test_emit_repeated_field(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_config(messages, enums)
        assert "envar: list[str] = field(default_factory=list)" in output


class TestEmitFieldMeta:
    def test_emit_produces_valid_python(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        emit_config(messages, enums)
        output = emit_field_meta(messages, CLI_FLAGS)
        compile(output, "<test>", "exec")

    def test_emit_has_hostname_entry(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        emit_config(messages, enums)
        output = emit_field_meta(messages, CLI_FLAGS)
        assert '"NsJailConfig", "hostname"' in output
        assert '"NSJAIL"' in output


class TestFullGeneration:
    def test_generate_against_vendored_proto(self):
        proto_path = Path("_vendor/nsjail/config.proto")
        if not proto_path.exists():
            pytest.skip("Vendored config.proto not available")

        text = proto_path.read_text()
        items = parse_proto(text)
        top_enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]

        enums_out = emit_enums(top_enums, messages)
        compile(enums_out, "enums.py", "exec")

        config_out = emit_config(messages, top_enums)
        compile(config_out, "config.py", "exec")

        meta_out = emit_field_meta(messages, CLI_FLAGS)
        compile(meta_out, "_field_meta.py", "exec")
```

- [ ] **Step 3: Run generator against real config.proto**

```bash
cd /mnt/aux-data/teague/Projects/nsjail-python
/home/teague/.local/share/venv/bin/python -m _codegen.generate
```

- [ ] **Step 4: Run full test suite against generated files**

Run: `/home/teague/.local/share/venv/bin/pytest tests/ -v`

This is the critical validation — all 108+ existing tests must pass against the generated output. If they fail, fix the emitter functions until they pass.

- [ ] **Step 5: Commit**

```bash
git add _codegen/generate.py src/nsjail/config.py src/nsjail/enums.py src/nsjail/_field_meta.py tests/test_codegen.py
git commit -m "feat: complete code generator — emit config.py, enums.py, _field_meta.py"
```

---

### Task 7: Final Integration Tests and Push

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Add integration tests for new features**

Add to `tests/test_integration.py`:

```python
import asyncio
from unittest.mock import MagicMock, patch

from nsjail import Jail, Runner
from nsjail.runner import NsJailResult


class TestBuilderRunIntegration:
    def test_builder_run_with_mock(self):
        mock_result = NsJailResult(
            returncode=0, stdout=b"hello", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        with patch.object(Runner, "run", return_value=mock_result):
            result = (
                Jail()
                .sh("echo hello")
                .timeout(10)
                .memory(256, "MB")
                .run()
            )
        assert result.returncode == 0
        assert result.stdout == b"hello"
```

Add protobuf integration test (only runs if protobuf installed):

```python
import pytest


class TestProtobufIntegration:
    def test_protobuf_round_trip(self):
        pytest.importorskip("google.protobuf")
        from nsjail.serializers.protobuf import to_protobuf

        cfg = (
            Jail()
            .sh("echo hello")
            .timeout(30)
            .memory(256, "MB")
            .build()
        )
        msg = to_protobuf(cfg)
        assert msg.time_limit == 30
```

- [ ] **Step 2: Run full test suite**

Run: `/home/teague/.local/share/venv/bin/pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 3: Commit and push**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for v0.1.x enhancements"
git push
```
