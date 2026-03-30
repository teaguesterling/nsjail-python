"""Pure Python serializer for protobuf text format."""

from __future__ import annotations

from dataclasses import fields as dc_fields
from enum import IntEnum
from typing import Any

from nsjail._field_meta import FIELD_REGISTRY, FieldMeta


def to_textproto(obj: Any, indent: int = 0) -> str:
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
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _escape_bytes(b: bytes) -> str:
    parts: list[str] = []
    for byte in b:
        if 32 <= byte < 127 and byte != ord("\\") and byte != ord('"'):
            parts.append(chr(byte))
        else:
            parts.append(f"\\x{byte:02x}")
    return "".join(parts)
