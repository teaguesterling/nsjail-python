"""Auto-generated protobuf module for nsjail config.proto.

The config_pb2 module is generated from _vendor/nsjail/config.proto using
grpc_tools.protoc. If the generated module does not exist, this package
will attempt to generate it on first import.

To regenerate manually:
    python -m grpc_tools.protoc \\
        --python_out=src/nsjail/_proto/ \\
        --proto_path=_vendor/nsjail/ \\
        config.proto
"""

from __future__ import annotations

from pathlib import Path


def _compile_proto() -> None:
    """Compile config.proto using grpc_tools.protoc."""
    try:
        from grpc_tools import protoc
    except ImportError as e:
        raise ImportError(
            "grpc_tools is required to compile config.proto. "
            "Install it with: pip install grpcio-tools"
        ) from e

    proto_dir = Path(__file__).parent
    # Walk up to find the repo root (where _vendor lives)
    repo_root = proto_dir
    for _ in range(10):
        if (repo_root / "_vendor" / "nsjail" / "config.proto").exists():
            break
        repo_root = repo_root.parent
    else:
        raise FileNotFoundError(
            "Could not find _vendor/nsjail/config.proto relative to package"
        )

    proto_path = str(repo_root / "_vendor" / "nsjail")
    python_out = str(proto_dir)

    ret = protoc.main([
        "grpc_tools.protoc",
        f"--proto_path={proto_path}",
        f"--python_out={python_out}",
        "config.proto",
    ])
    if ret != 0:
        raise RuntimeError(f"grpc_tools.protoc failed with exit code {ret}")


# Attempt to import config_pb2; compile if missing
_pb2_path = Path(__file__).parent / "config_pb2.py"
if not _pb2_path.exists():
    _compile_proto()
