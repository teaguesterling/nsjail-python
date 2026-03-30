"""Pre-built nsjail binary distribution."""

from pathlib import Path


def binary_path() -> Path:
    """Return the path to the bundled nsjail binary."""
    bin_path = Path(__file__).parent / "_bin" / "nsjail"
    if not bin_path.exists():
        raise FileNotFoundError(
            f"Bundled nsjail binary not found at {bin_path}. "
            f"This platform may not have a pre-built binary. "
            f"Try: pip install nsjail-python[build]"
        )
    return bin_path
