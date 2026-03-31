"""Fixtures for nsjail integration tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from nsjail.runner import Runner


def _find_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not find repo root")


def _build_nsjail(vendor_dir: Path) -> Path | None:
    nsjail_src = vendor_dir / "nsjail"
    if not (nsjail_src / "Makefile").exists():
        return None

    for tool in ("make", "g++", "protoc", "bison", "flex", "pkg-config"):
        if not shutil.which(tool):
            return None

    kafel_dir = nsjail_src / "kafel"
    if not (kafel_dir / "Makefile").exists():
        result = subprocess.run(
            ["git", "submodule", "update", "--init"],
            cwd=nsjail_src,
            capture_output=True,
        )
        if result.returncode != 0:
            return None

    result = subprocess.run(
        ["make", f"-j{os.cpu_count() or 1}"],
        cwd=nsjail_src,
        capture_output=True,
        timeout=300,
    )
    if result.returncode != 0:
        return None

    binary = nsjail_src / "nsjail"
    if binary.exists():
        return binary
    return None


@pytest.fixture(scope="session")
def nsjail_binary() -> Path:
    system = shutil.which("nsjail")
    if system:
        return Path(system)

    repo_root = _find_repo_root()
    vendor_dir = repo_root / "_vendor"

    built = vendor_dir / "nsjail" / "nsjail"
    if built.exists():
        return built

    binary = _build_nsjail(vendor_dir)
    if binary:
        return binary

    pytest.skip(
        "nsjail binary not available. Install nsjail, or install build deps: "
        "apt-get install protobuf-compiler libprotobuf-dev libnl-route-3-dev "
        "libcap-dev bison flex"
    )


@pytest.fixture
def runner(nsjail_binary: Path) -> Runner:
    return Runner(nsjail_path=str(nsjail_binary))
