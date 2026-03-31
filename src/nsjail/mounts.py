"""Mount helper functions for common sandbox filesystem patterns.

All helpers return list[MountPt] for composability.
"""

from __future__ import annotations

from nsjail.config import MountPt


def bind_tree(path: str, *, readonly: bool = True, dst: str | None = None) -> list[MountPt]:
    """Bind-mount a directory into the sandbox."""
    return [MountPt(src=path, dst=dst or path, is_bind=True, rw=not readonly)]


def bind_paths(paths: list[str], *, readonly: bool = True) -> list[MountPt]:
    """Bind-mount multiple directories into the sandbox."""
    return [
        MountPt(src=p, dst=p, is_bind=True, rw=not readonly)
        for p in paths
    ]


def tmpfs_mount(path: str, *, size: str | None = None) -> list[MountPt]:
    """Create a tmpfs mount with optional size limit."""
    options = f"size={size}" if size else None
    return [MountPt(dst=path, fstype="tmpfs", rw=True, is_dir=True, options=options)]


def proc_mount() -> list[MountPt]:
    """Mount /proc filesystem."""
    return [MountPt(dst="/proc", fstype="proc")]


def overlay_mount(
    lower: str,
    upper: str,
    work: str,
    dst: str,
) -> list[MountPt]:
    """Set up an overlay filesystem with read-only base and writable upper layer."""
    options = f"lowerdir={lower},upperdir={upper},workdir={work}"
    return [MountPt(dst=dst, fstype="overlay", options=options, rw=True)]
