# Mount Helpers Design Spec

**Date:** 2026-03-31
**Status:** Draft
**Scope:** High-level mount helpers for common sandbox filesystem patterns

## Context

nsjail-python's `MountPt` dataclass has 15 fields. Users currently construct mounts manually or use the limited `apply_readonly_root()` preset. Mount helpers provide ergonomic functions for common patterns: directory mirroring, overlay filesystems, and system path presets.

## New Module: `src/nsjail/mounts.py`

All helpers return `list[MountPt]` — they produce mount entries that get appended to a config's mount list. They don't modify configs directly, making them composable and testable in isolation.

## Helpers

### bind_tree(path, *, readonly=True, dst=None) -> list[MountPt]

Bind-mount a directory into the sandbox.

```python
from nsjail.mounts import bind_tree

bind_tree("/usr")
# [MountPt(src="/usr", dst="/usr", is_bind=True, rw=False)]

bind_tree("/data", readonly=False, dst="/sandbox/data")
# [MountPt(src="/data", dst="/sandbox/data", is_bind=True, rw=True)]
```

### bind_paths(paths, *, readonly=True) -> list[MountPt]

Bind-mount multiple directories at once.

```python
from nsjail.mounts import bind_paths

bind_paths(["/usr", "/lib", "/lib64"])
# [MountPt(src="/usr", dst="/usr", ...), MountPt(src="/lib", dst="/lib", ...), ...]
```

### overlay_mount(lower, upper, work, dst) -> list[MountPt]

Set up an overlay filesystem with read-only base and writable upper layer.

```python
from nsjail.mounts import overlay_mount

overlay_mount(
    lower="/workspace",
    upper="/tmp/overlay/upper",
    work="/tmp/overlay/work",
    dst="/workspace",
)
# [MountPt(dst="/workspace", fstype="overlay",
#   options="lowerdir=/workspace,upperdir=/tmp/overlay/upper,workdir=/tmp/overlay/work",
#   rw=True)]
```

### system_libs() -> list[MountPt]

Read-only bind mounts for common system library and binary paths. Only includes paths that exist on the host.

```python
from nsjail.mounts import system_libs

system_libs()
# Mounts (if they exist): /lib, /lib64, /usr/lib, /usr/bin, /usr/sbin, /bin, /sbin
# All read-only bind mounts
```

### dev_minimal() -> list[MountPt]

Minimal `/dev` entries needed by most programs.

```python
from nsjail.mounts import dev_minimal

dev_minimal()
# Bind mounts for: /dev/null, /dev/zero, /dev/urandom, /dev/random
# All read-only
```

### python_env() -> list[MountPt]

Detects the current Python installation and mounts it read-only. Uses `sys.prefix` and `sys.executable` to find the right paths.

```python
from nsjail.mounts import python_env

python_env()
# Mounts the Python prefix directory (e.g., /usr or /home/user/.venv)
# Includes the stdlib, site-packages, and the interpreter binary
```

### proc_mount() -> list[MountPt]

Mount /proc filesystem.

```python
from nsjail.mounts import proc_mount

proc_mount()
# [MountPt(dst="/proc", fstype="proc")]
```

### tmpfs_mount(path, *, size=None) -> list[MountPt]

Create a tmpfs mount with optional size limit.

```python
from nsjail.mounts import tmpfs_mount

tmpfs_mount("/tmp", size="64M")
# [MountPt(dst="/tmp", fstype="tmpfs", rw=True, is_dir=True, options="size=64M")]
```

## Builder Integration

Add a `.mounts()` method to the Jail builder that accepts `list[MountPt]`:

```python
from nsjail.mounts import system_libs, dev_minimal, python_env

cfg = (
    Jail()
    .sh("python script.py")
    .readonly_root()
    .mounts(system_libs())
    .mounts(dev_minimal())
    .mounts(python_env())
    .writable("/workspace")
    .build()
)
```

The method extends `cfg.mount` with the provided list and returns `self` for chaining.

## Public API

Export from `__init__.py`:
```python
from nsjail.mounts import (
    bind_tree, bind_paths, overlay_mount,
    system_libs, dev_minimal, python_env,
    proc_mount, tmpfs_mount,
)
```

## Testing

- Unit tests: each helper produces correct MountPt entries
- system_libs/python_env: test that returned paths actually exist on the host
- overlay_mount: test correct options string generation
- Builder .mounts(): test chaining and list extension
- Edge cases: empty paths list, nonexistent paths for system_libs

## Scope Boundaries

**In scope:**
- bind_tree, bind_paths, overlay_mount
- system_libs, dev_minimal, python_env, proc_mount, tmpfs_mount
- Builder .mounts() method
- Public API exports

**Out of scope:**
- Overlay workdir creation (caller manages directories)
- Path validation (helpers trust the caller)
- Mount ordering/deduplication
