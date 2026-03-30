# nsjail-python Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, layered Python package that wraps nsjail config generation, CLI rendering, and subprocess execution with zero required dependencies.

**Architecture:** Code generator reads nsjail's config.proto and emits Python dataclasses + field metadata. Three serializers (textproto, CLI, protobuf) consume the model. Presets and a fluent builder provide high-level ergonomics. A Runner class handles subprocess execution with config merging. Companion packages distribute the nsjail binary.

**Tech Stack:** Python 3.12+, dataclasses, IntEnum, subprocess, protobuf (optional), grpcio-tools (dev)

**Spec:** `docs/superpowers/specs/2026-03-29-nsjail-python-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/nsjail/__init__.py`
- Create: `src/nsjail/serializers/__init__.py`
- Create: `tests/__init__.py`
- Create: `_codegen/__init__.py`

- [ ] **Step 1: Initialize git repo**

Run: `cd /mnt/aux-data/teague/Projects/nsjail-python && git init`

- [ ] **Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nsjail-python"
version = "0.1.0"
description = "Python wrapper for Google's nsjail sandboxing tool"
requires-python = ">=3.12"
license = "MIT"
dependencies = []

[project.optional-dependencies]
proto = ["protobuf>=4.0"]
dev = [
    "grpcio-tools",
    "pytest",
    "protobuf>=4.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/nsjail"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Note: The `dependencies = ["nsjail-bin"]` default dependency from the spec is omitted for now — companion packages are built in a later task. We'll add it when those packages exist.

- [ ] **Step 3: Create package directories and init files**

Create `src/nsjail/__init__.py`:
```python
"""nsjail-python: Python wrapper for Google's nsjail sandboxing tool."""
```

Create `src/nsjail/serializers/__init__.py`:
```python
"""Serializers for NsJailConfig: textproto, CLI args, protobuf."""
```

Create `tests/__init__.py`:
```python
```

Create `_codegen/__init__.py`:
```python
```

- [ ] **Step 4: Create .gitignore**

```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
*.so
_vendor/
```

- [ ] **Step 5: Verify project installs**

Run: `cd /mnt/aux-data/teague/Projects/nsjail-python && pip install -e ".[dev]"`
Expected: Installs successfully with pytest available.

Run: `python -c "import nsjail; print('ok')"`
Expected: Prints "ok".

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ tests/ _codegen/ .gitignore
git commit -m "feat: project scaffolding for nsjail-python"
```

---

### Task 2: Exceptions Module

**Files:**
- Create: `src/nsjail/exceptions.py`
- Create: `tests/test_exceptions.py`

- [ ] **Step 1: Write test for exceptions**

Create `tests/test_exceptions.py`:
```python
from nsjail.exceptions import (
    NsjailError,
    UnsupportedCLIField,
    NsjailNotFound,
)


def test_nsjail_error_is_base_exception():
    assert issubclass(NsjailError, Exception)


def test_unsupported_cli_field_contains_field_name():
    err = UnsupportedCLIField("src_content")
    assert "src_content" in str(err)
    assert isinstance(err, NsjailError)


def test_nsjail_not_found_contains_install_hint():
    err = NsjailNotFound()
    msg = str(err)
    assert "nsjail" in msg.lower()
    assert isinstance(err, NsjailError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exceptions.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement exceptions**

Create `src/nsjail/exceptions.py`:
```python
"""Exception types for nsjail-python."""


class NsjailError(Exception):
    """Base exception for all nsjail-python errors."""


class UnsupportedCLIField(NsjailError):
    """Raised when a config field has no CLI flag equivalent."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(
            f"Config field {field_name!r} has no CLI flag equivalent. "
            f"Use textproto rendering instead, or pass on_unsupported='skip'."
        )


class NsjailNotFound(NsjailError):
    """Raised when the nsjail binary cannot be found."""

    def __init__(self) -> None:
        super().__init__(
            "nsjail binary not found. Install it via:\n"
            "  pip install nsjail-python          # includes pre-built binary\n"
            "  pip install nsjail-python[build]    # build from source\n"
            "  apt-get install nsjail              # system package\n"
            "Or specify the path: Runner(nsjail_path='/path/to/nsjail')"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exceptions.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/exceptions.py tests/test_exceptions.py
git commit -m "feat: add exception types"
```

---

### Task 3: Enums Module

**Files:**
- Create: `src/nsjail/enums.py`
- Create: `tests/test_enums.py`

- [ ] **Step 1: Write test for enums**

Create `tests/test_enums.py`:
```python
from enum import IntEnum

from nsjail.enums import Mode, LogLevel, RLimitType


def test_mode_values():
    assert Mode.LISTEN == 0
    assert Mode.ONCE == 1
    assert Mode.RERUN == 2
    assert Mode.EXECVE == 3


def test_log_level_values():
    assert LogLevel.DEBUG == 0
    assert LogLevel.INFO == 1
    assert LogLevel.WARNING == 2
    assert LogLevel.ERROR == 3
    assert LogLevel.FATAL == 4


def test_rlimit_type_values():
    assert RLimitType.VALUE == 0
    assert RLimitType.SOFT == 1
    assert RLimitType.HARD == 2
    assert RLimitType.INF == 3


def test_all_are_int_enums():
    assert issubclass(Mode, IntEnum)
    assert issubclass(LogLevel, IntEnum)
    assert issubclass(RLimitType, IntEnum)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_enums.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement enums**

Create `src/nsjail/enums.py`:
```python
# GENERATED from nsjail config.proto — DO NOT EDIT
# Re-run: python -m _codegen.generate

from enum import IntEnum


class Mode(IntEnum):
    """nsjail execution mode."""
    LISTEN = 0
    ONCE = 1
    RERUN = 2
    EXECVE = 3


class LogLevel(IntEnum):
    """Log verbosity level."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    FATAL = 4


class RLimitType(IntEnum):
    """How to interpret an rlimit value."""
    VALUE = 0
    SOFT = 1
    HARD = 2
    INF = 3
```

Note: This is hand-written for now. The code generator (Task 10) will produce this file in the future; at that point we replace this file with the generated version.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_enums.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/enums.py tests/test_enums.py
git commit -m "feat: add enum types (Mode, LogLevel, RLimitType)"
```

---

### Task 4: Core Data Model (config.py)

**Files:**
- Create: `src/nsjail/config.py`
- Create: `tests/test_config.py`

This is the largest single file — it contains all dataclasses mirroring config.proto. For now we hand-write it; Task 10 (code generator) will eventually produce it automatically.

- [ ] **Step 1: Write tests for core dataclasses**

Create `tests/test_config.py`:
```python
from dataclasses import fields

from nsjail.config import NsJailConfig, MountPt, IdMap, Exe, TrafficRule, UserNet
from nsjail.enums import Mode, LogLevel, RLimitType


class TestMountPt:
    def test_defaults(self):
        m = MountPt()
        assert m.src is None
        assert m.dst is None
        assert m.fstype is None
        assert m.is_bind is False
        assert m.rw is False
        assert m.mandatory is True

    def test_bind_mount(self):
        m = MountPt(src="/lib", dst="/lib", is_bind=True, rw=False)
        assert m.src == "/lib"
        assert m.dst == "/lib"
        assert m.is_bind is True
        assert m.rw is False

    def test_tmpfs_mount(self):
        m = MountPt(dst="/tmp", fstype="tmpfs", rw=True, options="size=50000000")
        assert m.fstype == "tmpfs"
        assert m.rw is True
        assert m.options == "size=50000000"


class TestIdMap:
    def test_defaults(self):
        m = IdMap()
        assert m.inside_id == ""
        assert m.outside_id == ""
        assert m.count == 1
        assert m.use_newidmap is False

    def test_uid_mapping(self):
        m = IdMap(inside_id="0", outside_id="99999", count=1)
        assert m.inside_id == "0"
        assert m.outside_id == "99999"


class TestExe:
    def test_defaults(self):
        e = Exe()
        assert e.path is None
        assert e.arg == []
        assert e.arg0 is None
        assert e.exec_fd is False

    def test_with_args(self):
        e = Exe(path="/bin/bash", arg=["-c", "echo hello"])
        assert e.path == "/bin/bash"
        assert e.arg == ["-c", "echo hello"]

    def test_arg_list_is_independent(self):
        e1 = Exe()
        e2 = Exe()
        e1.arg.append("x")
        assert e2.arg == []


class TestNsJailConfig:
    def test_defaults_match_nsjail(self):
        cfg = NsJailConfig()
        assert cfg.mode == Mode.ONCE
        assert cfg.hostname == "NSJAIL"
        assert cfg.cwd == "/"
        assert cfg.time_limit == 600

    def test_namespace_defaults(self):
        cfg = NsJailConfig()
        assert cfg.clone_newnet is True
        assert cfg.clone_newuser is True
        assert cfg.clone_newns is True
        assert cfg.clone_newpid is True
        assert cfg.clone_newipc is True
        assert cfg.clone_newuts is True
        assert cfg.clone_newcgroup is True
        assert cfg.clone_newtime is False

    def test_cgroup_defaults(self):
        cfg = NsJailConfig()
        assert cfg.cgroup_mem_max == 0
        assert cfg.cgroup_pids_max == 0
        assert cfg.cgroup_cpu_ms_per_sec == 0

    def test_list_fields_independent(self):
        c1 = NsJailConfig()
        c2 = NsJailConfig()
        c1.mount.append(MountPt(dst="/tmp"))
        assert c2.mount == []

    def test_full_construction(self):
        cfg = NsJailConfig(
            name="test",
            mode=Mode.ONCE,
            hostname="sandbox",
            time_limit=30,
            clone_newnet=True,
            mount=[
                MountPt(src="/", dst="/", is_bind=True, rw=False),
                MountPt(dst="/tmp", fstype="tmpfs", rw=True),
            ],
            uidmap=[IdMap(inside_id="0", outside_id="1000")],
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo hi"]),
        )
        assert cfg.name == "test"
        assert len(cfg.mount) == 2
        assert cfg.exec_bin.path == "/bin/sh"

    def test_rlimit_fields_exist(self):
        cfg = NsJailConfig()
        assert cfg.rlimit_as == 4096
        assert cfg.rlimit_as_type == RLimitType.VALUE
        assert cfg.rlimit_fsize == 1
        assert cfg.rlimit_nofile == 32
        assert cfg.rlimit_nproc_type == RLimitType.SOFT
        assert cfg.rlimit_stack_type == RLimitType.SOFT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement config.py**

Create `src/nsjail/config.py`:
```python
# GENERATED from nsjail config.proto — DO NOT EDIT
# Re-run: python -m _codegen.generate

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from nsjail.enums import LogLevel, Mode, RLimitType


# --- Nested messages ---


@dataclass
class MountPt:
    """Filesystem mount point configuration.

    Maps to nsjail MountPt proto message.
    """

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
    """UID/GID mapping for user namespaces.

    Maps to nsjail IdMap proto message.
    """

    inside_id: str = ""
    outside_id: str = ""
    count: int = 1
    use_newidmap: bool = False


@dataclass
class Exe:
    """Binary to execute inside the sandbox.

    Maps to nsjail Exe proto message.
    """

    path: str | None = None
    arg: list[str] = field(default_factory=list)
    arg0: str | None = None
    exec_fd: bool = False


class TrafficAction(IntEnum):
    """Action for traffic filtering rules."""

    DROP = 1
    REJECT = 2
    ALLOW = 3


class IpFamily(IntEnum):
    """IP address family."""

    IPV4 = 0
    IPV6 = 1


class TrafficProtocol(IntEnum):
    """Network protocol for traffic rules."""

    UNKNOWN_PROTO = 0
    TCP = 1
    UDP = 2
    ICMP = 3
    ICMPV6 = 4


@dataclass
class TrafficRule:
    """Network traffic filtering rule.

    Maps to nsjail TrafficRule proto message.
    """

    src_ip: str | None = None
    dst_ip: str | None = None
    iif: str | None = None
    oif: str | None = None
    proto: TrafficProtocol = TrafficProtocol.UNKNOWN_PROTO
    sport: int | None = None
    dport: int | None = None
    sport_end: int | None = None
    dport_end: int | None = None
    action: TrafficAction = TrafficAction.DROP
    ip_family: IpFamily = IpFamily.IPV4


class NstunAction(IntEnum):
    """Action for NSTUN rules."""

    DROP = 0
    REJECT = 1
    ALLOW = 2
    REDIRECT = 3
    ENCAP_SOCKS5 = 4


class NstunProtocol(IntEnum):
    """Protocol for NSTUN rules."""

    ANY = 0
    TCP = 1
    UDP = 2
    ICMP = 3


@dataclass
class NstunRule:
    """NSTUN network rule.

    Maps to nsjail NstunRule proto message.
    """

    action: NstunAction = NstunAction.ALLOW
    proto: NstunProtocol = NstunProtocol.ANY
    src_ip: str | None = None
    sport: int | None = None
    sport_end: int | None = None
    dst_ip: str | None = None
    dport: int | None = None
    dport_end: int | None = None
    redirect_ip: str | None = None
    redirect_port: int | None = None


class UserNetBackend(IntEnum):
    """User-mode networking backend."""

    NSTUN = 0
    PASTA = 1


@dataclass
class Pasta:
    """PASTA user-mode networking configuration."""

    nat: bool = True
    enable_tcp: bool = True
    enable_udp: bool = True
    enable_icmp: bool = True
    ip4_enabled: bool = True
    mask4: str = "255.255.255.0"
    enable_ip4_dhcp: bool = False
    ip6_enabled: bool = True
    mask6: str = "64"
    enable_ip6_dhcp: bool = False
    enable_ip6_ra: bool = False
    enable_dns: bool = False
    dns_forward: str = ""
    map_gw: bool = True
    tcp_map_in: str = "none"
    udp_map_in: str = "none"
    tcp_map_out: str = "none"
    udp_map_out: str = "none"


@dataclass
class UserNet:
    """User-mode networking configuration.

    Maps to nsjail UserNet proto message.
    """

    backend: UserNetBackend = UserNetBackend.NSTUN
    ip4: str = "10.255.255.2"
    gw4: str = "10.255.255.1"
    ip6: str = "fc00::2"
    gw6: str = "fc00::1"
    ns_iface: str = "eth0"
    nstun_rule: list[NstunRule] = field(default_factory=list)
    pasta: Pasta | None = None


# --- Top-level config ---


@dataclass
class NsJailConfig:
    """Complete nsjail sandbox configuration.

    Maps 1:1 to nsjail NsJailConfig proto message.
    All fields use proto-defined defaults so an unmodified instance
    matches nsjail's default behavior.
    """

    # --- Identity ---
    name: str | None = None
    description: list[str] = field(default_factory=list)
    mode: Mode = Mode.ONCE
    hostname: str = "NSJAIL"
    cwd: str = "/"

    # --- Listen mode ---
    port: int = 0
    bindhost: str = "::"
    max_conns: int = 0
    max_conns_per_ip: int = 0

    # --- Execution ---
    time_limit: int = 600
    daemon: bool = False
    max_cpus: int = 0
    nice_level: int = 19
    keep_env: bool = False
    envar: list[str] = field(default_factory=list)
    silent: bool = False
    skip_setsid: bool = False
    stderr_to_null: bool = False
    pass_fd: list[int] = field(default_factory=list)
    disable_no_new_privs: bool = False
    forward_signals: bool = False
    disable_tsc: bool = False
    oom_score_adj: int | None = None

    # --- Logging ---
    log_fd: int | None = None
    log_file: str | None = None
    log_level: LogLevel | None = None

    # --- Capabilities ---
    keep_caps: bool = False
    cap: list[str] = field(default_factory=list)

    # --- Rlimits ---
    rlimit_as: int = 4096
    rlimit_as_type: RLimitType = RLimitType.VALUE
    rlimit_core: int = 0
    rlimit_core_type: RLimitType = RLimitType.VALUE
    rlimit_cpu: int = 600
    rlimit_cpu_type: RLimitType = RLimitType.VALUE
    rlimit_fsize: int = 1
    rlimit_fsize_type: RLimitType = RLimitType.VALUE
    rlimit_nofile: int = 32
    rlimit_nofile_type: RLimitType = RLimitType.VALUE
    rlimit_nproc: int = 1024
    rlimit_nproc_type: RLimitType = RLimitType.SOFT
    rlimit_stack: int = 8
    rlimit_stack_type: RLimitType = RLimitType.SOFT
    rlimit_memlock: int = 64
    rlimit_memlock_type: RLimitType = RLimitType.VALUE
    rlimit_rtprio: int = 0
    rlimit_rtprio_type: RLimitType = RLimitType.VALUE
    rlimit_msgqueue: int = 1024
    rlimit_msgqueue_type: RLimitType = RLimitType.VALUE
    disable_rl: bool = False

    # --- Personality ---
    persona_addr_compat_layout: bool = False
    persona_mmap_page_zero: bool = False
    persona_read_implies_exec: bool = False
    persona_addr_limit_3gb: bool = False
    persona_addr_no_randomize: bool = False

    # --- Namespaces ---
    clone_newnet: bool = True
    clone_newuser: bool = True
    clone_newns: bool = True
    clone_newpid: bool = True
    clone_newipc: bool = True
    clone_newuts: bool = True
    clone_newcgroup: bool = True
    clone_newtime: bool = False

    # --- UID/GID mapping ---
    uidmap: list[IdMap] = field(default_factory=list)
    gidmap: list[IdMap] = field(default_factory=list)

    # --- Mounts ---
    mount_proc: bool = False
    mount: list[MountPt] = field(default_factory=list)
    no_pivotroot: bool = False

    # --- Seccomp ---
    seccomp_policy_file: str | None = None
    seccomp_string: list[str] = field(default_factory=list)
    seccomp_log: bool = False

    # --- Cgroups v1 memory ---
    cgroup_mem_max: int = 0
    cgroup_mem_memsw_max: int = 0
    cgroup_mem_swap_max: int = -1
    cgroup_mem_mount: str = "/sys/fs/cgroup/memory"
    cgroup_mem_parent: str = "NSJAIL"

    # --- Cgroups v1 pids ---
    cgroup_pids_max: int = 0
    cgroup_pids_mount: str = "/sys/fs/cgroup/pids"
    cgroup_pids_parent: str = "NSJAIL"

    # --- Cgroups v1 net_cls ---
    cgroup_net_cls_classid: int = 0
    cgroup_net_cls_mount: str = "/sys/fs/cgroup/net_cls"
    cgroup_net_cls_parent: str = "NSJAIL"

    # --- Cgroups v1 cpu ---
    cgroup_cpu_ms_per_sec: int = 0
    cgroup_cpu_mount: str = "/sys/fs/cgroup/cpu"
    cgroup_cpu_parent: str = "NSJAIL"

    # --- Cgroups v2 ---
    cgroupv2_mount: str = "/sys/fs/cgroup"
    use_cgroupv2: bool = False
    detect_cgroupv2: bool = False

    # --- Networking ---
    iface_no_lo: bool = False
    iface_own: list[str] = field(default_factory=list)
    macvlan_iface: str | None = None
    macvlan_vs_ip: str = "192.168.0.2"
    macvlan_vs_nm: str = "255.255.255.0"
    macvlan_vs_gw: str = "192.168.0.1"
    macvlan_vs_ma: str = ""
    macvlan_vs_mo: str = "private"

    # --- Traffic rules ---
    traffic_rule: list[TrafficRule] = field(default_factory=list)

    # --- User-mode networking ---
    user_net: UserNet | None = None

    # --- Execution binary ---
    exec_bin: Exe | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/config.py tests/test_config.py
git commit -m "feat: add core data model (NsJailConfig, MountPt, IdMap, Exe, etc.)"
```

---

### Task 5: Field Metadata Registry (_field_meta.py)

**Files:**
- Create: `src/nsjail/_field_meta.py`
- Create: `tests/test_field_meta.py`

The field metadata registry maps `(message_name, field_name)` to metadata about each field: its proto field number, proto type, default value, and CLI flag name. This drives the serializers generically.

- [ ] **Step 1: Write tests for field metadata**

Create `tests/test_field_meta.py`:
```python
from nsjail._field_meta import FieldMeta, FIELD_REGISTRY


def test_field_meta_has_required_attrs():
    meta = FieldMeta(
        number=1,
        proto_type="string",
        default=None,
        cli_flag="--name",
        cli_supported=True,
        is_repeated=False,
        is_message=False,
    )
    assert meta.number == 1
    assert meta.proto_type == "string"
    assert meta.cli_flag == "--name"


def test_registry_has_nsjailconfig_hostname():
    meta = FIELD_REGISTRY[("NsJailConfig", "hostname")]
    assert meta.proto_type == "string"
    assert meta.default == "NSJAIL"
    assert meta.cli_supported is True


def test_registry_has_mount_dst():
    meta = FIELD_REGISTRY[("MountPt", "dst")]
    assert meta.proto_type == "string"
    assert meta.default is None


def test_registry_has_nsjailconfig_mount():
    meta = FIELD_REGISTRY[("NsJailConfig", "mount")]
    assert meta.is_repeated is True
    assert meta.is_message is True


def test_registry_has_nsjailconfig_clone_newnet():
    meta = FIELD_REGISTRY[("NsJailConfig", "clone_newnet")]
    assert meta.proto_type == "bool"
    assert meta.default is True


def test_unsupported_cli_field():
    meta = FIELD_REGISTRY[("MountPt", "src_content")]
    assert meta.cli_supported is False


def test_all_nsjailconfig_fields_in_registry():
    from dataclasses import fields as dc_fields
    from nsjail.config import NsJailConfig

    for f in dc_fields(NsJailConfig):
        key = ("NsJailConfig", f.name)
        assert key in FIELD_REGISTRY, f"Missing registry entry for {key}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_field_meta.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement _field_meta.py**

Create `src/nsjail/_field_meta.py`. This file is large because it contains a registry entry for every field in every dataclass. The implementation pattern:

```python
# GENERATED from nsjail config.proto — DO NOT EDIT
# Re-run: python -m _codegen.generate

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldMeta:
    """Metadata about a single proto field."""

    number: int
    proto_type: str
    default: object
    cli_flag: str | None
    cli_supported: bool
    is_repeated: bool
    is_message: bool


FIELD_REGISTRY: dict[tuple[str, str], FieldMeta] = {}


def _r(msg: str, name: str, **kwargs: object) -> None:
    """Register a field."""
    FIELD_REGISTRY[(msg, name)] = FieldMeta(**kwargs)  # type: ignore[arg-type]


# --- MountPt fields ---
_r("MountPt", "src", number=1, proto_type="string", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "prefix_src_env", number=2, proto_type="string", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "src_content", number=3, proto_type="bytes", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "dst", number=4, proto_type="string", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "prefix_dst_env", number=5, proto_type="string", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "fstype", number=6, proto_type="string", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "options", number=7, proto_type="string", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "is_bind", number=8, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "rw", number=9, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "is_dir", number=10, proto_type="bool", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "mandatory", number=11, proto_type="bool", default=True, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "is_symlink", number=12, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "nosuid", number=13, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "nodev", number=14, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "noexec", number=15, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)

# --- IdMap fields ---
_r("IdMap", "inside_id", number=1, proto_type="string", default="", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("IdMap", "outside_id", number=2, proto_type="string", default="", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("IdMap", "count", number=3, proto_type="uint32", default=1, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("IdMap", "use_newidmap", number=4, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)

# --- Exe fields ---
_r("Exe", "path", number=1, proto_type="string", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("Exe", "arg", number=2, proto_type="string", default=[], cli_flag=None, cli_supported=False, is_repeated=True, is_message=False)
_r("Exe", "arg0", number=3, proto_type="string", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("Exe", "exec_fd", number=4, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)

# --- NsJailConfig fields ---
# Identity
_r("NsJailConfig", "name", number=1, proto_type="string", default=None, cli_flag="--name", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "description", number=2, proto_type="string", default=[], cli_flag=None, cli_supported=False, is_repeated=True, is_message=False)
_r("NsJailConfig", "mode", number=3, proto_type="enum", default=1, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "hostname", number=8, proto_type="string", default="NSJAIL", cli_flag="--hostname", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cwd", number=9, proto_type="string", default="/", cli_flag="--cwd", cli_supported=True, is_repeated=False, is_message=False)
# Listen mode
_r("NsJailConfig", "port", number=10, proto_type="uint32", default=0, cli_flag="--port", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "bindhost", number=11, proto_type="string", default="::", cli_flag="--bindhost", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "max_conns", number=12, proto_type="uint32", default=0, cli_flag="--max_conns", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "max_conns_per_ip", number=13, proto_type="uint32", default=0, cli_flag="--max_conns_per_ip", cli_supported=True, is_repeated=False, is_message=False)
# Execution
_r("NsJailConfig", "time_limit", number=14, proto_type="uint32", default=600, cli_flag="--time_limit", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "daemon", number=15, proto_type="bool", default=False, cli_flag="--daemon", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "max_cpus", number=16, proto_type="uint32", default=0, cli_flag="--max_cpus", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "nice_level", number=17, proto_type="int32", default=19, cli_flag="--nice_level", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "keep_env", number=18, proto_type="bool", default=False, cli_flag="--keep_env", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "envar", number=19, proto_type="string", default=[], cli_flag="--env", cli_supported=True, is_repeated=True, is_message=False)
_r("NsJailConfig", "silent", number=20, proto_type="bool", default=False, cli_flag="--silent", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "skip_setsid", number=21, proto_type="bool", default=False, cli_flag="--skip_setsid", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "stderr_to_null", number=22, proto_type="bool", default=False, cli_flag="--stderr_to_null", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "pass_fd", number=23, proto_type="int32", default=[], cli_flag="--pass_fd", cli_supported=True, is_repeated=True, is_message=False)
_r("NsJailConfig", "disable_no_new_privs", number=24, proto_type="bool", default=False, cli_flag="--disable_no_new_privs", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "forward_signals", number=25, proto_type="bool", default=False, cli_flag="--forward_signals", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "disable_tsc", number=26, proto_type="bool", default=False, cli_flag="--disable_tsc", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "oom_score_adj", number=27, proto_type="int32", default=None, cli_flag="--oom_score_adj", cli_supported=True, is_repeated=False, is_message=False)
# Logging
_r("NsJailConfig", "log_fd", number=30, proto_type="int32", default=None, cli_flag="--log_fd", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "log_file", number=31, proto_type="string", default=None, cli_flag="--log", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "log_level", number=32, proto_type="enum", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
# Capabilities
_r("NsJailConfig", "keep_caps", number=33, proto_type="bool", default=False, cli_flag="--keep_caps", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cap", number=34, proto_type="string", default=[], cli_flag="--cap", cli_supported=True, is_repeated=True, is_message=False)
# Rlimits
_r("NsJailConfig", "rlimit_as", number=35, proto_type="uint64", default=4096, cli_flag="--rlimit_as", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_as_type", number=36, proto_type="enum", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_core", number=37, proto_type="uint64", default=0, cli_flag="--rlimit_core", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_core_type", number=38, proto_type="enum", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_cpu", number=39, proto_type="uint64", default=600, cli_flag="--rlimit_cpu", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_cpu_type", number=40, proto_type="enum", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_fsize", number=41, proto_type="uint64", default=1, cli_flag="--rlimit_fsize", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_fsize_type", number=42, proto_type="enum", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_nofile", number=43, proto_type="uint64", default=32, cli_flag="--rlimit_nofile", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_nofile_type", number=44, proto_type="enum", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_nproc", number=45, proto_type="uint64", default=1024, cli_flag="--rlimit_nproc", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_nproc_type", number=46, proto_type="enum", default=1, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_stack", number=47, proto_type="uint64", default=8, cli_flag="--rlimit_stack", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_stack_type", number=48, proto_type="enum", default=1, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_memlock", number=49, proto_type="uint64", default=64, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_memlock_type", number=50, proto_type="enum", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_rtprio", number=100, proto_type="uint64", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_rtprio_type", number=101, proto_type="enum", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_msgqueue", number=102, proto_type="uint64", default=1024, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_msgqueue_type", number=103, proto_type="enum", default=0, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "disable_rl", number=104, proto_type="bool", default=False, cli_flag="--disable_rl", cli_supported=True, is_repeated=False, is_message=False)
# Personality
_r("NsJailConfig", "persona_addr_compat_layout", number=51, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "persona_mmap_page_zero", number=52, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "persona_read_implies_exec", number=53, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "persona_addr_limit_3gb", number=54, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "persona_addr_no_randomize", number=55, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
# Namespaces
_r("NsJailConfig", "clone_newnet", number=60, proto_type="bool", default=True, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newuser", number=61, proto_type="bool", default=True, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newns", number=62, proto_type="bool", default=True, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newpid", number=63, proto_type="bool", default=True, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newipc", number=64, proto_type="bool", default=True, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newuts", number=65, proto_type="bool", default=True, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newcgroup", number=66, proto_type="bool", default=True, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newtime", number=67, proto_type="bool", default=False, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
# UID/GID mapping
_r("NsJailConfig", "uidmap", number=68, proto_type="message", default=[], cli_flag="--uid_mapping", cli_supported=True, is_repeated=True, is_message=True)
_r("NsJailConfig", "gidmap", number=69, proto_type="message", default=[], cli_flag="--gid_mapping", cli_supported=True, is_repeated=True, is_message=True)
# Mounts
_r("NsJailConfig", "mount_proc", number=73, proto_type="bool", default=False, cli_flag="--mount_proc", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "mount", number=74, proto_type="message", default=[], cli_flag=None, cli_supported=False, is_repeated=True, is_message=True)
_r("NsJailConfig", "no_pivotroot", number=75, proto_type="bool", default=False, cli_flag="--no_pivotroot", cli_supported=True, is_repeated=False, is_message=False)
# Seccomp
_r("NsJailConfig", "seccomp_policy_file", number=76, proto_type="string", default=None, cli_flag="--seccomp_policy", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "seccomp_string", number=77, proto_type="string", default=[], cli_flag="--seccomp_string", cli_supported=True, is_repeated=True, is_message=False)
_r("NsJailConfig", "seccomp_log", number=78, proto_type="bool", default=False, cli_flag="--seccomp_log", cli_supported=True, is_repeated=False, is_message=False)
# Cgroup v1 memory
_r("NsJailConfig", "cgroup_mem_max", number=80, proto_type="uint64", default=0, cli_flag="--cgroup_mem_max", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_mem_memsw_max", number=81, proto_type="uint64", default=0, cli_flag="--cgroup_mem_memsw_max", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_mem_swap_max", number=82, proto_type="int64", default=-1, cli_flag="--cgroup_mem_swap_max", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_mem_mount", number=83, proto_type="string", default="/sys/fs/cgroup/memory", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_mem_parent", number=84, proto_type="string", default="NSJAIL", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
# Cgroup v1 pids
_r("NsJailConfig", "cgroup_pids_max", number=85, proto_type="uint64", default=0, cli_flag="--cgroup_pids_max", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_pids_mount", number=86, proto_type="string", default="/sys/fs/cgroup/pids", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_pids_parent", number=87, proto_type="string", default="NSJAIL", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
# Cgroup v1 net_cls
_r("NsJailConfig", "cgroup_net_cls_classid", number=88, proto_type="uint32", default=0, cli_flag="--cgroup_net_cls_classid", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_net_cls_mount", number=89, proto_type="string", default="/sys/fs/cgroup/net_cls", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_net_cls_parent", number=90, proto_type="string", default="NSJAIL", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
# Cgroup v1 cpu
_r("NsJailConfig", "cgroup_cpu_ms_per_sec", number=91, proto_type="uint32", default=0, cli_flag="--cgroup_cpu_ms_per_sec", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_cpu_mount", number=92, proto_type="string", default="/sys/fs/cgroup/cpu", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_cpu_parent", number=93, proto_type="string", default="NSJAIL", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
# Cgroup v2
_r("NsJailConfig", "cgroupv2_mount", number=94, proto_type="string", default="/sys/fs/cgroup", cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "use_cgroupv2", number=105, proto_type="bool", default=False, cli_flag="--use_cgroupv2", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "detect_cgroupv2", number=106, proto_type="bool", default=False, cli_flag="--detect_cgroupv2", cli_supported=True, is_repeated=False, is_message=False)
# Networking
_r("NsJailConfig", "iface_no_lo", number=95, proto_type="bool", default=False, cli_flag="--iface_no_lo", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "iface_own", number=96, proto_type="string", default=[], cli_flag="--iface_own", cli_supported=True, is_repeated=True, is_message=False)
_r("NsJailConfig", "macvlan_iface", number=97, proto_type="string", default=None, cli_flag="--macvlan_iface", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_ip", number=98, proto_type="string", default="192.168.0.2", cli_flag="--macvlan_vs_ip", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_nm", number=99, proto_type="string", default="255.255.255.0", cli_flag="--macvlan_vs_nm", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_gw", number=100, proto_type="string", default="192.168.0.1", cli_flag="--macvlan_vs_gw", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_ma", number=107, proto_type="string", default="", cli_flag="--macvlan_vs_ma", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_mo", number=108, proto_type="string", default="private", cli_flag="--macvlan_vs_mo", cli_supported=True, is_repeated=False, is_message=False)
# Traffic rules
_r("NsJailConfig", "traffic_rule", number=109, proto_type="message", default=[], cli_flag=None, cli_supported=False, is_repeated=True, is_message=True)
# User-mode networking
_r("NsJailConfig", "user_net", number=110, proto_type="message", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=True)
# Execution
_r("NsJailConfig", "exec_bin", number=111, proto_type="message", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=True)

del _r
```

Note: Proto field numbers are approximate — will be corrected when the code generator is built. The CLI flag names are based on nsjail's README. The important thing is coverage and structure.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_field_meta.py -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/_field_meta.py tests/test_field_meta.py
git commit -m "feat: add field metadata registry for serializer dispatch"
```

---

### Task 6: Text-Proto Serializer

**Files:**
- Create: `src/nsjail/serializers/textproto.py`
- Modify: `src/nsjail/serializers/__init__.py`
- Create: `tests/test_serializers.py`

- [ ] **Step 1: Write tests for text-proto serializer**

Create `tests/test_serializers.py`:
```python
from nsjail.config import NsJailConfig, MountPt, IdMap, Exe
from nsjail.enums import Mode
from nsjail.serializers import to_textproto


class TestTextProtoScalars:
    def test_empty_config_emits_nothing(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert text.strip() == ""

    def test_changed_scalar_string(self):
        cfg = NsJailConfig(hostname="sandbox")
        text = to_textproto(cfg)
        assert 'hostname: "sandbox"' in text

    def test_unchanged_scalar_not_emitted(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert "hostname" not in text  # default "NSJAIL" is not emitted

    def test_changed_scalar_int(self):
        cfg = NsJailConfig(time_limit=30)
        text = to_textproto(cfg)
        assert "time_limit: 30" in text

    def test_changed_bool_false_to_true(self):
        cfg = NsJailConfig(clone_newtime=True)
        text = to_textproto(cfg)
        assert "clone_newtime: true" in text

    def test_changed_bool_true_to_false(self):
        cfg = NsJailConfig(clone_newnet=False)
        text = to_textproto(cfg)
        assert "clone_newnet: false" in text

    def test_none_field_not_emitted(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert "log_file" not in text

    def test_none_field_set_to_value(self):
        cfg = NsJailConfig(log_file="/var/log/nsjail.log")
        text = to_textproto(cfg)
        assert 'log_file: "/var/log/nsjail.log"' in text

    def test_enum_field(self):
        cfg = NsJailConfig(mode=Mode.LISTEN)
        text = to_textproto(cfg)
        assert "mode: LISTEN" in text


class TestTextProtoRepeated:
    def test_repeated_string(self):
        cfg = NsJailConfig(envar=["HOME=/home/user", "PATH=/usr/bin"])
        text = to_textproto(cfg)
        assert 'envar: "HOME=/home/user"' in text
        assert 'envar: "PATH=/usr/bin"' in text

    def test_empty_repeated_not_emitted(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert "envar" not in text


class TestTextProtoMessage:
    def test_mount_message(self):
        cfg = NsJailConfig(mount=[
            MountPt(src="/", dst="/", is_bind=True, rw=False),
        ])
        text = to_textproto(cfg)
        assert "mount {" in text
        assert 'src: "/"' in text
        assert 'dst: "/"' in text
        assert "is_bind: true" in text
        assert "rw" not in text.split("mount {")[1].split("}")[0] or "rw: false" not in text  # rw=False is default, not emitted

    def test_exec_bin_message(self):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo hi"]),
        )
        text = to_textproto(cfg)
        assert "exec_bin {" in text
        assert 'path: "/bin/sh"' in text
        assert 'arg: "-c"' in text
        assert 'arg: "echo hi"' in text

    def test_nested_message_none_not_emitted(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert "exec_bin" not in text


class TestTextProtoRoundTrip:
    def test_complex_config(self):
        cfg = NsJailConfig(
            hostname="mybox",
            time_limit=60,
            clone_newnet=True,
            clone_newtime=True,
            mount=[
                MountPt(src="/", dst="/", is_bind=True),
                MountPt(dst="/tmp", fstype="tmpfs", rw=True, options="size=64M"),
            ],
            uidmap=[IdMap(inside_id="0", outside_id="1000")],
            envar=["HOME=/home/user"],
            exec_bin=Exe(path="/usr/bin/python3", arg=["script.py"]),
        )
        text = to_textproto(cfg)
        # Verify structure is parseable (basic checks)
        assert text.count("mount {") == 2
        assert text.count("uidmap {") == 1
        assert text.count("exec_bin {") == 1
        # Verify braces are balanced
        assert text.count("{") == text.count("}")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_serializers.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement textproto serializer**

Create `src/nsjail/serializers/textproto.py`:
```python
"""Pure Python serializer for protobuf text format.

Walks dataclass fields using _field_meta to emit only fields that differ
from their proto-defined defaults.
"""

from __future__ import annotations

from dataclasses import fields as dc_fields
from enum import IntEnum
from typing import Any

from nsjail._field_meta import FIELD_REGISTRY, FieldMeta


def to_textproto(obj: Any, indent: int = 0) -> str:
    """Serialize a config dataclass to protobuf text format.

    Only emits fields whose values differ from the proto-defined default.
    """
    lines: list[str] = []
    prefix = "  " * indent
    cls_name = type(obj).__name__

    for f in dc_fields(obj):
        key = (cls_name, f.name)
        meta = FIELD_REGISTRY.get(key)
        if meta is None:
            continue

        value = getattr(obj, f.name)

        if meta.is_repeated:
            if not value:
                continue
            if meta.is_message:
                for item in value:
                    lines.append(f"{prefix}{f.name} {{")
                    inner = to_textproto(item, indent + 1)
                    if inner.strip():
                        lines.append(inner)
                    lines.append(f"{prefix}}}")
            else:
                for item in value:
                    lines.append(f"{prefix}{f.name}: {_format_scalar(item, meta)}")
        elif meta.is_message:
            if value is None:
                continue
            lines.append(f"{prefix}{f.name} {{")
            inner = to_textproto(value, indent + 1)
            if inner.strip():
                lines.append(inner)
            lines.append(f"{prefix}}}")
        else:
            if _is_default(value, meta):
                continue
            lines.append(f"{prefix}{f.name}: {_format_scalar(value, meta)}")

    return "\n".join(lines)


def _is_default(value: Any, meta: FieldMeta) -> bool:
    """Check if a value matches the proto-defined default."""
    if value is None and meta.default is None:
        return True
    if value is None:
        return False
    if meta.default is None:
        return False
    if isinstance(value, IntEnum):
        return int(value) == meta.default
    return value == meta.default


def _format_scalar(value: Any, meta: FieldMeta) -> str:
    """Format a scalar value for text-proto output."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, IntEnum):
        return value.name
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return f'"{_escape_string(value)}"'
    if isinstance(value, bytes):
        return f'"{_escape_bytes(value)}"'
    return str(value)


def _escape_string(s: str) -> str:
    """Escape a string for protobuf text format."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _escape_bytes(b: bytes) -> str:
    """Escape bytes for protobuf text format."""
    parts: list[str] = []
    for byte in b:
        if 32 <= byte < 127 and byte != ord("\\") and byte != ord('"'):
            parts.append(chr(byte))
        else:
            parts.append(f"\\x{byte:02x}")
    return "".join(parts)
```

- [ ] **Step 4: Update serializers __init__.py**

Update `src/nsjail/serializers/__init__.py`:
```python
"""Serializers for NsJailConfig: textproto, CLI args, protobuf."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nsjail.serializers.textproto import to_textproto


def to_file(cfg: Any, path: str | Path, *, validate: bool = False) -> None:
    """Write a config to a .cfg file in protobuf text format.

    Args:
        cfg: A NsJailConfig dataclass instance.
        path: File path to write to.
        validate: If True, validate against compiled proto schema first.
            Requires the [proto] extra.
    """
    if validate:
        try:
            from nsjail.serializers.protobuf import to_protobuf
        except ImportError:
            raise ImportError(
                "Validation requires the protobuf extra: pip install nsjail-python[proto]"
            ) from None
        to_protobuf(cfg)  # Validates by converting; raises on invalid

    text = to_textproto(cfg)
    Path(path).write_text(text + "\n")


__all__ = ["to_textproto", "to_file"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_serializers.py -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/nsjail/serializers/ tests/test_serializers.py
git commit -m "feat: add text-proto serializer (pure Python)"
```

---

### Task 7: CLI Argument Serializer

**Files:**
- Create: `src/nsjail/serializers/cli.py`
- Modify: `src/nsjail/serializers/__init__.py`
- Create: `tests/test_cli_serializer.py`

- [ ] **Step 1: Write tests for CLI serializer**

Create `tests/test_cli_serializer.py`:
```python
import pytest

from nsjail.config import NsJailConfig, MountPt, IdMap, Exe
from nsjail.enums import Mode
from nsjail.exceptions import UnsupportedCLIField
from nsjail.serializers import to_cli_args


class TestCliScalars:
    def test_empty_config_returns_empty(self):
        cfg = NsJailConfig()
        args = to_cli_args(cfg, on_unsupported="skip")
        assert args == []

    def test_changed_string_field(self):
        cfg = NsJailConfig(hostname="sandbox")
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--hostname" in args
        idx = args.index("--hostname")
        assert args[idx + 1] == "sandbox"

    def test_changed_int_field(self):
        cfg = NsJailConfig(time_limit=30)
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--time_limit" in args
        idx = args.index("--time_limit")
        assert args[idx + 1] == "30"

    def test_bool_flag_true(self):
        cfg = NsJailConfig(keep_env=True)
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--keep_env" in args

    def test_default_values_not_emitted(self):
        cfg = NsJailConfig()
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--hostname" not in args
        assert "--time_limit" not in args

    def test_repeated_string_field(self):
        cfg = NsJailConfig(envar=["A=1", "B=2"])
        args = to_cli_args(cfg, on_unsupported="skip")
        assert args.count("--env") == 2


class TestCliUnsupported:
    def test_unsupported_field_raises_by_default(self):
        cfg = NsJailConfig(mount=[MountPt(src="/", dst="/", is_bind=True)])
        with pytest.raises(UnsupportedCLIField):
            to_cli_args(cfg, on_unsupported="raise")

    def test_unsupported_field_skip(self):
        cfg = NsJailConfig(mount=[MountPt(src="/", dst="/", is_bind=True)])
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--mount" not in args  # mount has no direct CLI flag

    def test_unsupported_field_warn(self, caplog):
        import logging
        cfg = NsJailConfig(mount=[MountPt(src="/", dst="/", is_bind=True)])
        with caplog.at_level(logging.WARNING):
            args = to_cli_args(cfg, on_unsupported="warn")
        assert "mount" in caplog.text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_serializer.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement CLI serializer**

Create `src/nsjail/serializers/cli.py`:
```python
"""Serialize NsJailConfig to nsjail CLI arguments."""

from __future__ import annotations

import logging
from dataclasses import fields as dc_fields
from enum import IntEnum
from typing import Any, Literal

from nsjail._field_meta import FIELD_REGISTRY
from nsjail.exceptions import UnsupportedCLIField

logger = logging.getLogger(__name__)


def to_cli_args(
    cfg: Any,
    *,
    on_unsupported: Literal["raise", "warn", "skip"] = "raise",
) -> list[str]:
    """Serialize a NsJailConfig to a list of CLI arguments.

    Args:
        cfg: A NsJailConfig dataclass instance.
        on_unsupported: How to handle fields without CLI equivalents.

    Returns:
        A list of strings suitable for subprocess: ["--flag", "value", ...]
    """
    args: list[str] = []
    cls_name = type(cfg).__name__

    for f in dc_fields(cfg):
        key = (cls_name, f.name)
        meta = FIELD_REGISTRY.get(key)
        if meta is None:
            continue

        value = getattr(cfg, f.name)

        # Skip defaults and None
        if meta.is_repeated:
            if not value:
                continue
        elif meta.is_message:
            if value is None:
                continue
        else:
            from nsjail.serializers.textproto import _is_default
            if _is_default(value, meta):
                continue

        # Check CLI support
        if not meta.cli_supported or meta.cli_flag is None:
            if on_unsupported == "raise":
                raise UnsupportedCLIField(f.name)
            elif on_unsupported == "warn":
                logger.warning(
                    "Config field %r has no CLI equivalent, skipping", f.name
                )
            continue

        # Render the field
        if meta.is_repeated:
            for item in value:
                args.append(meta.cli_flag)
                args.append(str(item))
        elif isinstance(value, bool):
            if value:
                args.append(meta.cli_flag)
        elif isinstance(value, IntEnum):
            args.append(meta.cli_flag)
            args.append(str(int(value)))
        else:
            args.append(meta.cli_flag)
            args.append(str(value))

    return args
```

- [ ] **Step 4: Update serializers __init__.py**

Add to `src/nsjail/serializers/__init__.py`:
```python
from nsjail.serializers.cli import to_cli_args

__all__ = ["to_textproto", "to_cli_args", "to_file"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_cli_serializer.py -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/nsjail/serializers/ tests/test_cli_serializer.py
git commit -m "feat: add CLI argument serializer"
```

---

### Task 8: Presets (apply functions + sandbox factory)

**Files:**
- Create: `src/nsjail/presets.py`
- Create: `tests/test_presets.py`

- [ ] **Step 1: Write tests for presets**

Create `tests/test_presets.py`:
```python
from nsjail.config import NsJailConfig, MountPt, Exe
from nsjail.enums import Mode
from nsjail.presets import (
    apply_readonly_root,
    apply_cgroup_limits,
    apply_seccomp_log,
    sandbox,
)


class TestApplyReadonlyRoot:
    def test_adds_root_bind_mount(self):
        cfg = NsJailConfig()
        apply_readonly_root(cfg)
        root_mounts = [m for m in cfg.mount if m.dst == "/"]
        assert len(root_mounts) == 1
        assert root_mounts[0].is_bind is True
        assert root_mounts[0].rw is False

    def test_adds_writable_dirs(self):
        cfg = NsJailConfig()
        apply_readonly_root(cfg, writable=["/workspace", "/home"])
        writable = [m for m in cfg.mount if m.rw is True]
        dsts = {m.dst for m in writable}
        assert "/workspace" in dsts
        assert "/home" in dsts

    def test_writable_as_tmpfs(self):
        cfg = NsJailConfig()
        apply_readonly_root(cfg, writable=["/tmp"])
        tmp_mounts = [m for m in cfg.mount if m.dst == "/tmp"]
        assert len(tmp_mounts) == 1
        assert tmp_mounts[0].fstype == "tmpfs"
        assert tmp_mounts[0].rw is True


class TestApplyCgroupLimits:
    def test_memory_limit(self):
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg, memory_mb=512)
        assert cfg.cgroup_mem_max == 512 * 1024 * 1024

    def test_cpu_limit(self):
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg, cpu_ms_per_sec=500)
        assert cfg.cgroup_cpu_ms_per_sec == 500

    def test_pids_limit(self):
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg, pids_max=64)
        assert cfg.cgroup_pids_max == 64

    def test_no_args_does_nothing(self):
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg)
        assert cfg.cgroup_mem_max == 0
        assert cfg.cgroup_cpu_ms_per_sec == 0
        assert cfg.cgroup_pids_max == 0


class TestApplySeccompLog:
    def test_enables_seccomp_log(self):
        cfg = NsJailConfig()
        apply_seccomp_log(cfg)
        assert cfg.seccomp_log is True


class TestSandbox:
    def test_basic_sandbox(self):
        cfg = sandbox(
            command=["python", "script.py"],
            timeout_sec=60,
        )
        assert cfg.mode == Mode.ONCE
        assert cfg.time_limit == 60
        assert cfg.exec_bin is not None
        assert cfg.exec_bin.path == "python"
        assert cfg.exec_bin.arg == ["script.py"]

    def test_sandbox_with_memory(self):
        cfg = sandbox(command=["echo", "hi"], memory_mb=256)
        assert cfg.cgroup_mem_max == 256 * 1024 * 1024

    def test_sandbox_no_network(self):
        cfg = sandbox(command=["echo"], network=False)
        assert cfg.clone_newnet is True  # Default is already True

    def test_sandbox_with_network(self):
        cfg = sandbox(command=["echo"], network=True)
        assert cfg.clone_newnet is False

    def test_sandbox_with_writable_dirs(self):
        cfg = sandbox(
            command=["echo"],
            writable_dirs=["/workspace"],
        )
        writable = [m for m in cfg.mount if m.rw is True and m.dst == "/workspace"]
        assert len(writable) == 1

    def test_sandbox_sets_cwd(self):
        cfg = sandbox(command=["echo"], cwd="/workspace")
        assert cfg.cwd == "/workspace"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_presets.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement presets**

Create `src/nsjail/presets.py`:
```python
"""Opinionated preset configurations and composable modifiers."""

from __future__ import annotations

from nsjail.config import Exe, MountPt, NsJailConfig
from nsjail.enums import Mode


def apply_readonly_root(
    cfg: NsJailConfig,
    *,
    writable: list[str] | None = None,
) -> None:
    """Add a read-only root bind mount with optional writable directories.

    /tmp is automatically mounted as tmpfs when included in writable.
    Other writable paths are bind-mounted read-write from the host.
    """
    cfg.mount.append(MountPt(src="/", dst="/", is_bind=True, rw=False))

    for path in writable or []:
        if path == "/tmp":
            cfg.mount.append(
                MountPt(dst="/tmp", fstype="tmpfs", rw=True, is_dir=True)
            )
        else:
            cfg.mount.append(
                MountPt(src=path, dst=path, is_bind=True, rw=True)
            )


def apply_cgroup_limits(
    cfg: NsJailConfig,
    *,
    memory_mb: int | None = None,
    cpu_ms_per_sec: int | None = None,
    pids_max: int | None = None,
) -> None:
    """Set cgroup resource limits."""
    if memory_mb is not None:
        cfg.cgroup_mem_max = memory_mb * 1024 * 1024
    if cpu_ms_per_sec is not None:
        cfg.cgroup_cpu_ms_per_sec = cpu_ms_per_sec
    if pids_max is not None:
        cfg.cgroup_pids_max = pids_max


def apply_seccomp_log(cfg: NsJailConfig) -> None:
    """Enable seccomp logging (violations logged to dmesg)."""
    cfg.seccomp_log = True


def sandbox(
    *,
    command: list[str],
    cwd: str = "/",
    timeout_sec: int = 600,
    memory_mb: int | None = None,
    cpu_ms_per_sec: int | None = None,
    pids_max: int | None = None,
    network: bool = False,
    writable_dirs: list[str] | None = None,
) -> NsJailConfig:
    """Create a general-purpose sandbox configuration.

    Args:
        command: Command to run inside the sandbox (first element is the binary).
        cwd: Working directory inside the sandbox.
        timeout_sec: Wall-clock time limit in seconds.
        memory_mb: Memory limit in megabytes.
        cpu_ms_per_sec: CPU throttle (milliseconds of CPU per second).
        pids_max: Maximum number of processes/threads.
        network: If True, disable network namespace (allow network access).
        writable_dirs: Directories to mount read-write. /tmp is auto-tmpfs.
    """
    cfg = NsJailConfig(
        mode=Mode.ONCE,
        cwd=cwd,
        time_limit=timeout_sec,
        clone_newnet=not network,
    )

    cfg.exec_bin = Exe(path=command[0], arg=command[1:])

    apply_readonly_root(cfg, writable=writable_dirs)
    apply_cgroup_limits(
        cfg,
        memory_mb=memory_mb,
        cpu_ms_per_sec=cpu_ms_per_sec,
        pids_max=pids_max,
    )

    return cfg
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_presets.py -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/presets.py tests/test_presets.py
git commit -m "feat: add presets (apply_* modifiers + sandbox factory)"
```

---

### Task 9: Fluent Builder

**Files:**
- Create: `src/nsjail/builder.py`
- Create: `tests/test_builder.py`

- [ ] **Step 1: Write tests for builder**

Create `tests/test_builder.py`:
```python
from nsjail.builder import Jail
from nsjail.config import NsJailConfig
from nsjail.enums import Mode


class TestBuilderCommand:
    def test_command(self):
        cfg = Jail().command("python", "script.py").build()
        assert cfg.exec_bin.path == "python"
        assert cfg.exec_bin.arg == ["script.py"]

    def test_sh(self):
        cfg = Jail().sh("echo hello && ls").build()
        assert cfg.exec_bin.path == "/bin/sh"
        assert cfg.exec_bin.arg == ["-c", "echo hello && ls"]

    def test_python(self):
        cfg = Jail().python("script.py").build()
        assert cfg.exec_bin.path == "/usr/bin/python3"
        assert cfg.exec_bin.arg == ["script.py"]

    def test_bash(self):
        cfg = Jail().bash("-c", "echo hi").build()
        assert cfg.exec_bin.path == "/bin/bash"
        assert cfg.exec_bin.arg == ["-c", "echo hi"]


class TestBuilderResources:
    def test_timeout(self):
        cfg = Jail().sh("true").timeout(30).build()
        assert cfg.time_limit == 30

    def test_memory_mb(self):
        cfg = Jail().sh("true").memory(512, "MB").build()
        assert cfg.cgroup_mem_max == 512 * 1024 * 1024

    def test_memory_gb(self):
        cfg = Jail().sh("true").memory(2, "GB").build()
        assert cfg.cgroup_mem_max == 2 * 1024 * 1024 * 1024

    def test_cpu(self):
        cfg = Jail().sh("true").cpu(500).build()
        assert cfg.cgroup_cpu_ms_per_sec == 500

    def test_pids(self):
        cfg = Jail().sh("true").pids(64).build()
        assert cfg.cgroup_pids_max == 64


class TestBuilderNamespace:
    def test_no_network(self):
        cfg = Jail().sh("true").no_network().build()
        assert cfg.clone_newnet is True  # newnet=True means isolated

    def test_network(self):
        cfg = Jail().sh("true").network().build()
        assert cfg.clone_newnet is False


class TestBuilderFilesystem:
    def test_readonly_root(self):
        cfg = Jail().sh("true").readonly_root().build()
        root = [m for m in cfg.mount if m.dst == "/"]
        assert len(root) == 1
        assert root[0].rw is False

    def test_writable(self):
        cfg = Jail().sh("true").readonly_root().writable("/workspace").build()
        ws = [m for m in cfg.mount if m.dst == "/workspace"]
        assert len(ws) == 1
        assert ws[0].rw is True

    def test_writable_tmpfs(self):
        cfg = Jail().sh("true").writable("/tmp", tmpfs=True, size="64M").build()
        tmp = [m for m in cfg.mount if m.dst == "/tmp"]
        assert len(tmp) == 1
        assert tmp[0].fstype == "tmpfs"
        assert "64M" in (tmp[0].options or "")

    def test_mount(self):
        cfg = Jail().sh("true").mount("/data", "/data", readonly=True).build()
        data = [m for m in cfg.mount if m.dst == "/data"]
        assert len(data) == 1
        assert data[0].rw is False


class TestBuilderEnvironment:
    def test_env(self):
        cfg = Jail().sh("true").env("HOME=/home/user").env("CI=1").build()
        assert "HOME=/home/user" in cfg.envar
        assert "CI=1" in cfg.envar

    def test_cwd(self):
        cfg = Jail().sh("true").cwd("/workspace").build()
        assert cfg.cwd == "/workspace"


class TestBuilderSecurity:
    def test_seccomp_log(self):
        cfg = Jail().sh("true").seccomp_log().build()
        assert cfg.seccomp_log is True

    def test_uid_map(self):
        cfg = Jail().sh("true").uid_map(inside=0, outside=1000).build()
        assert len(cfg.uidmap) == 1
        assert cfg.uidmap[0].inside_id == "0"
        assert cfg.uidmap[0].outside_id == "1000"


class TestBuilderChaining:
    def test_full_chain(self):
        cfg = (
            Jail()
            .sh("pytest tests/ -v")
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
            .uid_map(inside=0, outside=1000)
            .build()
        )
        assert isinstance(cfg, NsJailConfig)
        assert cfg.exec_bin.path == "/bin/sh"
        assert cfg.time_limit == 60
        assert cfg.cgroup_mem_max == 512 * 1024 * 1024
        assert cfg.seccomp_log is True
        assert len(cfg.envar) == 2

    def test_build_returns_nsjailconfig(self):
        cfg = Jail().sh("true").build()
        assert isinstance(cfg, NsJailConfig)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_builder.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement builder**

Create `src/nsjail/builder.py`:
```python
"""Fluent builder for NsJailConfig."""

from __future__ import annotations

from typing import Literal

from nsjail.config import Exe, IdMap, MountPt, NsJailConfig
from nsjail.presets import (
    apply_cgroup_limits,
    apply_readonly_root,
    apply_seccomp_log,
)


class Jail:
    """Fluent builder for NsJailConfig.

    Each method mutates internal state and returns self for chaining.
    Call .build() to produce the final NsJailConfig.
    """

    def __init__(self) -> None:
        self._cfg = NsJailConfig()

    def build(self) -> NsJailConfig:
        """Return the built NsJailConfig."""
        return self._cfg

    # --- Command builders ---

    def command(self, *args: str) -> Jail:
        """Set the command to execute. First arg is the binary path."""
        self._cfg.exec_bin = Exe(path=args[0], arg=list(args[1:]))
        return self

    def sh(self, script: str) -> Jail:
        """Run a shell script via /bin/sh -c."""
        self._cfg.exec_bin = Exe(path="/bin/sh", arg=["-c", script])
        return self

    def python(self, *args: str) -> Jail:
        """Run via /usr/bin/python3."""
        self._cfg.exec_bin = Exe(path="/usr/bin/python3", arg=list(args))
        return self

    def bash(self, *args: str) -> Jail:
        """Run via /bin/bash."""
        self._cfg.exec_bin = Exe(path="/bin/bash", arg=list(args))
        return self

    # --- Resource limits ---

    def timeout(self, seconds: int) -> Jail:
        """Set wall-clock time limit."""
        self._cfg.time_limit = seconds
        return self

    def memory(self, amount: int, unit: Literal["MB", "GB"] = "MB") -> Jail:
        """Set memory limit."""
        multiplier = 1024 * 1024 if unit == "MB" else 1024 * 1024 * 1024
        apply_cgroup_limits(self._cfg, memory_mb=amount * multiplier // (1024 * 1024))
        return self

    def cpu(self, ms_per_sec: int) -> Jail:
        """Set CPU throttle (milliseconds of CPU per second)."""
        apply_cgroup_limits(self._cfg, cpu_ms_per_sec=ms_per_sec)
        return self

    def pids(self, max_pids: int) -> Jail:
        """Set maximum number of processes/threads."""
        apply_cgroup_limits(self._cfg, pids_max=max_pids)
        return self

    # --- Namespace control ---

    def no_network(self) -> Jail:
        """Isolate network (create new network namespace)."""
        self._cfg.clone_newnet = True
        return self

    def network(self) -> Jail:
        """Allow network access (disable network namespace)."""
        self._cfg.clone_newnet = False
        return self

    # --- Filesystem ---

    def readonly_root(self) -> Jail:
        """Mount root filesystem read-only."""
        apply_readonly_root(self._cfg)
        return self

    def writable(
        self,
        path: str,
        *,
        tmpfs: bool = False,
        size: str | None = None,
    ) -> Jail:
        """Add a writable directory."""
        if tmpfs:
            options = f"size={size}" if size else None
            self._cfg.mount.append(
                MountPt(dst=path, fstype="tmpfs", rw=True, is_dir=True, options=options)
            )
        else:
            self._cfg.mount.append(
                MountPt(src=path, dst=path, is_bind=True, rw=True)
            )
        return self

    def mount(
        self,
        src: str,
        dst: str,
        *,
        readonly: bool = False,
    ) -> Jail:
        """Add a bind mount."""
        self._cfg.mount.append(
            MountPt(src=src, dst=dst, is_bind=True, rw=not readonly)
        )
        return self

    # --- Environment ---

    def env(self, var: str) -> Jail:
        """Add an environment variable (KEY=VALUE format)."""
        self._cfg.envar.append(var)
        return self

    def cwd(self, path: str) -> Jail:
        """Set working directory inside the sandbox."""
        self._cfg.cwd = path
        return self

    # --- Security ---

    def seccomp_log(self) -> Jail:
        """Enable seccomp violation logging."""
        apply_seccomp_log(self._cfg)
        return self

    def uid_map(
        self,
        *,
        inside: int = 0,
        outside: int = 1000,
        count: int = 1,
    ) -> Jail:
        """Add a UID mapping."""
        self._cfg.uidmap.append(
            IdMap(inside_id=str(inside), outside_id=str(outside), count=count)
        )
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_builder.py -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/builder.py tests/test_builder.py
git commit -m "feat: add fluent Jail builder"
```

---

### Task 10: Runner

**Files:**
- Create: `src/nsjail/runner.py`
- Create: `tests/test_runner.py`

- [ ] **Step 1: Write tests for Runner**

Create `tests/test_runner.py`:
```python
import subprocess
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nsjail.config import Exe, MountPt, NsJailConfig
from nsjail.exceptions import NsjailNotFound
from nsjail.runner import NsJailResult, Runner, merge_configs, resolve_nsjail_path


class TestResolveNsjailPath:
    def test_explicit_path(self):
        assert resolve_nsjail_path("/custom/nsjail") == Path("/custom/nsjail")

    def test_system_nsjail(self):
        with patch("shutil.which", return_value="/usr/bin/nsjail"):
            assert resolve_nsjail_path(None) == Path("/usr/bin/nsjail")

    def test_bundled_binary(self):
        mock_module = MagicMock()
        mock_module.binary_path.return_value = Path("/site-packages/nsjail_bin/_bin/nsjail")
        with (
            patch("shutil.which", return_value=None),
            patch.dict("sys.modules", {"nsjail_bin": mock_module}),
        ):
            result = resolve_nsjail_path(None)
            assert result == Path("/site-packages/nsjail_bin/_bin/nsjail")

    def test_not_found_raises(self):
        with (
            patch("shutil.which", return_value=None),
            patch.dict("sys.modules", {}),
        ):
            # Also need to make import fail
            with patch("builtins.__import__", side_effect=ImportError):
                with pytest.raises(NsjailNotFound):
                    resolve_nsjail_path(None)


class TestMergeConfigs:
    def test_scalar_override(self):
        base = NsJailConfig(hostname="base", time_limit=60)
        override = NsJailConfig(time_limit=120)
        # Only time_limit was explicitly changed from default
        merged = merge_configs(base, override, override_fields={"time_limit"})
        assert merged.hostname == "base"
        assert merged.time_limit == 120

    def test_list_append(self):
        base = NsJailConfig(envar=["A=1"])
        override = NsJailConfig(envar=["B=2"])
        merged = merge_configs(base, override, override_fields={"envar"})
        assert merged.envar == ["A=1", "B=2"]

    def test_mount_append(self):
        base = NsJailConfig(mount=[MountPt(dst="/")])
        override = NsJailConfig(mount=[MountPt(dst="/tmp")])
        merged = merge_configs(base, override, override_fields={"mount"})
        assert len(merged.mount) == 2

    def test_extra_args_appended(self):
        base = NsJailConfig(exec_bin=Exe(path="python", arg=["main.py"]))
        merged = merge_configs(base, NsJailConfig(), override_fields=set(), extra_args=["--verbose"])
        assert merged.exec_bin.arg == ["main.py", "--verbose"]


class TestNsJailResult:
    def test_result_fields(self):
        result = NsJailResult(
            returncode=0,
            stdout=b"hello",
            stderr=b"",
            config_path=Path("/tmp/test.cfg"),
            nsjail_args=["nsjail", "--config", "/tmp/test.cfg"],
            timed_out=False,
            oom_killed=False,
            signaled=False,
            inner_returncode=0,
        )
        assert result.returncode == 0
        assert result.stdout == b"hello"


class TestRunner:
    def test_runner_creation(self):
        runner = Runner(nsjail_path="/usr/bin/nsjail")
        assert runner._nsjail_path == "/usr/bin/nsjail"

    def test_runner_with_base_config(self):
        base = NsJailConfig(hostname="test", time_limit=30)
        runner = Runner(base_config=base)
        assert runner._base_config.hostname == "test"

    def test_fork_creates_new_runner(self):
        base = NsJailConfig(hostname="base", time_limit=60)
        runner = Runner(base_config=base)
        forked = runner.fork(
            overrides=NsJailConfig(time_limit=120),
            override_fields={"time_limit"},
        )
        assert forked._base_config.time_limit == 120
        assert forked._base_config.hostname == "base"
        # Original unchanged
        assert runner._base_config.time_limit == 60
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_runner.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement runner**

Create `src/nsjail/runner.py`:
```python
"""Runner for executing nsjail sandboxes."""

from __future__ import annotations

import copy
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, fields as dc_fields
from pathlib import Path
from typing import Any

from nsjail.config import NsJailConfig
from nsjail.exceptions import NsjailNotFound
from nsjail.serializers import to_textproto, to_file


def resolve_nsjail_path(explicit_path: str | None) -> Path:
    """Resolve the nsjail binary path using the precedence order.

    1. Explicit path (always wins)
    2. System nsjail on PATH
    3. Bundled binary from companion package
    4. Raises NsjailNotFound
    """
    if explicit_path is not None:
        return Path(explicit_path)

    system = shutil.which("nsjail")
    if system is not None:
        return Path(system)

    # Try companion packages
    for module_name in ("nsjail_bin", "nsjail_bin_build"):
        try:
            mod = __import__(module_name)
            return mod.binary_path()
        except (ImportError, AttributeError):
            continue

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
        """Run nsjail with the baked config, optionally merged with overrides.

        Args:
            overrides: Config fields to override on the base config.
            override_fields: Set of field names that were explicitly set
                on the overrides object. Only these fields are applied.
            extra_args: Extra arguments appended to exec_bin.arg.
            timeout: subprocess timeout (separate from nsjail's time_limit).
        """
        nsjail_bin = resolve_nsjail_path(self._nsjail_path)

        if overrides is not None and override_fields:
            cfg = merge_configs(
                self._base_config,
                overrides,
                override_fields=override_fields,
                extra_args=extra_args,
            )
        elif extra_args:
            cfg = merge_configs(
                self._base_config,
                NsJailConfig(),
                override_fields=set(),
                extra_args=extra_args,
            )
        else:
            cfg = copy.deepcopy(self._base_config)

        # Render config
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

        # Add command separator and exec_bin args if using CLI mode
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

        # nsjail exit codes:
        # 0 = success
        # 1 = error
        # 109 = time limit exceeded
        # 100+ = signal number
        timed_out = result.returncode == 109
        signaled = result.returncode > 100 and not timed_out
        oom_killed = result.returncode == 137  # SIGKILL from OOM

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
        """Create a derived Runner with additional overrides baked in."""
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_runner.py -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/runner.py tests/test_runner.py
git commit -m "feat: add Runner with config merging and fork"
```

---

### Task 11: Public API (__init__.py)

**Files:**
- Modify: `src/nsjail/__init__.py`
- Create: `tests/test_public_api.py`

- [ ] **Step 1: Write tests for public API**

Create `tests/test_public_api.py`:
```python
def test_top_level_imports():
    from nsjail import (
        NsJailConfig,
        MountPt,
        IdMap,
        Exe,
        Mode,
        LogLevel,
        RLimitType,
        Jail,
        Runner,
        NsJailResult,
        sandbox,
    )
    # Verify they are the right types
    assert NsJailConfig is not None
    assert Jail is not None
    assert Runner is not None


def test_serializer_imports():
    from nsjail.serializers import to_textproto, to_cli_args, to_file
    assert callable(to_textproto)
    assert callable(to_cli_args)
    assert callable(to_file)


def test_exception_imports():
    from nsjail.exceptions import NsjailError, UnsupportedCLIField, NsjailNotFound
    assert issubclass(UnsupportedCLIField, NsjailError)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL with ImportError (Jail not in __init__.py yet).

- [ ] **Step 3: Update __init__.py**

Update `src/nsjail/__init__.py`:
```python
"""nsjail-python: Python wrapper for Google's nsjail sandboxing tool."""

from nsjail.config import Exe, IdMap, MountPt, NsJailConfig
from nsjail.enums import LogLevel, Mode, RLimitType
from nsjail.builder import Jail
from nsjail.presets import sandbox
from nsjail.runner import NsJailResult, Runner

__all__ = [
    "Exe",
    "IdMap",
    "Jail",
    "LogLevel",
    "Mode",
    "MountPt",
    "NsJailConfig",
    "NsJailResult",
    "RLimitType",
    "Runner",
    "sandbox",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_public_api.py -v`
Expected: All tests pass.

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/nsjail/__init__.py tests/test_public_api.py
git commit -m "feat: wire up public API exports"
```

---

### Task 12: Companion Package Scaffolding

**Files:**
- Create: `packages/nsjail-bin/pyproject.toml`
- Create: `packages/nsjail-bin/src/nsjail_bin/__init__.py`
- Create: `packages/nsjail-bin-build/pyproject.toml`
- Create: `packages/nsjail-bin-build/src/nsjail_bin_build/__init__.py`
- Create: `packages/nsjail-bin-none/pyproject.toml`
- Create: `packages/nsjail-bin-none/src/nsjail_bin_none/__init__.py`

- [ ] **Step 1: Create nsjail-bin package**

Create `packages/nsjail-bin/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nsjail-bin"
version = "0.1.0"
description = "Pre-built nsjail binary for nsjail-python"
requires-python = ">=3.12"
license = "MIT"

[tool.hatch.build.targets.wheel]
packages = ["src/nsjail_bin"]
```

Create `packages/nsjail-bin/src/nsjail_bin/__init__.py`:
```python
"""Pre-built nsjail binary distribution."""

from pathlib import Path


def binary_path() -> Path:
    """Return the path to the bundled nsjail binary."""
    bin_path = Path(__file__).parent / "_bin" / "nsjail"
    if not bin_path.exists():
        raise FileNotFoundError(
            f"Bundled nsjail binary not found at {bin_path}. "
            f"This platform may not have a pre-built binary. "
            f"Try: pip install nsjail-python[build]"
        )
    return bin_path
```

- [ ] **Step 2: Create nsjail-bin-build package**

Create `packages/nsjail-bin-build/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nsjail-bin-build"
version = "0.1.0"
description = "Build nsjail from source for nsjail-python"
requires-python = ">=3.12"
license = "MIT"

[tool.hatch.build.targets.wheel]
packages = ["src/nsjail_bin_build"]
```

Create `packages/nsjail-bin-build/src/nsjail_bin_build/__init__.py`:
```python
"""Build-from-source nsjail binary distribution."""

from pathlib import Path


def binary_path() -> Path:
    """Return the path to the built nsjail binary."""
    bin_path = Path(__file__).parent / "_bin" / "nsjail"
    if not bin_path.exists():
        raise FileNotFoundError(
            f"Built nsjail binary not found at {bin_path}. "
            f"The build may have failed during installation. "
            f"Check build logs or try: pip install nsjail-python"
        )
    return bin_path
```

- [ ] **Step 3: Create nsjail-bin-none package**

Create `packages/nsjail-bin-none/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nsjail-bin-none"
version = "0.1.0"
description = "No-op nsjail binary package (use system nsjail)"
requires-python = ">=3.12"
license = "MIT"

[tool.hatch.build.targets.wheel]
packages = ["src/nsjail_bin_none"]
```

Create `packages/nsjail-bin-none/src/nsjail_bin_none/__init__.py`:
```python
"""No-op companion package. System-provided nsjail is expected."""
```

- [ ] **Step 4: Verify packages are importable**

Run:
```bash
cd /mnt/aux-data/teague/Projects/nsjail-python
pip install -e packages/nsjail-bin-none/
python -c "import nsjail_bin_none; print('ok')"
```
Expected: Prints "ok".

- [ ] **Step 5: Commit**

```bash
git add packages/
git commit -m "feat: add companion packages (nsjail-bin, nsjail-bin-build, nsjail-bin-none)"
```

---

### Task 13: Code Generator

**Files:**
- Create: `_codegen/generate.py`
- Create: `_codegen/cli_flags.py`
- Modify: `_codegen/__init__.py`

This task creates the code generator that reads `config.proto` and emits `config.py`, `enums.py`, and `_field_meta.py`. For v0.1, it uses a simple regex-based proto parser (nsjail's proto is a simple subset of proto2).

- [ ] **Step 1: Create CLI flags table**

Create `_codegen/cli_flags.py`:
```python
"""Hand-maintained mapping of proto field names to CLI flags.

The code generator merges this table into _field_meta.py.
Fields not listed here are assumed to have no CLI equivalent.
"""

# (message_name, field_name) -> (cli_flag, cli_supported)
CLI_FLAGS: dict[tuple[str, str], tuple[str, bool]] = {
    # NsJailConfig scalars
    ("NsJailConfig", "name"): ("--name", True),
    ("NsJailConfig", "hostname"): ("--hostname", True),
    ("NsJailConfig", "cwd"): ("--cwd", True),
    ("NsJailConfig", "port"): ("--port", True),
    ("NsJailConfig", "bindhost"): ("--bindhost", True),
    ("NsJailConfig", "max_conns"): ("--max_conns", True),
    ("NsJailConfig", "max_conns_per_ip"): ("--max_conns_per_ip", True),
    ("NsJailConfig", "time_limit"): ("--time_limit", True),
    ("NsJailConfig", "daemon"): ("--daemon", True),
    ("NsJailConfig", "max_cpus"): ("--max_cpus", True),
    ("NsJailConfig", "nice_level"): ("--nice_level", True),
    ("NsJailConfig", "keep_env"): ("--keep_env", True),
    ("NsJailConfig", "envar"): ("--env", True),
    ("NsJailConfig", "silent"): ("--silent", True),
    ("NsJailConfig", "skip_setsid"): ("--skip_setsid", True),
    ("NsJailConfig", "stderr_to_null"): ("--stderr_to_null", True),
    ("NsJailConfig", "pass_fd"): ("--pass_fd", True),
    ("NsJailConfig", "disable_no_new_privs"): ("--disable_no_new_privs", True),
    ("NsJailConfig", "forward_signals"): ("--forward_signals", True),
    ("NsJailConfig", "disable_tsc"): ("--disable_tsc", True),
    ("NsJailConfig", "oom_score_adj"): ("--oom_score_adj", True),
    ("NsJailConfig", "log_fd"): ("--log_fd", True),
    ("NsJailConfig", "log_file"): ("--log", True),
    ("NsJailConfig", "keep_caps"): ("--keep_caps", True),
    ("NsJailConfig", "cap"): ("--cap", True),
    ("NsJailConfig", "rlimit_as"): ("--rlimit_as", True),
    ("NsJailConfig", "rlimit_core"): ("--rlimit_core", True),
    ("NsJailConfig", "rlimit_cpu"): ("--rlimit_cpu", True),
    ("NsJailConfig", "rlimit_fsize"): ("--rlimit_fsize", True),
    ("NsJailConfig", "rlimit_nofile"): ("--rlimit_nofile", True),
    ("NsJailConfig", "rlimit_nproc"): ("--rlimit_nproc", True),
    ("NsJailConfig", "rlimit_stack"): ("--rlimit_stack", True),
    ("NsJailConfig", "disable_rl"): ("--disable_rl", True),
    # Namespaces — CLI uses disable_ prefix for the true-by-default ones
    ("NsJailConfig", "clone_newnet"): (None, True),
    ("NsJailConfig", "clone_newuser"): (None, True),
    ("NsJailConfig", "clone_newns"): (None, True),
    ("NsJailConfig", "clone_newpid"): (None, True),
    ("NsJailConfig", "clone_newipc"): (None, True),
    ("NsJailConfig", "clone_newuts"): (None, True),
    ("NsJailConfig", "clone_newcgroup"): (None, True),
    ("NsJailConfig", "clone_newtime"): (None, True),
    # UID/GID
    ("NsJailConfig", "uidmap"): ("--uid_mapping", True),
    ("NsJailConfig", "gidmap"): ("--gid_mapping", True),
    # Mounts
    ("NsJailConfig", "mount_proc"): ("--mount_proc", True),
    ("NsJailConfig", "no_pivotroot"): ("--no_pivotroot", True),
    # Seccomp
    ("NsJailConfig", "seccomp_policy_file"): ("--seccomp_policy", True),
    ("NsJailConfig", "seccomp_string"): ("--seccomp_string", True),
    ("NsJailConfig", "seccomp_log"): ("--seccomp_log", True),
    # Cgroups
    ("NsJailConfig", "cgroup_mem_max"): ("--cgroup_mem_max", True),
    ("NsJailConfig", "cgroup_mem_memsw_max"): ("--cgroup_mem_memsw_max", True),
    ("NsJailConfig", "cgroup_mem_swap_max"): ("--cgroup_mem_swap_max", True),
    ("NsJailConfig", "cgroup_pids_max"): ("--cgroup_pids_max", True),
    ("NsJailConfig", "cgroup_net_cls_classid"): ("--cgroup_net_cls_classid", True),
    ("NsJailConfig", "cgroup_cpu_ms_per_sec"): ("--cgroup_cpu_ms_per_sec", True),
    ("NsJailConfig", "use_cgroupv2"): ("--use_cgroupv2", True),
    ("NsJailConfig", "detect_cgroupv2"): ("--detect_cgroupv2", True),
    # Networking
    ("NsJailConfig", "iface_no_lo"): ("--iface_no_lo", True),
    ("NsJailConfig", "iface_own"): ("--iface_own", True),
    ("NsJailConfig", "macvlan_iface"): ("--macvlan_iface", True),
    ("NsJailConfig", "macvlan_vs_ip"): ("--macvlan_vs_ip", True),
    ("NsJailConfig", "macvlan_vs_nm"): ("--macvlan_vs_nm", True),
    ("NsJailConfig", "macvlan_vs_gw"): ("--macvlan_vs_gw", True),
    ("NsJailConfig", "macvlan_vs_ma"): ("--macvlan_vs_ma", True),
    ("NsJailConfig", "macvlan_vs_mo"): ("--macvlan_vs_mo", True),
}
```

- [ ] **Step 2: Create code generator**

Create `_codegen/generate.py`:
```python
"""Code generator: reads config.proto, emits config.py, enums.py, _field_meta.py.

Usage:
    python -m _codegen.generate [path/to/config.proto]

If no path given, uses _codegen/config.proto (vendored).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from _codegen.cli_flags import CLI_FLAGS

HEADER = '''\
# GENERATED from nsjail config.proto — DO NOT EDIT
# Re-run: python -m _codegen.generate
'''


@dataclass
class ProtoField:
    label: str  # "optional", "repeated", "required"
    type: str
    name: str
    number: int
    default: str | None


@dataclass
class ProtoEnum:
    name: str
    values: list[tuple[str, int]]


@dataclass
class ProtoMessage:
    name: str
    fields: list[ProtoField]
    enums: list[ProtoEnum]
    messages: list[ProtoMessage]


def parse_proto(text: str) -> list[ProtoMessage | ProtoEnum]:
    """Simple regex-based parser for the subset of proto2 used by nsjail.

    This is NOT a general-purpose proto parser. It handles:
    - message definitions (including nested)
    - enum definitions
    - field declarations with optional defaults
    - // comments
    """
    # Strip comments
    text = re.sub(r'//[^\n]*', '', text)

    results: list[ProtoMessage | ProtoEnum] = []
    _parse_block(text, results)
    return results


def _parse_block(text: str, results: list) -> None:
    """Recursively parse messages and enums from a block of proto text."""
    # Find top-level messages and enums
    pos = 0
    while pos < len(text):
        # Match enum
        m = re.match(r'\s*enum\s+(\w+)\s*\{', text[pos:])
        if m:
            name = m.group(1)
            brace_start = pos + m.end()
            brace_end = _find_matching_brace(text, brace_start - 1)
            body = text[brace_start:brace_end]
            values = re.findall(r'(\w+)\s*=\s*(\d+)', body)
            results.append(ProtoEnum(name=name, values=[(n, int(v)) for n, v in values]))
            pos = brace_end + 1
            continue

        # Match message
        m = re.match(r'\s*message\s+(\w+)\s*\{', text[pos:])
        if m:
            name = m.group(1)
            brace_start = pos + m.end()
            brace_end = _find_matching_brace(text, brace_start - 1)
            body = text[brace_start:brace_end]

            msg = ProtoMessage(name=name, fields=[], enums=[], messages=[])

            # Parse nested messages and enums first
            nested: list = []
            _parse_block(body, nested)
            for item in nested:
                if isinstance(item, ProtoEnum):
                    msg.enums.append(item)
                elif isinstance(item, ProtoMessage):
                    msg.messages.append(item)

            # Parse fields (after stripping nested blocks)
            stripped = _strip_nested_blocks(body)
            field_pattern = re.compile(
                r'(repeated|optional|required)?\s*(\w+)\s+(\w+)\s*=\s*(\d+)'
                r'(?:\s*\[\s*default\s*=\s*([^\]]+)\])?\s*;'
            )
            for fm in field_pattern.finditer(stripped):
                label = fm.group(1) or "optional"
                msg.fields.append(ProtoField(
                    label=label,
                    type=fm.group(2),
                    name=fm.group(3),
                    number=int(fm.group(4)),
                    default=fm.group(5).strip() if fm.group(5) else None,
                ))

            results.append(msg)
            pos = brace_end + 1
            continue

        pos += 1


def _find_matching_brace(text: str, open_pos: int) -> int:
    """Find the matching closing brace."""
    depth = 1
    pos = open_pos + 1
    while pos < len(text) and depth > 0:
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
        pos += 1
    return pos - 1


def _strip_nested_blocks(text: str) -> str:
    """Remove nested message{} and enum{} blocks, leaving only fields."""
    result = []
    pos = 0
    while pos < len(text):
        m = re.match(r'\s*(message|enum)\s+\w+\s*\{', text[pos:])
        if m:
            brace_start = pos + m.end()
            brace_end = _find_matching_brace(text, brace_start - 1)
            pos = brace_end + 1
        else:
            result.append(text[pos])
            pos += 1
    return ''.join(result)


def main() -> None:
    proto_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("_codegen/config.proto")
    if not proto_path.exists():
        print(f"Error: {proto_path} not found", file=sys.stderr)
        print("Download it: curl -o _codegen/config.proto "
              "https://raw.githubusercontent.com/google/nsjail/master/config.proto",
              file=sys.stderr)
        sys.exit(1)

    text = proto_path.read_text()
    items = parse_proto(text)

    print(f"Parsed {len(items)} top-level items from {proto_path}")
    for item in items:
        if isinstance(item, ProtoMessage):
            print(f"  message {item.name}: {len(item.fields)} fields, "
                  f"{len(item.enums)} enums, {len(item.messages)} nested messages")
        elif isinstance(item, ProtoEnum):
            print(f"  enum {item.name}: {len(item.values)} values")

    # TODO: Emit config.py, enums.py, _field_meta.py from parsed items.
    # For now, these files are hand-written. The generator will be completed
    # when we vendor config.proto and validate the parser against it.
    print("\nGenerator parsed successfully. Code emission not yet implemented.")
    print("Hand-written files in src/nsjail/ are authoritative for v0.1.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Test the parser**

Run:
```bash
cd /mnt/aux-data/teague/Projects/nsjail-python
curl -o _codegen/config.proto https://raw.githubusercontent.com/google/nsjail/master/config.proto
python -m _codegen.generate
```
Expected: Prints parsed message/enum counts without errors.

- [ ] **Step 4: Commit**

```bash
git add _codegen/
git commit -m "feat: add proto parser and CLI flags table for code generator"
```

---

### Task 14: Vendor nsjail as git submodule

**Files:**
- Create: `_vendor/nsjail` (git submodule)

- [ ] **Step 1: Add nsjail as git submodule**

Run:
```bash
cd /mnt/aux-data/teague/Projects/nsjail-python
git submodule add https://github.com/google/nsjail.git _vendor/nsjail
cd _vendor/nsjail
git checkout $(git describe --tags --abbrev=0)
cd ../..
```

- [ ] **Step 2: Initialize kafel submodule**

Run:
```bash
cd /mnt/aux-data/teague/Projects/nsjail-python/_vendor/nsjail
git submodule update --init
cd ../..
```

- [ ] **Step 3: Symlink config.proto for codegen**

Run:
```bash
cd /mnt/aux-data/teague/Projects/nsjail-python
ln -sf ../../_vendor/nsjail/config.proto _codegen/config.proto
```

- [ ] **Step 4: Test generator with vendored proto**

Run:
```bash
python -m _codegen.generate _vendor/nsjail/config.proto
```
Expected: Parses successfully.

- [ ] **Step 5: Commit**

```bash
git add _vendor/ _codegen/config.proto .gitmodules
git commit -m "feat: vendor nsjail as git submodule"
```

---

### Task 15: End-to-end Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write end-to-end test**

Create `tests/test_integration.py`:
```python
"""End-to-end tests for nsjail-python.

These tests verify the full workflow from builder to serialized config.
They do NOT require nsjail to be installed.
"""

from nsjail import Jail, NsJailConfig, MountPt, Exe, sandbox, Runner
from nsjail.serializers import to_textproto, to_cli_args, to_file


class TestBuilderToTextproto:
    def test_full_pipeline(self):
        cfg = (
            Jail()
            .sh("echo hello")
            .timeout(30)
            .memory(256, "MB")
            .no_network()
            .readonly_root()
            .writable("/tmp", tmpfs=True, size="32M")
            .env("HOME=/root")
            .build()
        )

        text = to_textproto(cfg)

        assert "time_limit: 30" in text
        assert 'envar: "HOME=/root"' in text
        assert "exec_bin {" in text
        assert 'path: "/bin/sh"' in text
        assert "mount {" in text
        assert text.count("{") == text.count("}")

    def test_sandbox_to_textproto(self):
        cfg = sandbox(
            command=["python", "script.py"],
            cwd="/workspace",
            timeout_sec=60,
            memory_mb=512,
            writable_dirs=["/workspace", "/tmp"],
        )

        text = to_textproto(cfg)

        assert "time_limit: 60" in text
        assert 'cwd: "/workspace"' in text
        assert "cgroup_mem_max:" in text


class TestBuilderToCliArgs:
    def test_simple_config(self):
        cfg = NsJailConfig(
            hostname="test",
            time_limit=30,
            keep_env=True,
            envar=["A=1"],
        )
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--hostname" in args
        assert "--time_limit" in args
        assert "--keep_env" in args
        assert "--env" in args


class TestTextprotoToFile(tmp_path_factory=None):
    def test_write_and_read(self, tmp_path):
        cfg = (
            Jail()
            .sh("true")
            .timeout(10)
            .build()
        )
        path = tmp_path / "test.cfg"
        to_file(cfg, path)

        content = path.read_text()
        assert "time_limit: 10" in content
        assert "exec_bin {" in content
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: All tests pass.

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests"
```
