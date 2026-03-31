# Seccomp Policy Helpers & Cgroup Stats Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a SeccompPolicy builder with presets for generating Kafel policies, and a CgroupMonitor for capturing resource usage stats during nsjail execution.

**Architecture:** SeccompPolicy is a standalone builder that renders to Kafel strings. CgroupMonitor is a background thread that polls cgroup stat files while nsjail runs. Both integrate into the existing Jail builder and Runner.

**Tech Stack:** Python 3.12+, dataclasses, threading

**Spec:** `docs/superpowers/specs/2026-03-30-seccomp-cgroup-design.md`

---

### Task 1: SeccompPolicy Builder

**Files:**
- Create: `src/nsjail/seccomp.py`
- Create: `tests/test_seccomp.py`

- [ ] **Step 1: Write tests for SeccompPolicy**

Create `tests/test_seccomp.py`:

```python
from nsjail.seccomp import SeccompPolicy


class TestSeccompPolicyBuilder:
    def test_empty_policy_with_default(self):
        policy = SeccompPolicy("test").default_kill()
        text = str(policy)
        assert "POLICY test" in text
        assert "DEFAULT KILL" in text

    def test_allow_syscalls(self):
        policy = SeccompPolicy("p").allow("read", "write").default_kill()
        text = str(policy)
        assert "ALLOW { read, write }" in text

    def test_deny_syscalls(self):
        policy = SeccompPolicy("p").deny("execve", "fork").default_allow()
        text = str(policy)
        assert "KILL { execve, fork }" in text

    def test_errno_syscalls(self):
        policy = SeccompPolicy("p").errno(1, "open", "openat").default_kill()
        text = str(policy)
        assert "ERRNO(1) { open, openat }" in text

    def test_log_syscalls(self):
        policy = SeccompPolicy("p").log("connect").default_kill()
        text = str(policy)
        assert "LOG { connect }" in text

    def test_trap_syscalls(self):
        policy = SeccompPolicy("p").trap(5, "ptrace").default_kill()
        text = str(policy)
        assert "TRAP(5) { ptrace }" in text

    def test_multiple_rules(self):
        policy = (
            SeccompPolicy("multi")
            .allow("read", "write", "close")
            .deny("execve")
            .errno(13, "open")
            .default_kill()
        )
        text = str(policy)
        assert "ALLOW { read, write, close }" in text
        assert "KILL { execve }" in text
        assert "ERRNO(13) { open }" in text
        assert "DEFAULT KILL" in text

    def test_chaining_returns_self(self):
        policy = SeccompPolicy("p")
        result = policy.allow("read")
        assert result is policy

    def test_default_name(self):
        policy = SeccompPolicy().allow("read").default_kill()
        text = str(policy)
        assert "POLICY policy" in text

    def test_default_allow(self):
        policy = SeccompPolicy("p").deny("execve").default_allow()
        text = str(policy)
        assert "DEFAULT ALLOW" in text

    def test_default_log(self):
        policy = SeccompPolicy("p").default_log()
        text = str(policy)
        assert "DEFAULT LOG" in text

    def test_default_errno(self):
        policy = SeccompPolicy("p").default_errno(1)
        text = str(policy)
        assert "DEFAULT ERRNO(1)" in text

    def test_use_statement(self):
        policy = SeccompPolicy("mypol").allow("read").default_kill()
        text = str(policy)
        assert "USE mypol" in text

    def test_accumulates_across_calls(self):
        policy = SeccompPolicy("p").allow("read").allow("write").default_kill()
        text = str(policy)
        assert "read" in text
        assert "write" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_seccomp.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement SeccompPolicy**

Create `src/nsjail/seccomp.py`:

```python
"""Seccomp policy builder and presets for nsjail.

Generates Kafel policy strings from a fluent Python API.
"""

from __future__ import annotations


class SeccompPolicy:
    """Builder for Kafel seccomp policy strings.

    Usage:
        policy = (
            SeccompPolicy("my_policy")
            .allow("read", "write", "close")
            .deny("execve")
            .default_kill()
        )
        cfg.seccomp_string.append(str(policy))
    """

    def __init__(self, name: str = "policy") -> None:
        self._name = name
        self._rules: list[tuple[str, list[str]]] = []
        self._default: str = "KILL"

    def allow(self, *syscalls: str) -> SeccompPolicy:
        """Add syscalls to ALLOW group."""
        self._add_rules("ALLOW", syscalls)
        return self

    def deny(self, *syscalls: str) -> SeccompPolicy:
        """Add syscalls to KILL group."""
        self._add_rules("KILL", syscalls)
        return self

    def errno(self, errno: int, *syscalls: str) -> SeccompPolicy:
        """Add syscalls to ERRNO(n) group."""
        self._add_rules(f"ERRNO({errno})", syscalls)
        return self

    def log(self, *syscalls: str) -> SeccompPolicy:
        """Add syscalls to LOG group."""
        self._add_rules("LOG", syscalls)
        return self

    def trap(self, signo: int, *syscalls: str) -> SeccompPolicy:
        """Add syscalls to TRAP(n) group."""
        self._add_rules(f"TRAP({signo})", syscalls)
        return self

    def default_kill(self) -> SeccompPolicy:
        """Set default action to KILL."""
        self._default = "KILL"
        return self

    def default_allow(self) -> SeccompPolicy:
        """Set default action to ALLOW."""
        self._default = "ALLOW"
        return self

    def default_log(self) -> SeccompPolicy:
        """Set default action to LOG."""
        self._default = "LOG"
        return self

    def default_errno(self, errno: int) -> SeccompPolicy:
        """Set default action to ERRNO(n)."""
        self._default = f"ERRNO({errno})"
        return self

    def _add_rules(self, action: str, syscalls: tuple[str, ...]) -> None:
        """Add syscalls to an action group, merging with existing."""
        for existing_action, existing_syscalls in self._rules:
            if existing_action == action:
                existing_syscalls.extend(syscalls)
                return
        self._rules.append((action, list(syscalls)))

    def __str__(self) -> str:
        """Render to Kafel policy string."""
        lines = [f"POLICY {self._name} {{"]
        for action, syscalls in self._rules:
            lines.append(f"  {action} {{ {', '.join(syscalls)} }}")
        lines.append(f"}} USE {self._name} DEFAULT {self._default}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_seccomp.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/seccomp.py tests/test_seccomp.py
git commit -m "feat: add SeccompPolicy builder for Kafel policy generation"
```

---

### Task 2: Seccomp Presets

**Files:**
- Modify: `src/nsjail/seccomp.py`
- Modify: `tests/test_seccomp.py`

- [ ] **Step 1: Write tests for presets**

Add to `tests/test_seccomp.py`:

```python
from nsjail.seccomp import MINIMAL, DEFAULT_LOG, READONLY


class TestSeccompPresets:
    def test_minimal_is_seccomp_policy(self):
        assert isinstance(MINIMAL, SeccompPolicy)

    def test_minimal_allows_basic_syscalls(self):
        text = str(MINIMAL)
        assert "read" in text
        assert "write" in text
        assert "close" in text
        assert "exit_group" in text
        assert "DEFAULT KILL" in text

    def test_minimal_valid_kafel(self):
        text = str(MINIMAL)
        assert "POLICY " in text
        assert "ALLOW {" in text
        assert "} USE " in text

    def test_default_log_uses_log_default(self):
        text = str(DEFAULT_LOG)
        assert "DEFAULT LOG" in text

    def test_readonly_blocks_writes(self):
        text = str(READONLY)
        # Should deny write-related syscalls
        assert "write" in text.lower() or "ERRNO" in text
        assert "DEFAULT" in text

    def test_presets_are_independent(self):
        t1 = str(MINIMAL)
        t2 = str(MINIMAL)
        assert t1 == t2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_seccomp.py::TestSeccompPresets -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Add presets to seccomp.py**

Add at the bottom of `src/nsjail/seccomp.py`:

```python
# --- Presets ---

MINIMAL = (
    SeccompPolicy("minimal")
    .allow(
        "read", "write", "close", "exit", "exit_group",
        "brk", "mmap", "munmap", "mprotect", "mremap",
        "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
        "clock_gettime", "clock_getres", "gettimeofday",
        "getpid", "gettid", "getuid", "getgid", "geteuid", "getegid",
        "futex", "nanosleep", "sched_yield",
        "access", "fstat", "stat", "lstat",
        "arch_prctl", "set_tid_address", "set_robust_list",
        "prlimit64", "getrandom",
    )
    .default_kill()
)

DEFAULT_LOG = SeccompPolicy("log_all").default_log()

READONLY = (
    SeccompPolicy("readonly")
    .allow(
        "read", "pread64", "readv", "close", "exit", "exit_group",
        "brk", "mmap", "munmap", "mprotect", "mremap",
        "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
        "clock_gettime", "clock_getres", "gettimeofday",
        "getpid", "gettid", "getuid", "getgid", "geteuid", "getegid",
        "futex", "nanosleep", "sched_yield",
        "access", "fstat", "stat", "lstat", "statfs",
        "openat", "fstatfs", "getdents64", "lseek",
        "arch_prctl", "set_tid_address", "set_robust_list",
        "prlimit64", "getrandom", "ioctl",
    )
    .errno(1, "write", "pwrite64", "writev", "truncate", "ftruncate")
    .deny("execve", "execveat", "fork", "vfork", "clone", "clone3")
    .errno(1, "socket", "connect", "bind", "listen", "accept", "accept4")
    .default_errno(1)
)
```

- [ ] **Step 4: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_seccomp.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/seccomp.py tests/test_seccomp.py
git commit -m "feat: add seccomp presets (MINIMAL, DEFAULT_LOG, READONLY)"
```

---

### Task 3: Jail Builder .seccomp() Method

**Files:**
- Modify: `src/nsjail/builder.py`
- Modify: `tests/test_builder.py`

- [ ] **Step 1: Write tests**

Add to `tests/test_builder.py`:

```python
from nsjail.seccomp import SeccompPolicy, MINIMAL


class TestBuilderSeccomp:
    def test_seccomp_with_policy(self):
        policy = SeccompPolicy("test").allow("read").default_kill()
        cfg = Jail().sh("true").seccomp(policy).build()
        assert len(cfg.seccomp_string) == 1
        assert "ALLOW { read }" in cfg.seccomp_string[0]

    def test_seccomp_with_preset(self):
        cfg = Jail().sh("true").seccomp(MINIMAL).build()
        assert len(cfg.seccomp_string) == 1
        assert "read" in cfg.seccomp_string[0]

    def test_seccomp_with_raw_string(self):
        raw = "POLICY p { ALLOW { read } } USE p DEFAULT KILL"
        cfg = Jail().sh("true").seccomp(raw).build()
        assert len(cfg.seccomp_string) == 1
        assert cfg.seccomp_string[0] == raw

    def test_seccomp_multiple(self):
        cfg = (
            Jail()
            .sh("true")
            .seccomp(MINIMAL)
            .seccomp("POLICY extra { ALLOW { openat } } USE extra DEFAULT KILL")
            .build()
        )
        assert len(cfg.seccomp_string) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_builder.py::TestBuilderSeccomp -v`
Expected: FAIL with TypeError (seccomp method exists but doesn't accept SeccompPolicy).

- [ ] **Step 3: Update builder.py**

The existing `seccomp_log()` method stays. Add a new `seccomp()` method to the Jail class in `src/nsjail/builder.py`:

```python
    def seccomp(self, policy: SeccompPolicy | str) -> Jail:
        """Add a seccomp policy. Accepts a SeccompPolicy, preset, or raw Kafel string."""
        from nsjail.seccomp import SeccompPolicy as _SeccompPolicy
        if isinstance(policy, _SeccompPolicy):
            self._cfg.seccomp_string.append(str(policy))
        else:
            self._cfg.seccomp_string.append(policy)
        return self
```

Also add the TYPE_CHECKING import for SeccompPolicy at the top:

```python
if TYPE_CHECKING:
    from nsjail.runner import Runner, NsJailResult
    from nsjail.seccomp import SeccompPolicy
```

- [ ] **Step 4: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_builder.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/builder.py tests/test_builder.py
git commit -m "feat: add .seccomp() method to Jail builder"
```

---

### Task 4: CgroupStats Dataclass

**Files:**
- Create: `src/nsjail/cgroup.py`
- Create: `tests/test_cgroup.py`

- [ ] **Step 1: Write tests**

Create `tests/test_cgroup.py`:

```python
from nsjail.cgroup import CgroupStats


class TestCgroupStats:
    def test_defaults_are_none(self):
        stats = CgroupStats()
        assert stats.memory_peak_bytes is None
        assert stats.memory_current_bytes is None
        assert stats.cpu_usage_ns is None
        assert stats.cpu_user_ns is None
        assert stats.cpu_system_ns is None
        assert stats.pids_current is None

    def test_with_values(self):
        stats = CgroupStats(
            memory_peak_bytes=1024 * 1024,
            memory_current_bytes=512 * 1024,
            cpu_usage_ns=1_000_000_000,
            pids_current=5,
        )
        assert stats.memory_peak_bytes == 1024 * 1024
        assert stats.cpu_usage_ns == 1_000_000_000
        assert stats.pids_current == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_cgroup.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement CgroupStats**

Create `src/nsjail/cgroup.py`:

```python
"""Cgroup stats monitoring for nsjail sandboxes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CgroupStats:
    """Resource usage stats captured from cgroup stat files."""

    memory_peak_bytes: int | None = None
    memory_current_bytes: int | None = None
    cpu_usage_ns: int | None = None
    cpu_user_ns: int | None = None
    cpu_system_ns: int | None = None
    pids_current: int | None = None
```

- [ ] **Step 4: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_cgroup.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/cgroup.py tests/test_cgroup.py
git commit -m "feat: add CgroupStats dataclass"
```

---

### Task 5: Cgroup Stat File Parsing

**Files:**
- Modify: `src/nsjail/cgroup.py`
- Modify: `tests/test_cgroup.py`

- [ ] **Step 1: Write tests for stat parsing**

Add to `tests/test_cgroup.py`:

```python
from nsjail.cgroup import parse_v1_stats, parse_v2_stats, CgroupStats


class TestParseV1Stats:
    def test_memory_stats(self, tmp_path):
        (tmp_path / "memory.max_usage_in_bytes").write_text("1048576\n")
        (tmp_path / "memory.usage_in_bytes").write_text("524288\n")
        stats = parse_v1_stats(memory_path=tmp_path)
        assert stats.memory_peak_bytes == 1048576
        assert stats.memory_current_bytes == 524288

    def test_cpu_stats(self, tmp_path):
        (tmp_path / "cpuacct.usage").write_text("5000000000\n")
        stats = parse_v1_stats(cpu_path=tmp_path)
        assert stats.cpu_usage_ns == 5000000000

    def test_pids_stats(self, tmp_path):
        (tmp_path / "pids.current").write_text("7\n")
        stats = parse_v1_stats(pids_path=tmp_path)
        assert stats.pids_current == 7

    def test_missing_files(self, tmp_path):
        stats = parse_v1_stats(memory_path=tmp_path)
        assert stats.memory_peak_bytes is None

    def test_all_none_when_no_paths(self):
        stats = parse_v1_stats()
        assert stats == CgroupStats()


class TestParseV2Stats:
    def test_memory_stats(self, tmp_path):
        (tmp_path / "memory.peak").write_text("2097152\n")
        (tmp_path / "memory.current").write_text("1048576\n")
        stats = parse_v2_stats(tmp_path)
        assert stats.memory_peak_bytes == 2097152
        assert stats.memory_current_bytes == 1048576

    def test_cpu_stats(self, tmp_path):
        (tmp_path / "cpu.stat").write_text(
            "usage_usec 5000000\n"
            "user_usec 3000000\n"
            "system_usec 2000000\n"
        )
        stats = parse_v2_stats(tmp_path)
        assert stats.cpu_usage_ns == 5000000000
        assert stats.cpu_user_ns == 3000000000
        assert stats.cpu_system_ns == 2000000000

    def test_pids_stats(self, tmp_path):
        (tmp_path / "pids.current").write_text("3\n")
        stats = parse_v2_stats(tmp_path)
        assert stats.pids_current == 3

    def test_missing_files(self, tmp_path):
        stats = parse_v2_stats(tmp_path)
        assert stats == CgroupStats()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_cgroup.py::TestParseV1Stats -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement stat parsing**

Add to `src/nsjail/cgroup.py`:

```python
from pathlib import Path


def _read_int(path: Path) -> int | None:
    """Read an integer from a cgroup stat file. Returns None if not readable."""
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, ValueError, PermissionError):
        return None


def parse_v1_stats(
    *,
    memory_path: Path | None = None,
    cpu_path: Path | None = None,
    pids_path: Path | None = None,
) -> CgroupStats:
    """Parse cgroup v1 stat files."""
    stats = CgroupStats()

    if memory_path:
        stats.memory_peak_bytes = _read_int(memory_path / "memory.max_usage_in_bytes")
        stats.memory_current_bytes = _read_int(memory_path / "memory.usage_in_bytes")

    if cpu_path:
        stats.cpu_usage_ns = _read_int(cpu_path / "cpuacct.usage")

    if pids_path:
        stats.pids_current = _read_int(pids_path / "pids.current")

    return stats


def parse_v2_stats(cgroup_path: Path) -> CgroupStats:
    """Parse cgroup v2 stat files from a unified cgroup directory."""
    stats = CgroupStats()

    stats.memory_peak_bytes = _read_int(cgroup_path / "memory.peak")
    stats.memory_current_bytes = _read_int(cgroup_path / "memory.current")
    stats.pids_current = _read_int(cgroup_path / "pids.current")

    # cpu.stat has key-value pairs like "usage_usec 5000000"
    cpu_stat_path = cgroup_path / "cpu.stat"
    try:
        text = cpu_stat_path.read_text()
        cpu_values: dict[str, int] = {}
        for line in text.strip().splitlines():
            parts = line.split()
            if len(parts) == 2:
                cpu_values[parts[0]] = int(parts[1])
        if "usage_usec" in cpu_values:
            stats.cpu_usage_ns = cpu_values["usage_usec"] * 1000
        if "user_usec" in cpu_values:
            stats.cpu_user_ns = cpu_values["user_usec"] * 1000
        if "system_usec" in cpu_values:
            stats.cpu_system_ns = cpu_values["system_usec"] * 1000
    except (FileNotFoundError, ValueError, PermissionError):
        pass

    return stats
```

- [ ] **Step 4: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_cgroup.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/cgroup.py tests/test_cgroup.py
git commit -m "feat: add cgroup v1/v2 stat file parsing"
```

---

### Task 6: CgroupMonitor Thread

**Files:**
- Modify: `src/nsjail/cgroup.py`
- Modify: `tests/test_cgroup.py`

- [ ] **Step 1: Write tests for CgroupMonitor**

Add to `tests/test_cgroup.py`:

```python
import time
import threading
from nsjail.cgroup import CgroupMonitor


class TestCgroupMonitor:
    def test_monitor_captures_stats(self, tmp_path):
        # Create fake cgroup files
        (tmp_path / "memory.peak").write_text("1048576\n")
        (tmp_path / "memory.current").write_text("524288\n")
        (tmp_path / "pids.current").write_text("3\n")

        monitor = CgroupMonitor(cgroup_path=tmp_path, poll_interval=0.05, use_v2=True)
        monitor.start()
        time.sleep(0.15)  # Let it poll a few times
        stats = monitor.stop()

        assert stats.memory_peak_bytes == 1048576
        assert stats.memory_current_bytes == 524288
        assert stats.pids_current == 3

    def test_monitor_survives_missing_files(self, tmp_path):
        # Empty dir — no stat files
        monitor = CgroupMonitor(cgroup_path=tmp_path, poll_interval=0.05, use_v2=True)
        monitor.start()
        time.sleep(0.1)
        stats = monitor.stop()
        assert stats == CgroupStats()

    def test_monitor_captures_changing_values(self, tmp_path):
        (tmp_path / "memory.current").write_text("100\n")
        (tmp_path / "memory.peak").write_text("100\n")

        monitor = CgroupMonitor(cgroup_path=tmp_path, poll_interval=0.05, use_v2=True)
        monitor.start()
        time.sleep(0.1)

        # Update values
        (tmp_path / "memory.current").write_text("200\n")
        (tmp_path / "memory.peak").write_text("200\n")
        time.sleep(0.1)

        stats = monitor.stop()
        assert stats.memory_peak_bytes == 200

    def test_monitor_stops_cleanly(self, tmp_path):
        (tmp_path / "memory.peak").write_text("1000\n")
        monitor = CgroupMonitor(cgroup_path=tmp_path, poll_interval=0.05, use_v2=True)
        monitor.start()
        time.sleep(0.1)
        stats = monitor.stop()
        # Should not hang or raise
        assert stats is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_cgroup.py::TestCgroupMonitor -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement CgroupMonitor**

Add to `src/nsjail/cgroup.py`:

```python
import threading


class CgroupMonitor:
    """Background thread that polls cgroup stat files.

    Captures the last-read resource usage stats before the cgroup
    is cleaned up by nsjail.
    """

    def __init__(
        self,
        cgroup_path: Path,
        poll_interval: float = 0.1,
        use_v2: bool = False,
        *,
        v1_memory_path: Path | None = None,
        v1_cpu_path: Path | None = None,
        v1_pids_path: Path | None = None,
    ) -> None:
        self._cgroup_path = cgroup_path
        self._poll_interval = poll_interval
        self._use_v2 = use_v2
        self._v1_memory_path = v1_memory_path
        self._v1_cpu_path = v1_cpu_path
        self._v1_pids_path = v1_pids_path
        self._stats = CgroupStats()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the monitoring thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> CgroupStats:
        """Stop monitoring and return the last captured stats."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        return self._stats

    def _poll_loop(self) -> None:
        """Poll stat files until stopped."""
        while not self._stop_event.is_set():
            try:
                if self._use_v2:
                    self._stats = parse_v2_stats(self._cgroup_path)
                else:
                    self._stats = parse_v1_stats(
                        memory_path=self._v1_memory_path,
                        cpu_path=self._v1_cpu_path,
                        pids_path=self._v1_pids_path,
                    )
            except Exception:
                pass  # Cgroup may have been deleted
            self._stop_event.wait(self._poll_interval)
```

- [ ] **Step 4: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_cgroup.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/cgroup.py tests/test_cgroup.py
git commit -m "feat: add CgroupMonitor background thread"
```

---

### Task 7: Runner Integration for Cgroup Stats

**Files:**
- Modify: `src/nsjail/runner.py`
- Modify: `tests/test_runner.py`

- [ ] **Step 1: Write tests**

Add to `tests/test_runner.py`:

```python
from nsjail.cgroup import CgroupStats


class TestRunnerCgroupStats:
    def test_nsjail_result_has_cgroup_stats_field(self):
        result = NsJailResult(
            returncode=0, stdout=b"", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
            cgroup_stats=CgroupStats(memory_peak_bytes=1024),
        )
        assert result.cgroup_stats.memory_peak_bytes == 1024

    def test_nsjail_result_cgroup_stats_default_none(self):
        result = NsJailResult(
            returncode=0, stdout=b"", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        assert result.cgroup_stats is None

    def test_runner_collect_cgroup_stats_flag(self):
        runner = Runner(
            nsjail_path="/usr/bin/nsjail",
            collect_cgroup_stats=True,
        )
        assert runner._collect_cgroup_stats is True

    def test_runner_default_no_cgroup_collection(self):
        runner = Runner(nsjail_path="/usr/bin/nsjail")
        assert runner._collect_cgroup_stats is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_runner.py::TestRunnerCgroupStats -v`
Expected: FAIL (NsJailResult doesn't have cgroup_stats field yet).

- [ ] **Step 3: Update NsJailResult and Runner**

In `src/nsjail/runner.py`:

Add import at top:
```python
from nsjail.cgroup import CgroupStats
```

Update `NsJailResult`:
```python
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
```

Update `Runner.__init__()` to accept `collect_cgroup_stats` and `cgroup_poll_interval`:
```python
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
```

Update `_make_result` to accept `cgroup_stats`:
```python
    def _make_result(
        self, returncode: int, stdout: bytes, stderr: bytes,
        config_path: Path | None, nsjail_args: list[str],
        cgroup_stats: CgroupStats | None = None,
    ) -> NsJailResult:
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
```

Update `run()` to start/stop the cgroup monitor:
```python
    def run(self, ...):
        nsjail_args, config_path, cfg = self._prepare_run(
            overrides, override_fields, extra_args
        )

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
        finally:
            if cgroup_monitor:
                cgroup_stats = cgroup_monitor.stop()
            if config_path and not self._keep_config:
                config_path.unlink(missing_ok=True)
                config_path = None

        return self._make_result(
            proc.returncode,
            stdout if self._capture_output else b"",
            stderr if self._capture_output else b"",
            config_path,
            nsjail_args,
            cgroup_stats=cgroup_stats,
        )
```

Add `_start_cgroup_monitor` helper:
```python
    def _start_cgroup_monitor(self, cfg: NsJailConfig, pid: int) -> CgroupMonitor:
        """Start a cgroup monitor for the given nsjail process."""
        from nsjail.cgroup import CgroupMonitor

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
                cgroup_path=Path("/dev/null"),  # unused for v1
                poll_interval=self._cgroup_poll_interval,
                use_v2=False,
                v1_memory_path=Path(cfg.cgroup_mem_mount) / cfg.cgroup_mem_parent / f"NSJAIL.{pid}" if cfg.cgroup_mem_max else None,
                v1_cpu_path=Path(cfg.cgroup_cpu_mount) / cfg.cgroup_cpu_parent / f"NSJAIL.{pid}" if cfg.cgroup_cpu_ms_per_sec else None,
                v1_pids_path=Path(cfg.cgroup_pids_mount) / cfg.cgroup_pids_parent / f"NSJAIL.{pid}" if cfg.cgroup_pids_max else None,
            )

        monitor.start()
        return monitor
```

Note: The `run()` method changes from `subprocess.run()` to `subprocess.Popen()` so we can get the PID before the process exits. This is necessary for cgroup path construction.

Also update `fork()` to pass through the new parameters:
```python
    def fork(self, ...):
        ...
        return Runner(
            nsjail_path=nsjail_path or self._nsjail_path,
            base_config=new_base,
            render_mode=self._render_mode,
            capture_output=self._capture_output,
            keep_config=self._keep_config,
            collect_cgroup_stats=self._collect_cgroup_stats,
            cgroup_poll_interval=self._cgroup_poll_interval,
        )
```

- [ ] **Step 4: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/ -v`
Expected: All tests pass (including existing runner tests — the NsJailResult change is backward compatible since `cgroup_stats` has a default).

- [ ] **Step 5: Commit**

```bash
git add src/nsjail/runner.py tests/test_runner.py
git commit -m "feat: add cgroup stats collection to Runner"
```

---

### Task 8: Update Public API and Final Integration

**Files:**
- Modify: `src/nsjail/__init__.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Update __init__.py**

Add seccomp and cgroup exports to `src/nsjail/__init__.py`:

```python
"""nsjail-python: Python wrapper for Google's nsjail sandboxing tool."""

from nsjail.config import Exe, IdMap, MountPt, NsJailConfig
from nsjail.enums import LogLevel, Mode, RLimitType
from nsjail.builder import Jail
from nsjail.cgroup import CgroupStats
from nsjail.presets import sandbox
from nsjail.runner import NsJailResult, Runner
from nsjail.seccomp import SeccompPolicy, MINIMAL, DEFAULT_LOG, READONLY

__all__ = [
    "CgroupStats",
    "DEFAULT_LOG",
    "Exe",
    "IdMap",
    "Jail",
    "LogLevel",
    "MINIMAL",
    "Mode",
    "MountPt",
    "NsJailConfig",
    "NsJailResult",
    "READONLY",
    "RLimitType",
    "Runner",
    "SeccompPolicy",
    "sandbox",
]
```

- [ ] **Step 2: Add integration tests**

Add to `tests/test_integration.py`:

```python
from nsjail.seccomp import SeccompPolicy, MINIMAL, READONLY
from nsjail.cgroup import CgroupStats


class TestSeccompIntegration:
    def test_builder_with_seccomp_to_textproto(self):
        cfg = (
            Jail()
            .sh("echo hi")
            .seccomp(MINIMAL)
            .build()
        )
        text = to_textproto(cfg)
        assert "seccomp_string:" in text
        assert "read" in text

    def test_custom_policy_to_textproto(self):
        policy = (
            SeccompPolicy("custom")
            .allow("read", "write")
            .deny("execve")
            .default_kill()
        )
        cfg = Jail().sh("echo hi").seccomp(policy).build()
        text = to_textproto(cfg)
        assert "seccomp_string:" in text


class TestCgroupStatsIntegration:
    def test_result_with_cgroup_stats(self):
        stats = CgroupStats(
            memory_peak_bytes=512 * 1024 * 1024,
            cpu_usage_ns=2_500_000_000,
            pids_current=12,
        )
        result = NsJailResult(
            returncode=0, stdout=b"", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
            cgroup_stats=stats,
        )
        assert result.cgroup_stats.memory_peak_bytes == 512 * 1024 * 1024
        assert result.cgroup_stats.cpu_usage_ns == 2_500_000_000
```

- [ ] **Step 3: Run full test suite**

Run: `/home/teague/.local/share/venv/bin/pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 4: Commit and push**

```bash
git add src/nsjail/__init__.py tests/test_integration.py
git commit -m "feat: update public API with seccomp + cgroup exports, add integration tests"
git push
```
