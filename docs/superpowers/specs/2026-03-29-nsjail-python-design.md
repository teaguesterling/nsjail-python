# nsjail-python Design Spec

**Date:** 2026-03-29
**Status:** Draft
**Package name:** `nsjail-python` (import: `nsjail`)
**Python:** 3.12+

## Context

nsjail is Google's process isolation tool that uses Linux namespaces, cgroups, seccomp-bpf, and mount manipulation to sandbox processes. Its configuration is defined by a protobuf schema (`config.proto`) with ~120 fields across namespace control, mount management, resource limits, seccomp policies, networking, and more.

Currently, using nsjail from Python means hand-writing protobuf text-format config files or constructing CLI argument lists as raw strings. There is no typed Python API for building, validating, or rendering nsjail configurations.

`nsjail-python` provides a standalone, layered Python API for nsjail — useful both for production sandbox orchestrators (CI runners, code execution services) and security researchers experimenting with isolation.

## Architecture Overview

Three layers, each building on the one below:

```
┌─────────────────────────────────────┐
│  Builder (Jail)                     │  Fluent API + command builders
├─────────────────────────────────────┤
│  Presets (sandbox, apply_*)         │  Opinionated factory functions
├─────────────────────────────────────┤
│  Core Model (NsJailConfig)          │  1:1 dataclasses from config.proto
└─────────────────────────────────────┘
        │                │
   Serializers        Runner
   ├─ textproto       ├─ Runner class
   ├─ cli             ├─ run() / async_run()
   └─ protobuf [opt]  └─ Config merging + fork()
```

## Package Layout

```
nsjail-python/                         # Monorepo root
    pyproject.toml                     # Main nsjail-python package
    src/
        nsjail/
            __init__.py                # Re-exports public API
            config.py                  # Generated dataclasses (1:1 with config.proto)
            enums.py                   # Generated IntEnum classes
            _field_meta.py             # Generated field metadata registry
            presets.py                 # Factory functions + apply_* composable modifiers
            builder.py                 # Fluent Jail() builder
            runner.py                  # Runner class, run(), async_run()
            exceptions.py              # NsjailError, UnsupportedCLIField, NsjailNotFound
            serializers/
                __init__.py            # Re-exports: to_textproto, to_cli_args, to_file
                textproto.py           # Pure Python text-format serializer
                cli.py                 # CLI argument renderer
                protobuf.py            # Protobuf message converter (requires [proto])
    packages/
        nsjail-bin/                    # Pre-built binary companion package
            pyproject.toml
            src/nsjail_bin/__init__.py
        nsjail-bin-build/              # Build-from-source companion package
            pyproject.toml
            src/nsjail_bin_build/__init__.py
        nsjail-bin-none/               # No-op companion package
            pyproject.toml
            src/nsjail_bin_none/__init__.py
    _vendor/
        nsjail/                        # Git submodule: google/nsjail @ release tag
    _codegen/                          # Dev-only, excluded from wheels
        generate.py
        cli_flags.py
    tests/
        test_config.py
        test_serializers.py
        test_presets.py
        test_builder.py
        test_runner.py
```

## Dependencies

### nsjail-python (main package)

```toml
[project]
name = "nsjail-python"
requires-python = ">=3.12"
dependencies = ["nsjail-bin"]  # Pre-built binary by default

[project.optional-dependencies]
proto = ["protobuf>=4.0"]
build = ["nsjail-bin-build"]   # Build from source instead of pre-built
system = ["nsjail-bin-none"]   # No binary — use system-provided nsjail
dev = ["grpcio-tools", "pytest", "protobuf>=4.0"]
```

### Companion packages

Three mutually-exclusive companion packages provide (or explicitly skip) the nsjail binary. They all satisfy the `nsjail-bin` dependency via pip's package resolution:

| Package | What it does | When to use |
|---|---|---|
| `nsjail-bin` | Ships pre-built nsjail binary in platform wheels | Default. Just works. |
| `nsjail-bin-build` | Builds nsjail from vendored source during install | Unusual platforms, custom patches, or no pre-built wheel available |
| `nsjail-bin-none` | Empty package — installs nothing | System-managed nsjail (apt, container image, etc.) |

**Install patterns:**
```bash
# Default: batteries included
pip install nsjail-python
# -> pulls nsjail-bin (platform wheel with pre-built binary)

# System nsjail, skip the bundled binary
pip install nsjail-python[system]
# -> pulls nsjail-bin-none (satisfies dep, installs nothing)

# Build from source
pip install nsjail-python[build]
# -> pulls nsjail-bin-build (compiles during install)

# With protobuf validation
pip install nsjail-python[proto]
```

- **Core (`nsjail-python`):** Pure Python. Config model, text-proto serializer, CLI renderer, presets, builder, and runner.
- **`nsjail[proto]` extra:** Installs `protobuf`. Enables schema validation against the compiled proto definition and conversion to protobuf message objects. The pure-Python text-proto serializer handles `.cfg` file output without this extra.
- **`nsjail[build]` extra:** Installs `nsjail-bin-build` instead of `nsjail-bin`. Builds nsjail from vendored source. Requires system build tools.
- **`nsjail[system]` extra:** Installs `nsjail-bin-none` instead of `nsjail-bin`. Documents intent: "nsjail is managed outside of pip."
- **Dev:** `grpcio-tools` for code generation from config.proto.

## nsjail Binary Distribution

### Problem

nsjail is a C++ binary that must be compiled from source. Most users don't want to install gcc, protobuf-compiler, libnl3-dev, and other build dependencies just to use a Python wrapper. The package should provide nsjail itself when possible.

### Companion package architecture

Three companion packages handle binary distribution. They are mutually exclusive — pip resolves which one to install based on the extras the user selects.

#### `nsjail-bin` (default)

Ships pre-built, statically-linked nsjail binaries in platform-specific wheels.

**Wheel contents:**
```
nsjail_bin/
    __init__.py         # Exposes binary_path() -> Path
    _bin/
        nsjail          # Statically-linked binary
```

**Platform wheels built in CI:**
- `manylinux_2_28_x86_64`
- `manylinux_2_28_aarch64`

nsjail only runs on Linux (it uses Linux-specific kernel APIs: namespaces, cgroups, seccomp), so no macOS/Windows wheels are needed.

**Build approach:** Static linking where possible. nsjail's dependencies (protobuf, libnl3, libcap) can be statically linked to produce a self-contained binary. The kafel submodule is already linked statically.

**CI pipeline:** A GitHub Actions workflow builds nsjail inside a manylinux container, runs the test suite against the built binary, and attaches it to the wheel.

#### `nsjail-bin-build`

Builds nsjail from vendored source during install.

**Vendored source:** nsjail is included as a git submodule at `_vendor/nsjail/` (which itself has a `kafel/` submodule). The submodule is pinned to a specific release tag.

**Build process:** A custom setuptools build extension runs:
```bash
cd _vendor/nsjail
make -j$(nproc)
```
The resulting binary is installed to `nsjail_bin_build/_bin/nsjail`.

**System requirements (documented clearly in error messages):**
- `gcc` / `g++` (C++20 support)
- `make`, `pkg-config`, `bison`, `flex`, `autoconf`, `libtool`
- `libprotobuf-dev`, `protobuf-compiler`
- `libnl-route-3-dev` (libnl3)
- `git` (for kafel submodule init)

If build dependencies are missing, the install fails with a clear error listing what's needed and suggesting the default `nsjail-bin` package as an alternative.

#### `nsjail-bin-none`

Empty package. Installs nothing. Satisfies the dependency so pip doesn't pull `nsjail-bin`. Exists to document intent: "I'm providing nsjail myself."

### Binary resolution order

The Runner discovers the nsjail binary using this precedence:

1. **Explicit path** — `Runner(nsjail_path="/custom/path/nsjail")` always wins
2. **System nsjail** — `shutil.which("nsjail")` on PATH
3. **Bundled binary** — probes `nsjail_bin.binary_path()` or `nsjail_bin_build.binary_path()` (whichever companion package is installed)
4. **Not found** — raises `NsjailNotFound` with install instructions

This means: if nsjail is already installed system-wide, it's used automatically even when the bundled binary is present. The bundled binary is a fallback.

### Repository layout

The monorepo contains all three companion packages alongside the main package:

```
nsjail-python/                      # Repository root
    pyproject.toml                  # Main nsjail-python package
    src/
        nsjail/                     # Main package source
            ...
    packages/
        nsjail-bin/                 # Pre-built binary companion
            pyproject.toml
            src/nsjail_bin/
                __init__.py
                _bin/.gitkeep
        nsjail-bin-build/           # Build-from-source companion
            pyproject.toml
            src/nsjail_bin_build/
                __init__.py
        nsjail-bin-none/            # No-op companion
            pyproject.toml
            src/nsjail_bin_none/
                __init__.py
    _vendor/                        # Git submodule, used by nsjail-bin and nsjail-bin-build
        nsjail/                     # google/nsjail pinned to release tag
            kafel/                  # google/kafel (nsjail's own submodule)
            Makefile
            config.proto
    _codegen/
        generate.py
        cli_flags.py
```

### Version pinning

The vendored nsjail submodule is pinned to a specific release tag (e.g., `3.4`). All companion packages share the same version number as the main package to keep compatibility clear.

When upgrading nsjail:
1. Update the submodule pin
2. Re-run the code generator against the new `config.proto`
3. Review CLI flag changes
4. Rebuild pre-built binaries in CI
5. Release new versions of all four packages together

## Layer 1: Core Data Model

### Source of truth

A code generator (`_codegen/generate.py`) reads nsjail's `config.proto` and emits three files:
- `config.py` — Python `@dataclass` classes, one per proto message
- `enums.py` — `IntEnum` classes, one per proto enum
- `_field_meta.py` — a registry mapping `(message_name, field_name)` to `FieldMeta(number, proto_type, default, cli_flag, cli_supported)`

Generated files are committed to the repo with a `# GENERATED — DO NOT EDIT` header. When nsjail updates config.proto, developers re-run the generator and review the diff.

The CLI flag mapping table in `_codegen/cli_flags.py` is hand-maintained because flag names require human judgment. The generator merges this table into `_field_meta.py`.

### Dataclass design

Every proto message becomes a `@dataclass`. Every field uses `None` to mean "not set," solving proto2's ambiguity where you cannot distinguish "set to default" from "unset." Boolean fields that default `True` in the proto (e.g., `clone_newnet`) keep that default — an unmodified `NsJailConfig()` matches nsjail's behavior.

```python
@dataclass
class MountPt:
    src: str | None = None
    prefix_src_env: str | None = None
    src_content: bytes | None = None
    dst: str | None = None
    prefix_dst_env: str | None = None
    fstype: str | None = None
    options: str | None = None
    is_bind: bool = False
    rw: bool = False
    is_dir: bool | None = None
    mandatory: bool = True
    is_symlink: bool = False
    nosuid: bool = False
    nodev: bool = False
    noexec: bool = False

@dataclass
class IdMap:
    inside_id: str = ""
    outside_id: str = ""
    count: int = 1
    use_newidmap: bool = False

@dataclass
class Exe:
    path: str | None = None
    arg: list[str] = field(default_factory=list)
    arg0: str | None = None
    exec_fd: bool = False

@dataclass
class NsJailConfig:
    # Identity
    name: str | None = None
    description: list[str] = field(default_factory=list)
    mode: Mode = Mode.ONCE
    hostname: str = "NSJAIL"
    cwd: str = "/"

    # Limits
    time_limit: int = 600

    # Namespaces
    clone_newnet: bool = True
    clone_newuser: bool = True
    clone_newns: bool = True
    clone_newpid: bool = True
    clone_newipc: bool = True
    clone_newuts: bool = True
    clone_newcgroup: bool = True
    clone_newtime: bool = False

    # Mounts, UID/GID maps
    mount: list[MountPt] = field(default_factory=list)
    uidmap: list[IdMap] = field(default_factory=list)
    gidmap: list[IdMap] = field(default_factory=list)

    # Cgroups
    cgroup_mem_max: int = 0
    cgroup_pids_max: int = 0
    cgroup_cpu_ms_per_sec: int = 0
    use_cgroupv2: bool = False
    detect_cgroupv2: bool = False

    # Seccomp
    seccomp_policy_file: str | None = None
    seccomp_string: list[str] = field(default_factory=list)
    seccomp_log: bool = False

    # Execution
    exec_bin: Exe | None = None
    # ... all remaining ~98 fields from config.proto
```

No validation at construction time. Validation happens at serialization time or via an explicit `validate()` call.

### Enums

```python
class Mode(IntEnum):
    LISTEN = 0
    ONCE = 1
    RERUN = 2
    EXECVE = 3

class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    FATAL = 4

class RLimitType(IntEnum):
    VALUE = 0
    SOFT = 1
    HARD = 2
    INF = 3
```

## Layer 2: Serializers

Three serialization targets, all consuming the same dataclass model.

### `textproto.py` — Pure Python, no dependencies

Walks dataclass fields using `_field_meta` to emit protobuf text format. A field is emitted only if its value differs from the proto-defined default. `None` fields are never emitted.

```python
from nsjail.serializers import to_textproto

print(to_textproto(cfg))
# hostname: "box"
# time_limit: 30
# mount {
#   src: "/"
#   dst: "/"
#   is_bind: true
# }
```

### `cli.py` — CLI argument rendering

Produces a `list[str]` for `subprocess.run(["nsjail"] + args + ["--", *command])`. Uses `_field_meta` to look up flag names.

Fields without CLI equivalents are handled by an `on_unsupported` parameter:
- `"raise"` (default) — raises `UnsupportedCLIField`
- `"warn"` — logs a warning, skips the field
- `"skip"` — silently skips

```python
from nsjail.serializers import to_cli_args

args = to_cli_args(cfg)
# ["--hostname", "box", "--time_limit", "30", "--bindmount_ro", "/:/"]
```

### `protobuf.py` — Requires `nsjail[proto]`

Converts the dataclass to a compiled `config_pb2.NsJailConfig` protobuf message. Raises `ImportError` if `protobuf` is not installed.

```python
from nsjail.serializers import to_protobuf
proto_msg = to_protobuf(cfg)
```

### `to_file()` convenience

```python
from nsjail.serializers import to_file

to_file(cfg, "/tmp/sandbox.cfg")                    # Writes text-proto format
to_file(cfg, "/tmp/sandbox.cfg", validate=True)      # Validates via [proto] extra first
```

## Layer 3: Presets

### Apply functions (composable modifiers)

Functions that take a `NsJailConfig` and mutate it. These are the atomic building blocks.

```python
from nsjail.presets import apply_readonly_root, apply_cgroup_limits, apply_seccomp_log

cfg = NsJailConfig()
apply_readonly_root(cfg, writable=["/workspace"])
apply_cgroup_limits(cfg, memory_mb=512, cpu_ms_per_sec=500, pids_max=64)
apply_seccomp_log(cfg)
```

### Factory functions

Compose apply functions into complete configurations.

```python
from nsjail.presets import sandbox

cfg = sandbox(
    command=["python", "script.py"],
    cwd="/workspace",
    timeout_sec=60,
    memory_mb=512,
    network=False,
    writable_dirs=["/workspace", "/tmp"],
)
```

### Fluent builder (`builder.py`)

Wraps apply functions in a chainable API with command builder integration.

```python
from nsjail.builder import Jail

cfg = (
    Jail()
    .sh("pytest tests/ -v")                # exec_bin = /bin/sh -c "..."
    .cwd("/workspace")
    .timeout(60)
    .memory(512, "MB")
    .cpu(500)
    .pids(64)
    .no_network()
    .readonly_root()
    .writable("/workspace")
    .writable("/tmp", tmpfs=True, size="64M")
    .env("HOME=/home/user")
    .env("CI=1")
    .seccomp_log()
    .mount("/data", "/data", readonly=True)
    .uid_map(inside=0, outside=1000)
    .build()   # Returns NsJailConfig
)
```

**Command builder methods:**
- `.command("python", "script.py")` — sets `exec_bin` directly
- `.sh("echo hello && ls")` — wraps in `/bin/sh -c "..."`
- `.python("script.py")` — sets `exec_bin` to `/usr/bin/python3`
- `.bash("-c", "script")` — sets `exec_bin` to `/bin/bash`

Each builder method calls the corresponding `apply_*` function internally — no duplicated logic.

## Runner

### Runner class

A configurable executor that holds nsjail settings and optionally a base config. Supports dependency injection.

```python
from nsjail.runner import Runner

runner = Runner(
    nsjail_path="/usr/bin/nsjail",
    render_mode="textproto",       # or "cli"
    capture_output=True,
    keep_config=False,
)
```

### Baked configs

A Runner can have a base config baked in. All `run()` calls inherit from it.

```python
runner = Runner(
    base_config=Jail()
        .command("python", "-m", "pytest")
        .memory(1024, "MB")
        .timeout(300)
        .readonly_root()
        .writable("/workspace")
        .env("CI=1")
        .build(),
)

# Run as-is
result = runner.run()

# Run with extra args appended to the baked command
result = runner.run(extra_args=["tests/unit/", "-x"])

# Run with config overrides
result = runner.run(
    overrides=NsJailConfig(time_limit=600, cgroup_mem_max=2 * 1024**3),
    extra_args=["tests/integration/"],
)
```

### Config merge semantics

When `overrides` is provided, fields merge with the base config:

| Field type | Merge behavior |
|---|---|
| Scalar (`str`, `int`, `bool`) | Override replaces base. For scalars where `None` is not a valid value (bools, ints with proto defaults), merging uses a separate "fields explicitly set" tracker — only fields the user actually assigned on the override object are applied. This is implemented via a `__post_init__` sentinel or a thin wrapper that tracks touched fields. |
| `list` fields (`mount`, `envar`, `seccomp_string`) | Override list is **appended** to base list |
| Nested message (`exec_bin`) | Merged field-by-field (same rules recursively) |
| `extra_args` (Runner-specific) | Appended to `exec_bin.arg` |

### Runner.fork()

Creates a derived Runner with additional overrides baked in.

```python
base = Runner(base_config=sandbox(memory_mb=512, timeout_sec=60))

heavy = base.fork(overrides=NsJailConfig(
    cgroup_mem_max=2 * 1024**3,
    time_limit=300,
))
```

### NsJailResult

```python
@dataclass
class NsJailResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    config_path: Path | None       # Temp config file path (textproto mode)
    nsjail_args: list[str]         # Actual command line used
    timed_out: bool                # nsjail killed process for exceeding time_limit
    oom_killed: bool               # Cgroup OOM killed the process
    signaled: bool                 # Process killed by signal
    inner_returncode: int | None   # Sandboxed process's own exit code
```

### Builder integration (deferred)

The builder could terminate a chain by executing via a Runner. Deferred until Runner is stable:

```python
# Future API:
result = (
    Jail()
    .sh("pytest tests/")
    .memory(512, "MB")
    .timeout(60)
    .run(runner=runner)
)
```

## Code Generator

Dev-only tooling in `_codegen/`, excluded from the wheel.

**Inputs:**
- `config.proto` — vendored from nsjail repo
- `cli_flags.py` — hand-maintained mapping of proto field names to CLI flag names

**Outputs (committed to repo):**
- `config.py` — dataclasses with `# GENERATED — DO NOT EDIT` header
- `enums.py` — IntEnum classes
- `_field_meta.py` — field metadata registry

**Update workflow:**
```bash
curl -o _codegen/config.proto https://raw.githubusercontent.com/google/nsjail/master/config.proto
python -m nsjail._codegen.generate
git diff src/nsjail/config.py src/nsjail/enums.py src/nsjail/_field_meta.py
```

The generator uses `grpcio-tools` or protobuf descriptor reflection to parse the proto. It does not need to handle the full proto2 spec — nsjail's config.proto uses a simple subset (no oneofs, extensions, or maps).

## Testing Strategy

- **Unit tests (no nsjail needed):** Config construction, serialization round-trips (dataclass → textproto → parse back), CLI argument generation, preset/builder output, config merging.
- **Integration tests (nsjail required):** Run nsjail with generated configs, verify sandboxing behavior (process isolation, mount visibility, resource limits). Skip gracefully when nsjail is not installed.
- **Codegen tests:** Verify the generator produces valid Python that matches expected field counts and types. Run as part of CI.
- **Serializer property tests:** Compare `to_textproto` output against `protobuf.text_format.MessageToString` output for the same config (when `[proto]` extra is installed) to catch serializer drift.

## Scope Boundaries

**In scope for v0.1:**
- Generated dataclass model covering all config.proto fields
- Text-proto serializer (pure Python)
- CLI argument renderer
- Core presets: `sandbox()`, `apply_readonly_root()`, `apply_cgroup_limits()`
- Fluent builder with `.sh()`, `.command()`, `.python()`
- Runner with base config, overrides, extra_args, fork()
- Sync `run()` execution
- Binary resolution (system → bundled → not found)
- `nsjail[build]` extra: vendored submodule + build-from-source support
- CI pipeline for `nsjail[binary]` pre-built wheels (x86_64, aarch64)

**Deferred:**
- `async_run()` on Runner — add when there's a concrete async use case
- `.run()` on the builder chain — needs Runner to be stable first
- Seccomp policy helpers (Kafel generation)
- Cgroup stats recovery (reading memory.peak/cpu.stat before nsjail cleanup)
- Protobuf serializer (`to_protobuf()`) — add with `[proto]` extra
