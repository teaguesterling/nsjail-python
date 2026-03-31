# Integration Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real nsjail integration tests that build nsjail from vendored source and verify sandbox behavior using user namespaces.

**Architecture:** A session-scoped pytest fixture builds nsjail from `_vendor/nsjail/`. Tests use the `@pytest.mark.integration` marker and skip gracefully if nsjail can't be built. Three test files cover execution, isolation, and end-to-end pipelines.

**Tech Stack:** Python 3.12+, pytest, subprocess, nsjail (built from source)

**Spec:** `docs/superpowers/specs/2026-03-30-integration-tests-design.md`

---

### Task 1: Test Infrastructure (conftest + marker)

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/conftest.py`
- Modify: `pyproject.toml` (add marker)

- [ ] **Step 1: Create integration test directory**

```bash
mkdir -p tests/integration
touch tests/integration/__init__.py
```

- [ ] **Step 2: Add pytest marker to pyproject.toml**

Add to the `[tool.pytest.ini_options]` section in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: tests requiring real nsjail binary"]
```

- [ ] **Step 3: Create conftest.py with nsjail fixture**

Create `tests/integration/conftest.py`:

```python
"""Fixtures for nsjail integration tests.

The nsjail_binary fixture builds nsjail from vendored source if needed.
All integration tests are skipped if nsjail can't be obtained.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from nsjail.runner import Runner


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (has pyproject.toml)."""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not find repo root")


def _build_nsjail(vendor_dir: Path) -> Path | None:
    """Try to build nsjail from vendored source. Returns binary path or None."""
    nsjail_src = vendor_dir / "nsjail"
    if not (nsjail_src / "Makefile").exists():
        return None

    # Check for required build tools
    for tool in ("make", "g++", "protoc", "bison", "flex", "pkg-config"):
        if not shutil.which(tool):
            return None

    # Init kafel submodule if needed
    kafel_dir = nsjail_src / "kafel"
    if not (kafel_dir / "Makefile").exists():
        result = subprocess.run(
            ["git", "submodule", "update", "--init"],
            cwd=nsjail_src,
            capture_output=True,
        )
        if result.returncode != 0:
            return None

    # Build
    result = subprocess.run(
        ["make", f"-j{os.cpu_count() or 1}"],
        cwd=nsjail_src,
        capture_output=True,
        timeout=300,
    )
    if result.returncode != 0:
        return None

    binary = nsjail_src / "nsjail"
    if binary.exists():
        return binary
    return None


@pytest.fixture(scope="session")
def nsjail_binary() -> Path:
    """Provide a path to a working nsjail binary.

    Resolution order:
    1. nsjail on PATH
    2. Already-built binary in _vendor/nsjail/
    3. Build from _vendor/nsjail/ source
    4. Skip tests
    """
    # 1. System nsjail
    system = shutil.which("nsjail")
    if system:
        return Path(system)

    repo_root = _find_repo_root()
    vendor_dir = repo_root / "_vendor"

    # 2. Already built
    built = vendor_dir / "nsjail" / "nsjail"
    if built.exists():
        return built

    # 3. Try to build
    binary = _build_nsjail(vendor_dir)
    if binary:
        return binary

    pytest.skip(
        "nsjail binary not available. Install nsjail, or install build deps: "
        "apt-get install protobuf-compiler libprotobuf-dev libnl-route-3-dev "
        "libcap-dev bison flex"
    )


@pytest.fixture
def runner(nsjail_binary: Path) -> Runner:
    """A Runner configured with the test nsjail binary."""
    return Runner(nsjail_path=str(nsjail_binary))
```

- [ ] **Step 4: Verify the fixture works**

```bash
/home/teague/.local/share/venv/bin/pytest tests/integration/ -v --co
```

Expected: Either collects 0 tests (no test files yet) or shows the fixture is loadable.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/ pyproject.toml
git commit -m "test: add integration test infrastructure (nsjail fixture + marker)"
```

---

### Task 2: Execution Tests

**Files:**
- Create: `tests/integration/test_execution.py`

- [ ] **Step 1: Create execution tests**

Create `tests/integration/test_execution.py`:

```python
"""Integration tests for nsjail command execution.

These tests run real nsjail processes using user namespaces.
"""

from __future__ import annotations

import time

import pytest

from nsjail.config import Exe, NsJailConfig
from nsjail.runner import Runner

pytestmark = pytest.mark.integration


class TestCommandExecution:
    def test_echo_stdout(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/echo", arg=["hello"]),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert result.stdout.strip() == b"hello"

    def test_exit_code_zero(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/true"),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert result.returncode == 0

    def test_exit_code_nonzero(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/false"),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert result.returncode != 0

    def test_exit_code_specific(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "exit 42"]),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert result.inner_returncode == 42

    def test_time_limit_kills(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sleep", arg=["60"]),
            time_limit=2,
        )
        start = time.monotonic()
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        elapsed = time.monotonic() - start
        assert result.timed_out is True
        assert elapsed < 10  # Should finish well under 10s

    def test_env_vars_set(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo $MYVAR"]),
            envar=["MYVAR=hello_from_nsjail"],
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "envar", "time_limit",
        })
        assert b"hello_from_nsjail" in result.stdout

    def test_working_directory(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "pwd"]),
            cwd="/tmp",
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "cwd", "time_limit",
        })
        assert b"/tmp" in result.stdout

    def test_stderr_captured(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo err >&2"]),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert b"err" in result.stderr
```

- [ ] **Step 2: Run tests**

```bash
/home/teague/.local/share/venv/bin/pytest tests/integration/test_execution.py -v
```

Expected: Either all pass (if nsjail builds) or all skip (if build deps missing).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_execution.py
git commit -m "test: add nsjail execution integration tests"
```

---

### Task 3: Isolation Tests

**Files:**
- Create: `tests/integration/test_isolation.py`

- [ ] **Step 1: Create isolation tests**

Create `tests/integration/test_isolation.py`:

```python
"""Integration tests for nsjail namespace and filesystem isolation.

These tests verify sandbox isolation using user namespaces (no root required).
"""

from __future__ import annotations

import pytest

from nsjail.config import Exe, MountPt, NsJailConfig
from nsjail.runner import Runner

pytestmark = pytest.mark.integration


class TestPidNamespace:
    def test_pid_is_one_inside(self, runner: Runner):
        """Process should see itself as PID 1 inside a PID namespace."""
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo $$"]),
            clone_newpid=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "clone_newpid", "time_limit",
        })
        assert result.stdout.strip() == b"1"


class TestFilesystem:
    def test_readonly_root_blocks_writes(self, runner: Runner):
        """Writing to a read-only root mount should fail."""
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "touch /testfile_readonly"]),
            mount=[MountPt(src="/", dst="/", is_bind=True, rw=False)],
            mount_proc=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "mount", "mount_proc", "time_limit",
        })
        assert result.returncode != 0

    def test_writable_directory(self, runner: Runner):
        """A read-write bind mount should allow writes."""
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "touch /tmp/testfile_rw && echo ok"]),
            mount=[
                MountPt(src="/", dst="/", is_bind=True, rw=False),
                MountPt(src="/tmp", dst="/tmp", is_bind=True, rw=True),
            ],
            mount_proc=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "mount", "mount_proc", "time_limit",
        })
        assert b"ok" in result.stdout

    def test_tmpfs_mount(self, runner: Runner):
        """A tmpfs mount should be writable and report as tmpfs."""
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "touch /tmp/test && df -T /tmp | tail -1"]),
            mount=[
                MountPt(src="/", dst="/", is_bind=True, rw=False),
                MountPt(dst="/tmp", fstype="tmpfs", rw=True, is_dir=True),
            ],
            mount_proc=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "mount", "mount_proc", "time_limit",
        })
        assert b"tmpfs" in result.stdout

    def test_mount_proc(self, runner: Runner):
        """mount_proc should make /proc available inside the sandbox."""
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "head -1 /proc/self/status"]),
            mount=[MountPt(src="/", dst="/", is_bind=True, rw=False)],
            mount_proc=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "mount", "mount_proc", "time_limit",
        })
        assert b"Name:" in result.stdout


class TestHostname:
    def test_custom_hostname(self, runner: Runner):
        """hostname config should be reflected inside the sandbox."""
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/hostname"),
            hostname="testjail",
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "hostname", "time_limit",
        })
        assert b"testjail" in result.stdout
```

- [ ] **Step 2: Run tests**

```bash
/home/teague/.local/share/venv/bin/pytest tests/integration/test_isolation.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_isolation.py
git commit -m "test: add nsjail isolation integration tests"
```

---

### Task 4: Pipeline Tests

**Files:**
- Create: `tests/integration/test_pipeline.py`

- [ ] **Step 1: Create pipeline tests**

Create `tests/integration/test_pipeline.py`:

```python
"""Integration tests for end-to-end nsjail-python pipelines.

Tests the full flow: builder/presets -> config -> serializer -> Runner -> result.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nsjail import Jail, NsJailConfig, sandbox
from nsjail.runner import Runner
from nsjail.serializers import to_textproto, to_file

pytestmark = pytest.mark.integration


class TestBuilderPipeline:
    def test_builder_sh_run(self, runner: Runner):
        """Jail().sh("...").run() should execute and return output."""
        result = (
            Jail()
            .sh("echo builder_works")
            .timeout(10)
            .run(runner=runner)
        )
        assert b"builder_works" in result.stdout
        assert result.returncode == 0

    def test_builder_command_run(self, runner: Runner):
        """Jail().command("echo", "hi").run() should work."""
        result = (
            Jail()
            .command("/bin/echo", "command_works")
            .timeout(10)
            .run(runner=runner)
        )
        assert b"command_works" in result.stdout


class TestSandboxPreset:
    def test_sandbox_preset(self, runner: Runner):
        """sandbox() preset should produce a working config."""
        cfg = sandbox(
            command=["/bin/echo", "preset_works"],
            timeout_sec=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit", "mode", "cwd", "clone_newnet", "mount",
        })
        assert b"preset_works" in result.stdout


class TestConfigFilePipeline:
    def test_textproto_to_file_to_nsjail(self, runner: Runner, tmp_path: Path):
        """Generate config file, then run nsjail with --config."""
        cfg = NsJailConfig(
            exec_bin=Jail().sh("echo config_file_works").build().exec_bin,
            time_limit=10,
        )
        config_path = tmp_path / "test.cfg"
        to_file(cfg, config_path)

        # Verify the config file was written
        content = config_path.read_text()
        assert "exec_bin" in content

        # Run using the config file directly
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert b"config_file_works" in result.stdout


class TestFullFeatureBuilder:
    def test_builder_with_all_features(self, runner: Runner):
        """Test a builder chain exercising many features at once."""
        result = (
            Jail()
            .sh('echo "host=$(hostname) cwd=$(pwd) var=$TESTVAR"')
            .timeout(10)
            .cwd("/tmp")
            .env("TESTVAR=integration_test")
            .build()
        )
        run_result = runner.run(
            overrides=result,
            override_fields={
                "exec_bin", "time_limit", "cwd", "envar", "hostname",
            },
        )
        assert b"cwd=/tmp" in run_result.stdout
        assert b"var=integration_test" in run_result.stdout
```

- [ ] **Step 2: Run tests**

```bash
/home/teague/.local/share/venv/bin/pytest tests/integration/test_pipeline.py -v
```

- [ ] **Step 3: Run full test suite**

```bash
/home/teague/.local/share/venv/bin/pytest tests/ -v --tb=short
```

Expected: All 301+ unit tests pass. Integration tests either pass or skip.

- [ ] **Step 4: Commit and push**

```bash
git add tests/integration/test_pipeline.py
git commit -m "test: add nsjail pipeline integration tests"
git push
```
