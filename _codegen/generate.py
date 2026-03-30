"""Code generator: reads config.proto, emits config.py, enums.py, _field_meta.py.

Usage:
    python -m _codegen.generate [path/to/config.proto]

If no path given, uses _codegen/config.proto (vendored).
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


def main() -> None:
    proto_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("_codegen/config.proto")
    if not proto_path.exists():
        print(f"Error: {proto_path} not found", file=sys.stderr)
        print("Download it: curl -o _codegen/config.proto "
              "https://raw.githubusercontent.com/google/nsjail/master/config.proto",
              file=sys.stderr)
        sys.exit(1)

    text = proto_path.read_text()
    items = parse_proto(text)

    print(f"Parsed {len(items)} top-level items from {proto_path}")
    for item in items:
        if isinstance(item, ProtoMessage):
            print(f"  message {item.name}: {len(item.fields)} fields, "
                  f"{len(item.enums)} enums, {len(item.messages)} nested messages")
        elif isinstance(item, ProtoEnum):
            print(f"  enum {item.name}: {len(item.values)} values")

    print("\nGenerator parsed successfully. Code emission not yet implemented.")
    print("Hand-written files in src/nsjail/ are authoritative for v0.1.")


if __name__ == "__main__":
    main()
