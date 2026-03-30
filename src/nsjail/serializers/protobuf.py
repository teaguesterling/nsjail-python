"""Convert NsJailConfig dataclass to compiled protobuf message.

Requires the [proto] extra: pip install nsjail-python[proto]
"""

from __future__ import annotations

from typing import Any

from google.protobuf import text_format

from nsjail.serializers.textproto import to_textproto


def to_protobuf(cfg: Any) -> Any:
    """Convert a NsJailConfig to a compiled protobuf message."""
    from nsjail._proto import config_pb2

    text = to_textproto(cfg)
    msg = config_pb2.NsJailConfig()
    text_format.Parse(text, msg)
    return msg
