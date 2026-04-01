# Jailed Python Execution Design Spec

**Date:** 2026-03-31
**Status:** Draft
**Scope:** Call Python functions inside nsjail sandboxes with automatic serialization

## Context

nsjail-python can generate configs, serialize them, and run nsjail subprocesses. But calling a Python function inside a sandbox requires users to manually handle serialization, mount setup, and result extraction. This feature provides a high-level API similar to `multiprocessing` — serialize a callable and its arguments, run it inside nsjail, and get the result back.

**Security note on pickle:** This feature uses pickle (or cloudpickle) for serialization, similar to how Python's `multiprocessing` module works. The pickle data flows only between the parent process and its own sandboxed child — it never crosses trust boundaries. The sandbox is the security boundary; pickle is just the transport within a single trust domain.

## Three APIs

All three share the same execution engine. They differ only in ergonomics.

### 1. `jail_call()` — Explicit apply wrapper

The lowest-level API. Call any callable in a sandbox:

```python
from nsjail.call import jail_call

result = jail_call(
    my_function,
    args=(data,),
    kwargs={"verbose": True},
    memory_mb=512,
    timeout_sec=30,
)
```

Signature:

```python
def jail_call(
    func: Callable,
    args: tuple = (),
    kwargs: dict | None = None,
    *,
    # Sandbox config
    memory_mb: int | None = None,
    timeout_sec: int = 600,
    cpu_ms_per_sec: int | None = None,
    pids_max: int | None = None,
    network: bool = False,
    writable_dirs: list[str] | None = None,
    extra_mounts: list[MountPt] | None = None,
    # Execution config
    nsjail_path: str | None = None,
    transport: Literal["tmpfs", "pipe"] = "tmpfs",
    python_path: str | None = None,
) -> Any:
```

### 2. `@jailed` — Decorator

Wraps a function so every invocation runs in a sandbox:

```python
from nsjail.call import jailed

@jailed(memory_mb=512, timeout_sec=30)
def untrusted_compute(data):
    return expensive_transform(data)

result = untrusted_compute(my_data)
```

The decorator accepts the same keyword arguments as `jail_call` (minus `func`, `args`, `kwargs`). It returns a wrapper that calls `jail_call` on each invocation.

```python
def jailed(**jail_kwargs) -> Callable:
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return jail_call(func, args=args, kwargs=kwargs, **jail_kwargs)
        return wrapper
    return decorator
```

### 3. `JailContext` — Context manager

Manages a reusable sandbox configuration for multiple calls:

```python
from nsjail.call import JailContext

with JailContext(memory_mb=512, timeout_sec=30) as jail:
    result1 = jail.call(function_a, data)
    result2 = jail.call(function_b, result1)
```

Each `jail.call()` is a separate sandboxed process execution. The context manager:
- Holds a shared sandbox configuration
- Creates/cleans up a shared tmpfs directory for I/O
- Provides a `.call(func, *args, **kwargs)` method

```python
class JailContext:
    def __init__(self, **jail_kwargs):
        self._jail_kwargs = jail_kwargs
        self._io_dir: Path | None = None

    def __enter__(self) -> JailContext:
        self._io_dir = Path(tempfile.mkdtemp(prefix="nsjail_ctx_"))
        return self

    def __exit__(self, *exc):
        if self._io_dir:
            shutil.rmtree(self._io_dir, ignore_errors=True)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        return jail_call(func, args=args, kwargs=kwargs,
                         _io_dir=self._io_dir, **self._jail_kwargs)
```

## Execution Engine

### Data flow

```
Parent                              Sandboxed child
──────                              ───────────────
1. Serialize (func, args, kwargs)
2. Write input.pkl to I/O dir
3. Build NsJailConfig:
   - python_env() mounts
   - system_libs() mounts
   - dev_minimal() mounts
   - tmpfs or bind-mount for I/O dir
   - user-specified mounts/writable dirs
4. Run nsjail with python -m nsjail._worker
                                    5. Import _worker module
                                    6. Read input.pkl
                                    7. Deserialize func + args
                                    8. try: result = func(*args, **kwargs)
                                    9. except: result = (True, exception)
                                    10. Serialize result
                                    11. Write output.pkl
                                    12. Exit 0 (or 1 on error)
13. Read output.pkl
14. Deserialize result
15. Return value or re-raise exception
```

### Child-side worker module: `src/nsjail/_worker.py`

A small module that nsjail runs via `python -m nsjail._worker`. It:

1. Reads the input file path from argv or a known location
2. Deserializes the callable and arguments
3. Calls the function in a try/except
4. Serializes the result (or the exception)
5. Writes the output file
6. Exits

```python
# nsjail/_worker.py (simplified)
import sys
from pathlib import Path

def main():
    io_dir = Path(sys.argv[1])
    input_path = io_dir / "input.pkl"
    output_path = io_dir / "output.pkl"

    try:
        import cloudpickle as pkl
    except ImportError:
        import pickle as pkl

    with open(input_path, "rb") as f:
        func, args, kwargs = pkl.load(f)

    try:
        result = func(*args, **kwargs)
        payload = (False, result)  # (is_error, value)
    except BaseException as e:
        payload = (True, e)

    with open(output_path, "wb") as f:
        pkl.dump(payload, f)

if __name__ == "__main__":
    main()
```

### Serialization

**Strategy:** Try `cloudpickle` first (handles lambdas, closures, local functions). If not installed, fall back to standard `pickle`. Both parent and child independently detect which is available.

**What can be serialized:**
- With cloudpickle: any callable (functions, lambdas, closures, bound methods, classes)
- With pickle: module-level functions and picklable objects only

**Dependency:** cloudpickle is an optional extra:
```toml
[project.optional-dependencies]
call = ["cloudpickle"]
```

### Transport modes

**Tmpfs (default):**
- Parent creates a temp directory on host
- Writes `input.pkl` to it
- nsjail bind-mounts it writable inside the sandbox
- Child reads input, writes output
- Parent reads `output.pkl` after child exits
- Parent cleans up the temp directory

**Pipe:**
- Serialize input, write to nsjail's stdin
- Child reads stdin, executes, writes result to stdout
- Child's own print output goes to stderr
- Parent reads stdout as the result
- No tmpfs needed, but child can't use stdout for logging

### NsJailConfig construction

`jail_call` builds a config automatically:

```python
cfg = (
    Jail()
    .command(python_path or sys.executable, "-m", "nsjail._worker", io_dir_inside)
    .timeout(timeout_sec)
    .readonly_root()
    .mounts(system_libs())
    .mounts(dev_minimal())
    .mounts(python_env())
    .mounts(proc_mount())
    .writable(io_dir_inside)
    .build()
)

if memory_mb:
    apply_cgroup_limits(cfg, memory_mb=memory_mb)
if not network:
    cfg.clone_newnet = True
```

The user's `extra_mounts` and `writable_dirs` are appended on top.

### Error propagation

The child serializes exceptions in the output payload as `(True, exception)`. The parent:

1. Reads the output file
2. If `is_error` is True, re-raises the exception
3. If the exception can't be deserialized (e.g., custom exception class not importable), wraps in `JailedExecutionError` with the original traceback as a string

```python
class JailedExecutionError(NsjailError):
    """Raised when a jailed function execution fails."""

    def __init__(self, message: str, original_traceback: str | None = None):
        self.original_traceback = original_traceback
        super().__init__(message)
```

Failure modes:
- **Function raises:** exception re-raised in parent
- **nsjail kills process (timeout/OOM):** `JailedExecutionError` with nsjail exit info
- **Serialization failure:** `JailedExecutionError` explaining the error
- **nsjail not found:** `NsjailNotFound` (existing exception)

### Module structure

```
src/nsjail/
    call.py          # jail_call, jailed decorator, JailContext
    _worker.py       # Child-side execution (run inside sandbox)
    exceptions.py    # Add JailedExecutionError
```

## Testing

- **Unit tests (no nsjail needed):** Test serialization/deserialization, config generation, error wrapping, decorator behavior with mocked jail_call
- **Integration tests (nsjail needed):** Actually run functions in nsjail, verify return values, test exception propagation, test timeout/OOM behavior, test with cloudpickle and without

## Scope Boundaries

**In scope:**
- `jail_call()` explicit wrapper
- `@jailed` decorator
- `JailContext` context manager
- `_worker.py` child-side module
- `JailedExecutionError` exception
- Tmpfs and pipe transport modes
- cloudpickle optional, standard pickle default
- Exception re-raising
- Auto-config with python_env/system_libs/dev_minimal mounts

**Out of scope:**
- Shared memory between calls (each call is independent)
- Persistent sandbox (process pool — would be a future feature)
- Streaming results (only batch call-and-return)
- GPU/device passthrough
- Custom Python environments (virtualenvs different from current)
