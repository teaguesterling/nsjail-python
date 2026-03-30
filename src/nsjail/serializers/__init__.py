"""Serializers for NsJailConfig: textproto, CLI args, protobuf."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nsjail.serializers.textproto import to_textproto
from nsjail.serializers.cli import to_cli_args


def to_file(cfg: Any, path: str | Path, *, validate: bool = False) -> None:
    if validate:
        try:
            from nsjail.serializers.protobuf import to_protobuf
        except ImportError:
            raise ImportError(
                "Validation requires the protobuf extra: pip install nsjail-python[proto]"
            ) from None
        to_protobuf(cfg)

    text = to_textproto(cfg)
    Path(path).write_text(text + "\n")


__all__ = ["to_textproto", "to_cli_args", "to_file"]
