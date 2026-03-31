# Integration Tests Design Spec

**Date:** 2026-03-30
**Status:** Draft
**Scope:** Real nsjail integration tests running in user namespaces

## Context

nsjail-python has 301 unit tests but none exercise real nsjail execution. Integration tests verify that generated configs actually produce correct sandbox behavior. These tests use user namespaces (no root required) and build nsjail from the vendored source as a test fixture.

## Test Fixture: nsjail Binary

A session-scoped pytest fixture provides a path to a working nsjail binary. Resolution order:

1. `nsjail` on PATH
2. `_vendor/nsjail/nsjail` (already built)
3. Build from `_vendor/nsjail/` via `make -j$(nproc)`
4. Skip all integration tests if unavailable

The fixture caches the built binary across the test session. Build output is suppressed unless it fails.

## Pytest Marker

All integration tests use `@pytest.mark.integration`. Configure in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = ["integration: tests requiring real nsjail binary"]
```

CI can include/exclude: `pytest -m integration` or `pytest -m "not integration"`.

## Test Structure

```
tests/
    integration/
        __init__.py
        conftest.py          # nsjail_binary fixture + skip logic
        test_execution.py    # Command execution, exit codes, timeouts
        test_isolation.py    # PID namespace, mounts, filesystem
        test_pipeline.py     # End-to-end builder/runner pipelines
```

## Test Cases

### test_execution.py — Command Execution

| Test | Config | Assertion |
|---|---|---|
| `test_echo_stdout` | `exec_bin: /bin/echo hello` | stdout == b"hello\n" |
| `test_exit_code_zero` | `exec_bin: /bin/true` | returncode == 0 |
| `test_exit_code_nonzero` | `exec_bin: /bin/false` | returncode != 0 |
| `test_exit_code_specific` | `sh -c "exit 42"` | inner_returncode == 42 |
| `test_time_limit_kills` | `sh -c "sleep 60"`, time_limit=2 | timed_out == True, completes in < 5s |
| `test_env_vars_set` | `envar=["MYVAR=hello"]`, `sh -c "echo $MYVAR"` | stdout contains "hello" |
| `test_working_directory` | `cwd="/tmp"`, `sh -c "pwd"` | stdout contains "/tmp" |
| `test_stderr_captured` | `sh -c "echo err >&2"` | stderr == b"err\n" |

### test_isolation.py — Namespace & Filesystem Isolation

| Test | Config | Assertion |
|---|---|---|
| `test_pid_namespace` | `clone_newpid=True`, `sh -c "echo $$"` | stdout is "1\n" (PID 1 inside) |
| `test_readonly_root` | ro bind mount `/`, `sh -c "touch /testfile"` | exit code != 0 |
| `test_writable_dir` | ro root + rw bind `/tmp`, `sh -c "touch /tmp/testfile && echo ok"` | stdout contains "ok" |
| `test_tmpfs_mount` | tmpfs on `/tmp`, `sh -c "df -T /tmp"` | output contains "tmpfs" |
| `test_hostname` | `hostname="testjail"`, `hostname` | stdout contains "testjail" |
| `test_mount_proc` | `mount_proc=True`, `sh -c "cat /proc/self/status \| head -1"` | output contains "Name:" |

### test_pipeline.py — End-to-End Pipelines

| Test | What it tests | Assertion |
|---|---|---|
| `test_builder_to_run` | `Jail().sh("echo hi").run(runner=runner)` | result.stdout contains "hi" |
| `test_sandbox_preset` | `sandbox(command=["echo", "hello"])` via Runner | stdout == b"hello\n" |
| `test_textproto_to_file_to_nsjail` | Generate config, write file, run nsjail --config | stdout matches expected |
| `test_builder_with_all_features` | Full chain: timeout, env, cwd, readonly, writable, hostname | All assertions pass |

## Runner Configuration for Tests

All integration tests use a Runner with `nsjail_path` set to the fixture binary and `render_mode="textproto"`:

```python
@pytest.fixture
def runner(nsjail_binary):
    return Runner(nsjail_path=str(nsjail_binary))
```

## CI Configuration

Add integration tests to the CI workflow. They run on Linux only and skip gracefully if build tools aren't available:

```yaml
- run: pytest tests/ -v -m "not integration"  # fast unit tests
- run: pytest tests/integration/ -v || true     # integration (best-effort)
```

## Scope Boundaries

**In scope:**
- nsjail binary build fixture
- User-namespace-tier tests (no root)
- Execution, isolation, and pipeline tests
- pytest marker for selective running

**Out of scope:**
- Cgroup enforcement tests (need root)
- Network namespace tests (need root for full isolation)
- Seccomp enforcement tests (need root)
- Performance/stress tests
