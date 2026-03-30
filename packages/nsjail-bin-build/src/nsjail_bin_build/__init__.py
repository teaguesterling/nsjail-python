"""Build-from-source nsjail binary distribution."""

from pathlib import Path


def binary_path() -> Path:
    """Return the path to the built nsjail binary."""
    bin_path = Path(__file__).parent / "_bin" / "nsjail"
    if not bin_path.exists():
        raise FileNotFoundError(
            f"Built nsjail binary not found at {bin_path}. "
            f"The build may have failed during installation. "
            f"Check build logs or try: pip install nsjail-python"
        )
    return bin_path
