"""Code generator: reads config.proto, emits config.py, enums.py, _field_meta.py.

Usage:
    python -m _codegen.generate [path/to/config.proto]

If no path given, uses _vendor/nsjail/config.proto (vendored).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


HEADER = '''\
# GENERATED from nsjail config.proto — DO NOT EDIT
# Re-run: python -m _codegen.generate
'''


@dataclass
class ProtoField:
    label: str
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
    """Simple regex-based parser for the subset of proto2 used by nsjail."""
    text = re.sub(r'//[^\n]*', '', text)
    results: list[ProtoMessage | ProtoEnum] = []
    _parse_block(text, results)
    return results


def _parse_block(text: str, results: list) -> None:
    pos = 0
    while pos < len(text):
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

        m = re.match(r'\s*message\s+(\w+)\s*\{', text[pos:])
        if m:
            name = m.group(1)
            brace_start = pos + m.end()
            brace_end = _find_matching_brace(text, brace_start - 1)
            body = text[brace_start:brace_end]

            msg = ProtoMessage(name=name, fields=[], enums=[], messages=[])

            nested: list = []
            _parse_block(body, nested)
            for item in nested:
                if isinstance(item, ProtoEnum):
                    msg.enums.append(item)
                elif isinstance(item, ProtoMessage):
                    msg.messages.append(item)

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


# ── Enum classification ──────────────────────────────────────────────────────

# Enums that are nested inside messages but should be top-level in enums.py
PROMOTED_ENUMS: dict[tuple[str, str], str] = {
    ("NsJailConfig", "RLimit"): "RLimitType",
}

# Top-level enums that should be renamed in the generated output
RENAMED_ENUMS: dict[str, str] = {
    "RLimit": "RLimitType",
}

# Top-level enums that are imported from enums.py into config.py
# Maps proto enum name → Python name used in config.py
KNOWN_ENUMS: dict[str, str] = {
    "Mode": "Mode",
    "LogLevel": "LogLevel",
}

# Renamed top-level enums also available as imports
for _proto_name, _py_name in RENAMED_ENUMS.items():
    KNOWN_ENUMS[_proto_name] = _py_name

# Promoted enums also available as imports (original proto name → Python name)
for (_msg, _proto_name), _py_name in PROMOTED_ENUMS.items():
    KNOWN_ENUMS[_proto_name] = _py_name

# All enum names (proto name → Python name), including nested non-promoted enums
# Built dynamically during emit_config
_ALL_ENUM_NAMES: dict[str, str] = {}

# ── Default override rules ────────────────────────────────────────────────────

# Messages where ALL string/bytes fields with empty-string proto defaults
# should be treated as None (unset) rather than "".
_NONE_DEFAULT_MESSAGES: set[str] = {"MountPt"}

# Individual (message, field) pairs where empty-string default → None.
_NONE_DEFAULT_FIELDS: set[tuple[str, str]] = {
    ("NsJailConfig", "name"),
}

# Scalar proto types → Python type name
_SCALAR_TYPES: dict[str, str] = {
    "string": "str",
    "uint32": "int",
    "int32": "int",
    "uint64": "int",
    "int64": "int",
    "bool": "bool",
    "bytes": "bytes",
}

# Proto type → proto_type string used in _field_meta.py
_META_PROTO_TYPES: dict[str, str] = {
    "string": "string",
    "uint32": "uint32",
    "int32": "int32",
    "uint64": "uint64",
    "int64": "int64",
    "bool": "bool",
    "bytes": "bytes",
}


def emit_enums(top_level_enums: list[ProtoEnum], messages: list[ProtoMessage]) -> str:
    """Generate enums.py content."""
    lines = [HEADER, "from enum import IntEnum\n"]

    for enum in top_level_enums:
        python_name = RENAMED_ENUMS.get(enum.name, enum.name)
        lines.append(f"\nclass {python_name}(IntEnum):")
        for name, value in enum.values:
            lines.append(f"    {name} = {value}")
        lines.append("")

    for msg in messages:
        for nested_enum in msg.enums:
            key = (msg.name, nested_enum.name)
            python_name = PROMOTED_ENUMS.get(key)
            if python_name:
                lines.append(f"\nclass {python_name}(IntEnum):")
                for name, value in nested_enum.values:
                    lines.append(f"    {name} = {value}")
                lines.append("")

    return "\n".join(lines) + "\n"


# ── Config emitter ────────────────────────────────────────────────────────────


def _build_enum_lookup(
    top_enums: list[ProtoEnum],
    messages: list[ProtoMessage],
) -> dict[str, dict[str, int]]:
    """Build enum_name → {value_name: int_value} for all enums."""
    lookup: dict[str, dict[str, int]] = {}
    for e in top_enums:
        lookup[e.name] = dict(e.values)
    for msg in messages:
        for ne in msg.enums:
            lookup[ne.name] = dict(ne.values)
        for sub in msg.messages:
            for ne in sub.enums:
                lookup[ne.name] = dict(ne.values)
    return lookup


def _resolve_field_type(
    field: ProtoField,
    msg_name: str,
    all_message_names: set[str],
) -> tuple[str, bool, bool]:
    """Return (python_type, is_enum, is_message) for a field's proto type."""
    if field.type in _SCALAR_TYPES:
        return _SCALAR_TYPES[field.type], False, False
    if field.type in _ALL_ENUM_NAMES:
        return _ALL_ENUM_NAMES[field.type], True, False
    if field.type in all_message_names:
        return field.type, False, True
    # Unknown type — treat as string
    return "str", False, False


def _resolve_default(
    field: ProtoField,
    msg_name: str,
    python_type: str,
    is_enum: bool,
    is_message: bool,
    enum_lookup: dict[str, dict[str, int]],
) -> str | None:
    """Return the Python default expression as a string, or None for no default.

    Returns None to signal "needs | None = None" annotation.
    Returns a string like 'False', '0', '"NSJAIL"' for explicit defaults.
    """
    is_repeated = field.label == "repeated"

    if is_repeated:
        return "field(default_factory=list)"

    # Optional message fields → None
    if is_message:
        return None

    proto_default = field.default

    # No proto default annotation
    if proto_default is None:
        return None

    # Check for None-override rules (empty string defaults treated as None)
    if proto_default in ('""', "''", '""'):
        raw = ""
    elif proto_default.startswith('"') and proto_default.endswith('"'):
        raw = proto_default[1:-1]
    else:
        raw = None  # Not a string default

    if raw is not None and raw == "":
        if msg_name in _NONE_DEFAULT_MESSAGES:
            return None
        if (msg_name, field.name) in _NONE_DEFAULT_FIELDS:
            return None

    # Enum defaults
    if is_enum:
        enum_py_name = _ALL_ENUM_NAMES.get(field.type, field.type)
        return f"{enum_py_name}.{proto_default}"

    # Bool defaults
    if field.type == "bool":
        if proto_default == "true":
            return "True"
        return "False"

    # Integer defaults
    if field.type in ("uint32", "int32", "uint64", "int64"):
        return proto_default

    # String defaults
    if field.type == "string":
        # proto_default is like '"NSJAIL"' (with quotes) or just NSJAIL
        if proto_default.startswith('"') and proto_default.endswith('"'):
            return proto_default  # Already quoted
        return f'"{proto_default}"'

    # Bytes defaults — empty bytes treated same as string
    if field.type == "bytes":
        if proto_default in ('""', "''"):
            return None  # Already handled above for None-override messages
        return proto_default

    return proto_default


def _emit_field_line(
    field: ProtoField,
    msg_name: str,
    all_message_names: set[str],
    enum_lookup: dict[str, dict[str, int]],
) -> str:
    """Emit a single dataclass field line."""
    python_type, is_enum, is_message = _resolve_field_type(
        field, msg_name, all_message_names
    )
    is_repeated = field.label == "repeated"

    default = _resolve_default(
        field, msg_name, python_type, is_enum, is_message, enum_lookup
    )

    if is_repeated:
        type_str = f"list[{python_type}]"
        return f"    {field.name}: {type_str} = {default}"

    if default is None:
        type_str = f"{python_type} | None"
        return f"    {field.name}: {type_str} = None"

    return f"    {field.name}: {python_type} = {default}"


def emit_config(
    messages: list[ProtoMessage],
    top_enums: list[ProtoEnum],
) -> str:
    """Generate config.py content from parsed proto messages and enums."""
    # Build the global enum name mapping
    _ALL_ENUM_NAMES.clear()
    _ALL_ENUM_NAMES.update(KNOWN_ENUMS)

    # Collect all nested enums NOT in PROMOTED_ENUMS — these go into config.py
    local_enums: list[tuple[str, ProtoEnum]] = []
    for msg in messages:
        for ne in msg.enums:
            key = (msg.name, ne.name)
            if key not in PROMOTED_ENUMS:
                _ALL_ENUM_NAMES[ne.name] = ne.name
                local_enums.append((msg.name, ne))
            # Promoted enums are already in KNOWN_ENUMS
        for sub in msg.messages:
            for ne in sub.enums:
                key = (sub.name, ne.name)
                if key not in PROMOTED_ENUMS:
                    _ALL_ENUM_NAMES[ne.name] = ne.name
                    local_enums.append((sub.name, ne))

    enum_lookup = _build_enum_lookup(top_enums, messages)

    # Collect all message names (top-level + nested) for type resolution
    all_message_names: set[str] = set()
    nested_messages: list[ProtoMessage] = []
    top_messages: list[ProtoMessage] = []

    for msg in messages:
        all_message_names.add(msg.name)
        top_messages.append(msg)
        for sub in msg.messages:
            all_message_names.add(sub.name)
            nested_messages.append(sub)

    # Determine which enums from enums.py are actually used
    enums_used: set[str] = set()
    all_msgs = top_messages + nested_messages
    for msg in all_msgs:
        for f in msg.fields:
            if f.type in KNOWN_ENUMS:
                enums_used.add(KNOWN_ENUMS[f.type])

    # Build output
    lines = [HEADER]
    lines.append("from __future__ import annotations\n")
    lines.append("from dataclasses import dataclass, field")
    lines.append("from enum import IntEnum\n")

    if enums_used:
        imports = sorted(enums_used)
        lines.append(f"from nsjail.enums import {', '.join(imports)}\n")

    # Emit nested messages first (they're referenced by top-level messages)
    for sub in nested_messages:
        lines.append("")
        lines.append("@dataclass")
        lines.append(f"class {sub.name}:")
        for f in sub.fields:
            lines.append(
                _emit_field_line(f, sub.name, all_message_names, enum_lookup)
            )
        lines.append("")

    # Emit local enums (nested enums NOT promoted to enums.py)
    for _parent, ne in local_enums:
        lines.append("")
        lines.append(f"class {ne.name}(IntEnum):")
        for vname, vval in ne.values:
            lines.append(f"    {vname} = {vval}")
        lines.append("")

    # Emit top-level messages
    for msg in top_messages:
        lines.append("")
        lines.append("@dataclass")
        lines.append(f"class {msg.name}:")
        for f in msg.fields:
            lines.append(
                _emit_field_line(f, msg.name, all_message_names, enum_lookup)
            )
        lines.append("")

    return "\n".join(lines) + "\n"


# ── Field meta emitter ────────────────────────────────────────────────────────


def emit_field_meta(
    messages: list[ProtoMessage],
    cli_flags: dict[tuple[str, str], tuple[str | None, bool]],
    top_enums: list[ProtoEnum] | None = None,
) -> str:
    """Generate _field_meta.py content.

    Note: emit_config() must be called first to populate _ALL_ENUM_NAMES.
    """
    enum_lookup = _build_enum_lookup(top_enums or [], messages)

    lines = [HEADER]
    lines.append("from __future__ import annotations\n")
    lines.append("from dataclasses import dataclass\n\n")
    lines.append("@dataclass(frozen=True)")
    lines.append("class FieldMeta:")
    lines.append('    """Metadata about a single proto field."""')
    lines.append("    number: int")
    lines.append("    proto_type: str")
    lines.append("    default: object")
    lines.append("    cli_flag: str | None")
    lines.append("    cli_supported: bool")
    lines.append("    is_repeated: bool")
    lines.append("    is_message: bool\n\n")
    lines.append("FIELD_REGISTRY: dict[tuple[str, str], FieldMeta] = {}\n\n")
    lines.append('def _r(msg: str, name: str, **kwargs: object) -> None:')
    lines.append('    FIELD_REGISTRY[(msg, name)] = FieldMeta(**kwargs)  # type: ignore[arg-type]')
    lines.append("")

    # Collect all messages (nested first, then top-level)
    all_msgs: list[ProtoMessage] = []
    for msg in messages:
        for sub in msg.messages:
            all_msgs.append(sub)
    # Then top-level messages that are NOT NsJailConfig (sub-messages first)
    top_non_config = [m for m in messages if m.name != "NsJailConfig"]
    top_config = [m for m in messages if m.name == "NsJailConfig"]
    all_msgs.extend(top_non_config)
    all_msgs.extend(top_config)

    for msg in all_msgs:
        lines.append(f"\n# ── {msg.name} ({len(msg.fields)} fields) " + "─" * max(1, 60 - len(msg.name)) + "──")
        for f in msg.fields:
            is_repeated = f.label == "repeated"
            is_message = f.type in {m.name for m in messages} | {
                sub.name for m2 in messages for sub in m2.messages
            }
            is_enum = f.type in _ALL_ENUM_NAMES

            # Determine proto_type for meta
            if is_message:
                proto_type = "message"
            elif is_enum:
                proto_type = "enum"
            elif f.type in _META_PROTO_TYPES:
                proto_type = _META_PROTO_TYPES[f.type]
            else:
                proto_type = f.type

            # Determine default for meta
            meta_default = _compute_meta_default(
                f, msg.name, is_repeated, is_message, is_enum, enum_lookup
            )

            # CLI flag lookup
            key = (msg.name, f.name)
            if key in cli_flags:
                cli_flag_val, cli_supported = cli_flags[key]
                cli_flag_repr = f'"{cli_flag_val}"' if cli_flag_val else "None"
            else:
                cli_flag_repr = "None"
                cli_supported = False

            lines.append(
                f'_r("{msg.name}", "{f.name}", '
                f"number={f.number}, "
                f'proto_type="{proto_type}", '
                f"default={meta_default}, "
                f"cli_flag={cli_flag_repr}, "
                f"cli_supported={cli_supported}, "
                f"is_repeated={is_repeated}, "
                f"is_message={is_message})"
            )

    lines.append("\ndel _r\n")
    return "\n".join(lines) + "\n"


def _compute_meta_default(
    field: ProtoField,
    msg_name: str,
    is_repeated: bool,
    is_message: bool,
    is_enum: bool,
    enum_lookup: dict[str, dict[str, int]],
) -> str:
    """Compute the Python repr of a field's default for _field_meta."""
    if is_repeated:
        return "[]"

    if is_message:
        return "None"

    proto_default = field.default

    if proto_default is None:
        return "None"

    # Check None-override rules
    if field.type in ("string", "bytes"):
        raw = ""
        if proto_default in ('""', "''"):
            raw = ""
        elif proto_default.startswith('"') and proto_default.endswith('"'):
            raw = proto_default[1:-1]
        else:
            raw = proto_default

        if raw == "":
            if msg_name in _NONE_DEFAULT_MESSAGES:
                return "None"
            if (msg_name, field.name) in _NONE_DEFAULT_FIELDS:
                return "None"

    # Enum → integer value
    if is_enum and field.type in enum_lookup:
        vals = enum_lookup[field.type]
        if proto_default in vals:
            return str(vals[proto_default])
        return proto_default

    # Bool
    if field.type == "bool":
        return "True" if proto_default == "true" else "False"

    # Integer
    if field.type in ("uint32", "int32", "uint64", "int64"):
        return proto_default

    # String
    if field.type == "string":
        if proto_default.startswith('"') and proto_default.endswith('"'):
            return proto_default
        return f'"{proto_default}"'

    return proto_default


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    # Resolve proto path
    if len(sys.argv) > 1:
        proto_path = Path(sys.argv[1])
    else:
        proto_path = Path("_vendor/nsjail/config.proto")
        if not proto_path.exists():
            proto_path = Path("_codegen/config.proto")

    if not proto_path.exists():
        print(f"Error: {proto_path} not found", file=sys.stderr)
        print("Download it: curl -o _vendor/nsjail/config.proto "
              "https://raw.githubusercontent.com/google/nsjail/master/config.proto",
              file=sys.stderr)
        sys.exit(1)

    text = proto_path.read_text()
    items = parse_proto(text)

    top_enums = [i for i in items if isinstance(i, ProtoEnum)]
    messages = [i for i in items if isinstance(i, ProtoMessage)]

    print(f"Parsed {len(items)} top-level items from {proto_path}")
    for item in items:
        if isinstance(item, ProtoMessage):
            print(f"  message {item.name}: {len(item.fields)} fields, "
                  f"{len(item.enums)} enums, {len(item.messages)} nested messages")
        elif isinstance(item, ProtoEnum):
            print(f"  enum {item.name}: {len(item.values)} values")

    # Import CLI flags
    from _codegen.cli_flags import CLI_FLAGS

    # Generate all three files
    out_dir = Path("src/nsjail")

    enums_out = emit_enums(top_enums, messages)
    (out_dir / "enums.py").write_text(enums_out)
    print(f"\nWrote {out_dir / 'enums.py'} ({len(enums_out)} bytes)")

    config_out = emit_config(messages, top_enums)
    (out_dir / "config.py").write_text(config_out)
    print(f"Wrote {out_dir / 'config.py'} ({len(config_out)} bytes)")

    meta_out = emit_field_meta(messages, CLI_FLAGS, top_enums=top_enums)
    (out_dir / "_field_meta.py").write_text(meta_out)
    print(f"Wrote {out_dir / '_field_meta.py'} ({len(meta_out)} bytes)")

    print("\nDone. Run tests: pytest tests/ -v")


if __name__ == "__main__":
    main()
