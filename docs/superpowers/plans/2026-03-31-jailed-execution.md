# Jailed Python Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `jail_call()`, `@jailed` decorator, and `JailContext` manager for calling Python functions inside nsjail sandboxes with automatic serialization.

**Architecture:** A `_worker.py` module runs inside the sandbox, deserializes the callable, executes it, and serializes the result. The parent-side `call.py` handles config building, serialization, nsjail execution, and result extraction. Three API wrappers (function, decorator, context manager) all delegate to the same engine.

**Tech Stack:** Python 3.12+, pickle/cloudpickle (optional), subprocess, tmpfs

**Spec:** `docs/superpowers/specs/2026-03-31-jailed-execution-design.md`

**Security note:** Pickle is used as the serialization transport between parent and child processes within the same trust domain (similar to Python's multiprocessing module). The sandbox is the security boundary; pickle is just the internal transport.

---

### Task 1: JailedExecutionError Exception

**Files:**
- Modify: `src/nsjail/exceptions.py`
- Modify: `tests/test_exceptions.py`

- [ ] **Step 1: Write tests**

Add to `tests/test_exceptions.py`:

```python
from nsjail.exceptions import JailedExecutionError


def test_jailed_execution_error_is_nsjail_error():
    assert issubclass(JailedExecutionError, NsjailError)


def test_jailed_execution_error_message():
    err = JailedExecutionError("function failed")
    assert "function failed" in str(err)


def test_jailed_execution_error_with_traceback():
    err = JailedExecutionError("failed", original_traceback="Traceback...")
    assert err.original_traceback == "Traceback..."
```

- [ ] **Step 2: Implement**

Add to `src/nsjail/exceptions.py`:

```python
class JailedExecutionError(NsjailError):
    """Raised when a jailed function execution fails."""

    def __init__(self, message: str, original_traceback: str | None = None) -> None:
        self.original_traceback = original_traceback
        super().__init__(message)
```

- [ ] **Step 3: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_exceptions.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/nsjail/exceptions.py tests/test_exceptions.py
git commit -m "feat: add JailedExecutionError exception"
```

---

### Task 2: Worker Module (_worker.py)

**Files:**
- Create: `src/nsjail/_worker.py`
- Create: `tests/test_worker.py`

- [ ] **Step 1: Write tests**

Create `tests/test_worker.py`. Tests exercise the worker logic directly (no nsjail needed) by writing pickle input files and calling `run_worker()`:

- `test_simple_function`: serialize `add(1,2)`, verify output is `3`
- `test_function_with_kwargs`: serialize with kwargs, verify correct result
- `test_function_returning_none`: verify None result works
- `test_function_raises`: serialize a function that raises ValueError, verify `(True, ValueError)` output
- `test_function_raises_custom_exception`: verify custom exception types survive serialization

Each test:
1. Writes `(func, args, kwargs)` to `tmp_path/input.pkl`
2. Calls `run_worker(tmp_path)`
3. Reads `(is_error, result)` from `tmp_path/output.pkl`
4. Asserts correctness

- [ ] **Step 2: Implement _worker.py**

Create `src/nsjail/_worker.py` with:
- `_get_serializer()`: tries cloudpickle, falls back to pickle
- `run_worker(io_dir: Path)`: reads input.pkl, calls function, writes output.pkl
- `main()`: CLI entry point for `python -m nsjail._worker <io_dir>`

- [ ] **Step 3: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_worker.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/nsjail/_worker.py tests/test_worker.py
git commit -m "feat: add worker module for jailed Python execution"
```

---

### Task 3: Core Execution Engine (jail_call)

**Files:**
- Create: `src/nsjail/call.py`
- Create: `tests/test_call.py`

- [ ] **Step 1: Write tests**

Create `tests/test_call.py` with tests for:
- `_serialize_input()`: roundtrip serialize/deserialize
- `_deserialize_output()`: success case, error re-raise, missing file
- `_build_jail_config()`: produces NsJailConfig with correct timeout, memory, network, mounts, worker command

All tests use mocks or tmp_path — no real nsjail.

- [ ] **Step 2: Implement call.py**

Create `src/nsjail/call.py` with:
- `_get_serializer()`: cloudpickle > pickle
- `_serialize_input(io_dir, func, args, kwargs)`: writes input.pkl
- `_deserialize_output(output_path)`: reads output.pkl, re-raises exceptions
- `_build_jail_config(io_dir, timeout_sec, ...)`: builds NsJailConfig with system_libs, dev_minimal, python_env, proc_mount, writable I/O dir
- `jail_call(func, args, kwargs, *, ...)`: full lifecycle — serialize, build config, run nsjail, deserialize result
- `_jail_call_pipe(...)`: alternative pipe transport

- [ ] **Step 3: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_call.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/nsjail/call.py tests/test_call.py
git commit -m "feat: add jail_call execution engine"
```

---

### Task 4: @jailed Decorator and JailContext

**Files:**
- Modify: `src/nsjail/call.py`
- Modify: `tests/test_call.py`

- [ ] **Step 1: Write tests**

Add to `tests/test_call.py`:
- `TestJailedDecorator`: wraps function, preserves name, calls jail_call with correct args/kwargs
- `TestJailContext`: creates/cleans up I/O dir, call() delegates to jail_call, multiple calls share I/O dir

All tests mock `jail_call` — no real nsjail.

- [ ] **Step 2: Implement**

Add to `src/nsjail/call.py`:
- `jailed(**jail_kwargs)`: decorator factory returning wrapper that calls `jail_call`
- `JailContext(**jail_kwargs)`: context manager with `__enter__`/`__exit__` managing tmpdir, `.call()` method

- [ ] **Step 3: Run tests**

Run: `/home/teague/.local/share/venv/bin/pytest tests/test_call.py -v`
Then: `/home/teague/.local/share/venv/bin/pytest tests/ -q`

- [ ] **Step 4: Commit**

```bash
git add src/nsjail/call.py tests/test_call.py
git commit -m "feat: add @jailed decorator and JailContext manager"
```

---

### Task 5: Public API Exports + Docs + Push

**Files:**
- Modify: `src/nsjail/__init__.py`
- Modify: `pyproject.toml`
- Modify: `docs/quickstart.rst`
- Modify: `docs/api.rst`

- [ ] **Step 1: Update __init__.py**

Add imports and exports for `jail_call`, `jailed`, `JailContext`, `JailedExecutionError`.

- [ ] **Step 2: Add [call] extra to pyproject.toml**

```toml
call = ["cloudpickle"]
```

- [ ] **Step 3: Update docs**

Add "Jailed Execution" section to quickstart.rst showing all three APIs.
Add automodule entries to api.rst.

- [ ] **Step 4: Run full suite**

Run: `/home/teague/.local/share/venv/bin/pytest tests/ -q`

- [ ] **Step 5: Commit and push**

```bash
git add src/nsjail/__init__.py pyproject.toml docs/
git commit -m "feat: export jailed execution APIs, add docs and [call] extra"
git push
```
