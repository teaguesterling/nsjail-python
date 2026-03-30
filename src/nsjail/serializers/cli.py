"""Serialize NsJailConfig to nsjail CLI arguments."""

from __future__ import annotations

import logging
from dataclasses import fields as dc_fields
from enum import IntEnum
from typing import Any, Literal

from nsjail._field_meta import FIELD_REGISTRY
from nsjail.exceptions import UnsupportedCLIField

logger = logging.getLogger(__name__)


def to_cli_args(
    cfg: Any,
    *,
    on_unsupported: Literal["raise", "warn", "skip"] = "raise",
) -> list[str]:
    args: list[str] = []
    cls_name = type(cfg).__name__

    for f in dc_fields(cfg):
        key = (cls_name, f.name)
        meta = FIELD_REGISTRY.get(key)
        if meta is None:
            continue

        value = getattr(cfg, f.name)

        # Skip defaults and None
        if meta.is_repeated:
            if not value:
                continue
        elif meta.is_message:
            if value is None:
                continue
        else:
            from nsjail.serializers.textproto import _is_default
            if _is_default(value, meta):
                continue

        # Check CLI support
        if not meta.cli_supported or meta.cli_flag is None:
            if on_unsupported == "raise":
                raise UnsupportedCLIField(f.name)
            elif on_unsupported == "warn":
                logger.warning(
                    "Config field %r has no CLI equivalent, skipping", f.name
                )
            continue

        # Render the field
        if meta.is_repeated:
            for item in value:
                args.append(meta.cli_flag)
                args.append(str(item))
        elif isinstance(value, bool):
            if value:
                args.append(meta.cli_flag)
        elif isinstance(value, IntEnum):
            args.append(meta.cli_flag)
            args.append(str(int(value)))
        else:
            args.append(meta.cli_flag)
            args.append(str(value))

    return args
