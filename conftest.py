"""Root conftest.py - ensures proto compilation before tests run."""

from __future__ import annotations

from pathlib import Path


def pytest_configure(config):
    """Compile config.proto if config_pb2.py does not exist."""
    proto_out = Path(__file__).parent / "src" / "nsjail" / "_proto" / "config_pb2.py"
    if proto_out.exists():
        return

    try:
        from grpc_tools import protoc
    except ImportError:
        # grpc_tools not installed; tests requiring proto will be skipped
        # via pytest.importorskip("google.protobuf")
        return

    repo_root = Path(__file__).parent
    proto_path = str(repo_root / "_vendor" / "nsjail")
    python_out = str(repo_root / "src" / "nsjail" / "_proto")

    ret = protoc.main([
        "grpc_tools.protoc",
        f"--proto_path={proto_path}",
        f"--python_out={python_out}",
        "config.proto",
    ])
    if ret != 0:
        import warnings
        warnings.warn(f"grpc_tools.protoc failed with exit code {ret}", stacklevel=1)
