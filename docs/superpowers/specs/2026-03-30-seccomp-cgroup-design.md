# Seccomp Policy Helpers & Cgroup Stats Recovery Design Spec

**Date:** 2026-03-30
**Status:** Draft
**Scope:** Two independent features batched into a single spec

## Context

nsjail-python v0.2.0 has config fields for seccomp (`seccomp_string`, `seccomp_policy_file`, `seccomp_log`) and cgroups (`cgroup_mem_max`, `cgroup_cpu_ms_per_sec`, etc.), but no high-level Python API for building seccomp policies or recovering resource usage stats from cgroups. These two features complete the sandbox observability story.

## Feature 1: Seccomp Policy Helpers

### New module: `src/nsjail/seccomp.py`

A `SeccompPolicy` builder that generates Kafel policy strings, plus preset policies for common scenarios.

### SeccompPolicy builder

Fluent API that accumulates syscall rules and renders to Kafel syntax on `str()`.

```python
from nsjail.seccomp import SeccompPolicy

policy = (
    SeccompPolicy("my_policy")
    .allow("read", "write", "close", "exit_group", "mmap", "brk")
    .deny("execve", "fork", "clone")
    .errno(1, "open", "openat")
    .log("connect", "socket")
    .default_kill()
)

print(str(policy))
# POLICY my_policy {
#   ALLOW { read, write, close, exit_group, mmap, brk }
#   KILL { execve, fork, clone }
#   ERRNO(1) { open, openat }
#   LOG { connect, socket }
# } USE my_policy DEFAULT KILL
```

### Methods

- `.allow(*syscalls)` — add syscalls to ALLOW group
- `.deny(*syscalls)` — add syscalls to KILL group
- `.errno(errno, *syscalls)` — add syscalls to ERRNO(n) group
- `.log(*syscalls)` — add syscalls to LOG group
- `.trap(signo, *syscalls)` — add syscalls to TRAP(n) group
- `.default_kill()` — set default action to KILL
- `.default_allow()` — set default action to ALLOW
- `.default_log()` — set default action to LOG
- `.default_errno(errno)` — set default action to ERRNO(n)

Each method returns `self` for chaining. The policy name defaults to `"policy"` if not provided.

### Rendering

`__str__()` renders to valid Kafel syntax. The output is a single string suitable for `cfg.seccomp_string.append(str(policy))`.

Rules are grouped by action. Within each group, syscalls are comma-separated. The format:

```
POLICY <name> {
  <ACTION> { <syscall1>, <syscall2>, ... }
  ...
} USE <name> DEFAULT <action>
```

### Presets

Pre-built `SeccompPolicy` instances for common scenarios:

**`MINIMAL`** — allows basic process lifecycle: read, write, close, exit, exit_group, brk, mmap, munmap, mprotect, rt_sigaction, rt_sigprocmask, sigreturn, clock_gettime, getpid, gettid. Kills everything else.

**`DEFAULT_LOG`** — logs all syscalls without blocking. For learning/auditing mode. Sets `default_log()` with no explicit allow/deny rules.

**`READONLY`** — allows reads and memory operations but blocks writes to files, exec, fork, network. Uses ERRNO(EPERM) for denied calls instead of KILL (more graceful failure).

### Jail builder integration

Add a `.seccomp()` method to the Jail builder:

```python
from nsjail.seccomp import SeccompPolicy, MINIMAL

# With a preset
cfg = Jail().sh("echo hi").seccomp(MINIMAL).build()

# With a custom policy
cfg = Jail().sh("echo hi").seccomp(
    SeccompPolicy().allow("read", "write").default_kill()
).build()

# With a raw Kafel string
cfg = Jail().sh("echo hi").seccomp("POLICY p { ALLOW { read } } USE p DEFAULT KILL").build()
```

The `.seccomp()` method accepts either a `SeccompPolicy`, a raw Kafel string, or a preset. It appends to `cfg.seccomp_string`.

### No argument filtering in v1

Kafel supports syscall argument filtering (e.g., `read { fd == 0 && count == 0 }`). This is not exposed in the builder for v1 — users who need argument filtering write raw Kafel strings. The builder covers the common case of allow/deny by syscall name.

## Feature 2: Cgroup Stats Recovery

### Problem

nsjail deletes cgroups immediately after the sandboxed process exits. By the time `Runner.run()` returns, the cgroup stat files are gone. We need to capture stats while the process is still running.

### Approach: Background monitor thread

A `CgroupMonitor` thread polls cgroup stat files at a configurable interval while the sandboxed process runs. When the process exits (or the cgroup disappears), the monitor returns the last captured values.

### New module: `src/nsjail/cgroup.py`

#### CgroupStats dataclass

```python
@dataclass
class CgroupStats:
    memory_peak_bytes: int | None = None
    memory_current_bytes: int | None = None
    cpu_usage_ns: int | None = None
    cpu_user_ns: int | None = None
    cpu_system_ns: int | None = None
    pids_current: int | None = None
```

All fields are optional — if a cgroup controller isn't configured or the stat file doesn't exist, the field is `None`.

#### CgroupMonitor

```python
class CgroupMonitor:
    def __init__(
        self,
        cgroup_path: Path,
        poll_interval: float = 0.1,
        use_v2: bool = False,
    ):
        """Monitor cgroup stats for a sandboxed process.

        Args:
            cgroup_path: Path to the cgroup directory (e.g., /sys/fs/cgroup/memory/NSJAIL/NSJAIL.12345)
            poll_interval: Seconds between stat reads (default 100ms)
            use_v2: Use cgroup v2 stat file paths
        """

    def start(self) -> None:
        """Start the monitoring thread."""

    def stop(self) -> CgroupStats:
        """Stop monitoring and return the last captured stats."""
```

The monitor thread:
1. Reads stat files every `poll_interval` seconds
2. Stores the latest values in thread-safe storage
3. Exits when `stop()` is called or the cgroup directory disappears
4. Returns the last successfully read stats

#### Stat file paths

**Cgroup v1:**
- `memory.max_usage_in_bytes` → `memory_peak_bytes`
- `memory.usage_in_bytes` → `memory_current_bytes`
- `cpuacct.usage` → `cpu_usage_ns`
- `pids.current` → `pids_current`

**Cgroup v2:**
- `memory.peak` → `memory_peak_bytes`
- `memory.current` → `memory_current_bytes`
- `cpu.stat` (parsed) → `cpu_usage_ns`, `cpu_user_ns`, `cpu_system_ns`
- `pids.current` → `pids_current`

### Cgroup path discovery

nsjail creates cgroups named `NSJAIL.{pid}` under the configured parent. The monitor needs to find this directory.

Strategy:
1. After starting the nsjail subprocess, we know its PID
2. Construct the expected cgroup path: `{cgroup_mount}/{cgroup_parent}/NSJAIL.{pid}`
3. Poll for the directory to appear (nsjail creates it asynchronously after start)
4. If it doesn't appear within 2 seconds, give up and return None stats

For cgroup v2, the path is simpler: `{cgroupv2_mount}/{parent}/NSJAIL.{pid}`

For cgroup v1, we need separate paths per controller:
- Memory: `{cgroup_mem_mount}/{cgroup_mem_parent}/NSJAIL.{pid}`
- CPU: `{cgroup_cpu_mount}/{cgroup_cpu_parent}/NSJAIL.{pid}`
- PIDs: `{cgroup_pids_mount}/{cgroup_pids_parent}/NSJAIL.{pid}`

### Runner integration

#### NsJailResult update

Add `cgroup_stats` field:

```python
@dataclass
class NsJailResult:
    # ... existing fields ...
    cgroup_stats: CgroupStats | None = None
```

#### Runner opt-in

```python
runner = Runner(
    base_config=cfg,
    collect_cgroup_stats=True,   # default False
    cgroup_poll_interval=0.1,    # seconds, default 0.1
)
result = runner.run()
if result.cgroup_stats:
    print(f"Peak memory: {result.cgroup_stats.memory_peak_bytes}")
    print(f"CPU time: {result.cgroup_stats.cpu_usage_ns}ns")
```

When `collect_cgroup_stats=True`, `Runner.run()`:
1. Starts the nsjail subprocess
2. Determines cgroup paths from the config and nsjail PID
3. Starts a `CgroupMonitor`
4. Waits for subprocess to complete
5. Stops the monitor and captures stats
6. Includes stats in `NsJailResult.cgroup_stats`

For `async_run()`, the monitor runs in a thread (not async — reading /sys files is blocking and fast).

### Limitations

- Stats are approximate — the last poll before cgroup deletion may miss the final values
- `memory.peak` (v2) is more reliable than polling `memory.usage_in_bytes` (v1) since it's maintained by the kernel
- Requires the nsjail process to actually create cgroups (i.e., `cgroup_mem_max > 0` or similar must be configured)
- Requires read access to cgroup filesystem (typically needs root or cgroup delegation)

## Testing Strategy

### Seccomp tests
- Unit tests: policy builder produces correct Kafel strings
- Test presets render to valid Kafel
- Test builder integration (`.seccomp()` method)
- No runtime seccomp testing (would need root + nsjail)

### Cgroup tests
- Unit tests: CgroupStats dataclass construction
- Unit tests: CgroupMonitor with mocked stat files (write temp files, verify reads)
- Unit tests: stat file parsing (v1 and v2 formats)
- Integration: Runner with `collect_cgroup_stats=True` using mocked subprocess
- No runtime cgroup testing (needs root + cgroups configured)

## Scope Boundaries

**In scope:**
- SeccompPolicy builder with allow/deny/errno/log/trap
- Three presets (MINIMAL, DEFAULT_LOG, READONLY)
- Jail `.seccomp()` method
- CgroupStats dataclass
- CgroupMonitor thread with v1/v2 support
- Runner integration (opt-in cgroup collection)
- NsJailResult.cgroup_stats field

**Out of scope:**
- Kafel argument filtering in the builder
- Seccomp learning mode (parsing audit logs)
- Cgroup creation/management (nsjail handles this)
- Real nsjail integration tests
