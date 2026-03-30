# nsjail-python v0.1.x Enhancements Design Spec

**Date:** 2026-03-29
**Status:** Draft
**Scope:** Four independent enhancements batched into a single release

## Context

nsjail-python v0.1.0 shipped with a complete config model, two serializers (textproto, CLI), presets, a fluent builder, and a sync Runner. This spec covers four near-term enhancements that round out the API for v0.1.x:

1. **async_run()** — Async subprocess execution on Runner
2. **Builder .run()** — Terminal method to execute directly from a builder chain
3. **to_protobuf()** — Protobuf message serializer (requires `[proto]` extra)
4. **Code generator emission** — Complete the codegen to emit config.py, enums.py, _field_meta.py from config.proto

## Enhancement 1: async_run() on Runner

### What changes

**File:** `src/nsjail/runner.py`

Extract shared config preparation logic from `run()` into a private `_prepare_run()` method. Both `run()` and `async_run()` call it.

```python
def _prepare_run(
    self,
    overrides: NsJailConfig | None,
    override_fields: set[str] | None,
    extra_args: list[str] | None,
) -> tuple[list[str], Path | None, NsJailConfig]:
    """Merge config, resolve binary, render. Returns (nsjail_args, config_path, cfg)."""
```

Returns a tuple of (nsjail command line, temp config path if textproto mode, merged config). Both `run()` and `async_run()` use this, then diverge only at the subprocess call.

### async_run() signature

```python
async def async_run(
    self,
    overrides: NsJailConfig | None = None,
    *,
    override_fields: set[str] | None = None,
    extra_args: list[str] | None = None,
    timeout: float | None = None,
) -> NsJailResult:
```

Uses `asyncio.create_subprocess_exec` for the subprocess call and `asyncio.wait_for` for timeout handling. Returns the same `NsJailResult` dataclass.

Config file cleanup uses a try/finally block, same as the sync version.

## Enhancement 2: Builder .run()

### What changes

**File:** `src/nsjail/builder.py`

Add `.run()` and `.async_run()` methods that terminate the builder chain by executing via a Runner.

```python
def run(self, *, runner: Runner | None = None, **run_kwargs) -> NsJailResult:
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
```

The builder's config becomes the base config of a temporary Runner. If an existing Runner is provided, its execution settings (nsjail_path, render_mode, etc.) are carried over, but its base_config is not — the builder's config wins entirely.

The Runner import is deferred to avoid circular imports (builder.py imports presets, runner.py imports serializers).

### async_run on builder

```python
async def async_run(self, *, runner: Runner | None = None, **run_kwargs) -> NsJailResult:
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

## Enhancement 3: to_protobuf() Serializer

### What changes

**New file:** `src/nsjail/serializers/protobuf.py`
**New directory:** `src/nsjail/_proto/` (compiled proto)
**Modify:** `src/nsjail/serializers/__init__.py` (add to_protobuf export)

### Approach

Piggyback on the existing textproto serializer. Convert dataclass to textproto string, then parse into a compiled protobuf message using `google.protobuf.text_format.Parse`.

```python
from google.protobuf import text_format
from nsjail.serializers.textproto import to_textproto


def to_protobuf(cfg):
    """Convert a NsJailConfig to a compiled protobuf message.

    Requires the [proto] extra: pip install nsjail-python[proto]
    """
    from nsjail._proto import config_pb2

    text = to_textproto(cfg)
    msg = config_pb2.NsJailConfig()
    text_format.Parse(text, msg)
    return msg
```

### Compiled proto

The `_proto/` directory contains `config_pb2.py`, generated from `_vendor/nsjail/config.proto` at dev time:

```bash
protoc --python_out=src/nsjail/_proto/ --proto_path=_vendor/nsjail/ config.proto
```

The compiled file is committed to the repo. It is regenerated when the vendored config.proto is updated.

`src/nsjail/_proto/__init__.py` is an empty file.

### Import guarding

`to_protobuf` is NOT imported by default in `serializers/__init__.py`. It's available via direct import:

```python
from nsjail.serializers.protobuf import to_protobuf
```

The existing `to_file(cfg, path, validate=True)` path already handles the ImportError case.

## Enhancement 4: Code Generator Emission

### What changes

**File:** `_codegen/generate.py` (major additions)
**Overwrites:** `src/nsjail/config.py`, `src/nsjail/enums.py`, `src/nsjail/_field_meta.py`

### Emitter functions

Three new functions added to `generate.py`:

**`emit_enums(enums: list[ProtoEnum]) -> str`**

Generates `enums.py`. Only emits top-level enums (Mode, LogLevel). The RLimit enum inside NsJailConfig is also emitted here as `RLimitType`.

**`emit_config(messages: list[ProtoMessage]) -> str`**

Generates `config.py` with all dataclasses.

Type mapping:
| Proto type | Python type | Notes |
|---|---|---|
| `string` | `str` | Default `""` uses `""`, no default uses `None` |
| `uint32`, `int32`, `uint64`, `int64` | `int` | |
| `bool` | `bool` | |
| `bytes` | `bytes` | |
| `repeated X` | `list[X]` | `field(default_factory=list)` |
| Message reference | Dataclass name | Optional: `X \| None = None` |
| Enum reference | IntEnum name | |

Nested enums (TrafficAction, NstunAction, etc.) are emitted as module-level IntEnums in config.py, before the dataclasses that use them.

**`emit_field_meta(messages: list[ProtoMessage], cli_flags: dict) -> str`**

Generates `_field_meta.py` by walking all messages/fields and merging with the `cli_flags` table from `_codegen/cli_flags.py`.

### Updated main()

```python
def main():
    proto_path = ...
    items = parse_proto(proto_path.read_text())

    enums = [i for i in items if isinstance(i, ProtoEnum)]
    messages = [i for i in items if isinstance(i, ProtoMessage)]

    output_dir = Path("src/nsjail")
    (output_dir / "enums.py").write_text(emit_enums(enums))
    (output_dir / "config.py").write_text(emit_config(messages))
    (output_dir / "_field_meta.py").write_text(emit_field_meta(messages, CLI_FLAGS))

    # Validate: import generated code
    importlib.invalidate_caches()
    # ... check imports succeed

    print("Generated successfully.")
```

### Validation

After writing files, the generator:
1. Imports the generated modules to verify they compile
2. Checks that every proto field has a corresponding dataclass field
3. Checks that every dataclass field has a `_field_meta` registry entry
4. Reports any mismatches

## Testing Strategy

- **async_run:** Test with mocked subprocess (patch `asyncio.create_subprocess_exec`). Test that `_prepare_run` produces correct args for both sync and async paths.
- **Builder .run():** Test with mocked Runner. Verify config is passed correctly and Runner settings are preserved.
- **to_protobuf:** Test round-trip: build config, call to_protobuf, compare text_format.MessageToString output with to_textproto output. Skip if protobuf not installed.
- **Code generator:** Run generator against vendored config.proto. Verify output matches current hand-written files (or is a superset). Run existing test suite against generated files to catch regressions.

## Scope Boundaries

**In scope:**
- async_run() on Runner (with _prepare_run extraction)
- .run() and .async_run() on Jail builder
- to_protobuf() serializer + compiled proto
- Code generator emission (enums, config, field_meta)
- Tests for all four

**Out of scope:**
- Seccomp policy helpers
- Cgroup stats recovery
- Pre-built binary CI pipeline
- Any changes to the data model itself
