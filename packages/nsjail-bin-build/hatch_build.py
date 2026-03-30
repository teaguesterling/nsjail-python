"""Hatch build hook for nsjail-bin-build.

Compiles nsjail from vendored source during wheel build.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

REQUIRED_TOOLS = {
    "make": "make",
    "g++": "g++",
    "protoc": "protobuf-compiler",
    "bison": "bison",
    "flex": "flex",
    "pkg-config": "pkg-config",
}

INSTALL_HINT = (
    "Install build dependencies:\n"
    "  apt-get install gcc g++ make protobuf-compiler "
    "libprotobuf-dev libnl-route-3-dev libcap-dev "
    "bison flex pkg-config autoconf libtool\n"
    "Or use the pre-built binary: pip install nsjail-bin"
)


class NsjailBuildFromSourceHook(BuildHookInterface):
    PLUGIN_NAME = "nsjail-bin-build"

    def initialize(self, version, build_data):
        build_data["pure_python"] = False
        build_data["infer_tag"] = True

        root = Path(self.root)

        # Find nsjail source
        nsjail_src = root / "_vendor" / "nsjail"
        if not (nsjail_src / "Makefile").exists():
            nsjail_src = root / "nsjail_src"
        if not (nsjail_src / "Makefile").exists():
            raise RuntimeError(
                "nsjail source not found. Expected at _vendor/nsjail/ or nsjail_src/.\n"
                "Try: pip install nsjail-bin (pre-built binary)"
            )

        # Check for required build tools
        missing = []
        for tool, pkg in REQUIRED_TOOLS.items():
            if not shutil.which(tool):
                missing.append(f"  {tool} (install: {pkg})")
        if missing:
            raise RuntimeError(
                f"Missing required build tools:\n"
                + "\n".join(missing)
                + f"\n\n{INSTALL_HINT}"
            )

        # Init kafel submodule if needed
        kafel_dir = nsjail_src / "kafel"
        if not (kafel_dir / "Makefile").exists():
            subprocess.run(
                ["git", "submodule", "update", "--init"],
                cwd=nsjail_src,
                check=True,
            )

        # Build nsjail
        result = subprocess.run(
            ["make", f"-j{os.cpu_count() or 1}"],
            cwd=nsjail_src,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"nsjail build failed (exit {result.returncode}):\n"
                f"{result.stderr[-2000:]}\n\n{INSTALL_HINT}"
            )

        # Copy binary into package
        bin_dir = root / "src" / "nsjail_bin_build" / "_bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        built = nsjail_src / "nsjail"
        if not built.exists():
            raise RuntimeError(f"Build succeeded but binary not found at {built}")
        shutil.copy2(built, bin_dir / "nsjail")
        os.chmod(bin_dir / "nsjail", 0o755)
