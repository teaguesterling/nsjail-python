# Binary Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make nsjail-bin ship pre-built static binaries and nsjail-bin-build compile from source, so `pip install nsjail-python` gives users a working nsjail binary.

**Architecture:** CI workflow builds nsjail statically in manylinux containers (x86_64 + aarch64), packages into platform-tagged wheels. Build-from-source uses a hatch build hook to compile during pip install. Main package adds nsjail-bin as a default dependency.

**Tech Stack:** GitHub Actions, manylinux_2_28, hatchling build hooks, static linking

**Spec:** `docs/superpowers/specs/2026-03-30-binary-distribution-design.md`

---

### Task 1: nsjail-bin Build Hook for Platform-Tagged Wheels

**Files:**
- Create: `packages/nsjail-bin/hatch_build.py`
- Modify: `packages/nsjail-bin/pyproject.toml`

The nsjail-bin wheel must have platform tags since it contains a native binary. A hatch build hook marks it as non-pure-Python.

- [ ] **Step 1: Create the build hook**

Create `packages/nsjail-bin/hatch_build.py`:

```python
"""Hatch build hook for nsjail-bin.

Marks the wheel as platform-specific since it contains a native binary.
"""

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class NsjailBinBuildHook(BuildHookInterface):
    PLUGIN_NAME = "nsjail-bin"

    def initialize(self, version, build_data):
        build_data["pure_python"] = False
        build_data["infer_tag"] = True
```

- [ ] **Step 2: Update pyproject.toml**

Replace `packages/nsjail-bin/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nsjail-bin"
version = "0.1.0"
description = "Pre-built nsjail binary for nsjail-python"
requires-python = ">=3.12"
license = "MIT"

[tool.hatch.build.targets.wheel]
packages = ["src/nsjail_bin"]

[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
```

- [ ] **Step 3: Create _bin directory with placeholder**

```bash
mkdir -p packages/nsjail-bin/src/nsjail_bin/_bin
touch packages/nsjail-bin/src/nsjail_bin/_bin/.gitkeep
```

- [ ] **Step 4: Verify wheel builds locally**

```bash
cd packages/nsjail-bin
pip install build hatchling
python -m build --wheel
```

Expected: Produces a wheel with a platform tag (e.g., `linux_x86_64`), not `py3-none-any`. The wheel will have an empty `_bin/` dir since no binary is present locally — CI populates it.

- [ ] **Step 5: Commit**

```bash
git add packages/nsjail-bin/
git commit -m "feat: add hatch build hook for platform-tagged nsjail-bin wheels"
```

---

### Task 2: nsjail-bin-build Build Hook (Compile from Source)

**Files:**
- Create: `packages/nsjail-bin-build/hatch_build.py`
- Modify: `packages/nsjail-bin-build/pyproject.toml`

This build hook compiles nsjail from vendored source during `pip install`. It checks for required build tools, runs `make`, and copies the binary.

- [ ] **Step 1: Create the build hook**

Create `packages/nsjail-bin-build/hatch_build.py`:

```python
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

        # Find nsjail source — in repo it's at _vendor/nsjail,
        # in sdist it's bundled at nsjail_src/
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
```

- [ ] **Step 2: Update pyproject.toml**

Replace `packages/nsjail-bin-build/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nsjail-bin-build"
version = "0.1.0"
description = "Build nsjail from source for nsjail-python"
requires-python = ">=3.12"
license = "MIT"

[tool.hatch.build.targets.wheel]
packages = ["src/nsjail_bin_build"]

[tool.hatch.build.targets.sdist]
include = [
    "src/",
    "hatch_build.py",
    "pyproject.toml",
]

[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
```

Note: The sdist doesn't include the nsjail source directly — building from sdist requires the vendored source to be available. For a proper sdist workflow, a pre-build script would copy `_vendor/nsjail/` into the sdist. This is a future enhancement; for now, building from the git repo (which has the submodule) is the supported path.

- [ ] **Step 3: Test the build hook locally**

If build tools are available on the machine:

```bash
cd /mnt/aux-data/teague/Projects/nsjail-python
cd packages/nsjail-bin-build
pip install build hatchling
python -m build --wheel
```

If build tools are NOT available, verify the hook fails with a clear error:

```bash
python -c "
from pathlib import Path
import sys
sys.path.insert(0, '.')
from hatch_build import NsjailBuildFromSourceHook
"
```

- [ ] **Step 4: Commit**

```bash
git add packages/nsjail-bin-build/
git commit -m "feat: add hatch build hook for nsjail-bin-build (compile from source)"
```

---

### Task 3: CI Workflow for Building Static Binaries

**Files:**
- Create: `.github/workflows/build-binaries.yml`

This workflow builds nsjail statically in manylinux containers and publishes nsjail-bin platform wheels.

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/build-binaries.yml`:

```yaml
name: Build nsjail binaries

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  id-token: write

jobs:
  build-binary:
    strategy:
      matrix:
        include:
          - arch: x86_64
            platform: manylinux_2_28_x86_64
          - arch: aarch64
            platform: manylinux_2_28_aarch64

    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Set up QEMU
        if: matrix.arch == 'aarch64'
        uses: docker/setup-qemu-action@v3
        with:
          platforms: arm64

      - name: Build nsjail in manylinux container
        run: |
          docker run --rm \
            --platform linux/${{ matrix.arch == 'aarch64' && 'arm64' || 'amd64' }} \
            -v ${{ github.workspace }}:/work \
            -w /work \
            quay.io/pypa/manylinux_2_28_${{ matrix.arch }} \
            bash -c '
              set -ex

              # Install build dependencies
              yum install -y \
                protobuf-compiler protobuf-devel \
                libnl3-devel libcap-devel \
                bison flex autoconf libtool git make gcc-c++ \
                pkg-config

              # Build nsjail
              cd _vendor/nsjail
              make -j$(nproc)
              strip nsjail

              # Verify binary
              file nsjail
              ./nsjail --help || true

              # Copy into package
              cp nsjail /work/packages/nsjail-bin/src/nsjail_bin/_bin/nsjail
              chmod +x /work/packages/nsjail-bin/src/nsjail_bin/_bin/nsjail
            '

      - name: Build wheel
        run: |
          pip install build hatchling
          cd packages/nsjail-bin
          python -m build --wheel

      - name: Verify wheel contents
        run: |
          pip install packages/nsjail-bin/dist/*.whl
          python -c "
          from nsjail_bin import binary_path
          p = binary_path()
          print(f'Binary at: {p}')
          print(f'Size: {p.stat().st_size} bytes')
          "

      - uses: actions/upload-artifact@v4
        with:
          name: nsjail-bin-${{ matrix.arch }}
          path: packages/nsjail-bin/dist/*.whl

  publish-binary:
    needs: build-binary
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: dist/
          merge-multiple: true

      - name: List wheels
        run: ls -la dist/

      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/build-binaries.yml
git commit -m "ci: add workflow for building static nsjail binaries (x86_64 + aarch64)"
```

---

### Task 4: Update Main Package Dependencies

**Files:**
- Modify: `pyproject.toml`

Add `nsjail-bin` as a default dependency and add the `build` and `system` extras that swap it out.

- [ ] **Step 1: Update pyproject.toml**

In the root `pyproject.toml`, change `dependencies` and add extras:

```toml
dependencies = ["nsjail-bin"]

[project.optional-dependencies]
proto = ["protobuf>=4.0"]
build = ["nsjail-bin-build"]
system = ["nsjail-bin-none"]
dev = [
    "grpcio-tools",
    "pytest",
    "protobuf>=4.0",
    "sphinx",
    "furo",
]
```

Note: The `build` and `system` extras install alternative companion packages. pip's dependency resolution means if a user does `pip install nsjail-python[system]`, both `nsjail-bin` (from dependencies) and `nsjail-bin-none` get installed — but since both are tiny packages and nsjail-bin's binary won't be present on platforms without a wheel, this is harmless. The Runner's resolution order (system PATH first, then companion) handles it correctly.

- [ ] **Step 2: Verify local install still works**

```bash
cd /mnt/aux-data/teague/Projects/nsjail-python
pip install -e ".[dev]"
python -c "from nsjail import Jail, Runner; print('ok')"
```

Note: `nsjail-bin` won't have a binary locally (no CI build happened), but the package should install. The Runner will fall back to system nsjail or raise NsjailNotFound.

- [ ] **Step 3: Run tests**

```bash
pytest tests/ -q
```

Expected: All 136 tests pass.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add nsjail-bin as default dependency, add build/system extras"
```

---

### Task 5: Publish Workflow for Companion Packages

**Files:**
- Create: `.github/workflows/publish-companions.yml`

Publishes `nsjail-bin-build` and `nsjail-bin-none` to PyPI. These are simple packages that don't need platform builds.

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/publish-companions.yml`:

```yaml
name: Publish companion packages

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  id-token: write

jobs:
  publish-bin-build:
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build nsjail-bin-build sdist
        run: |
          pip install build hatchling
          cd packages/nsjail-bin-build
          python -m build --sdist
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: packages/nsjail-bin-build/dist/

  publish-bin-none:
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build nsjail-bin-none
        run: |
          pip install build hatchling
          cd packages/nsjail-bin-none
          python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: packages/nsjail-bin-none/dist/
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/publish-companions.yml
git commit -m "ci: add publish workflow for companion packages"
```

---

### Task 6: Update README and Push

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README installation section**

Add the companion package install patterns to the README. Find the installation section and update it to explain the three install modes:

```markdown
## Installation

```bash
# Default: includes pre-built nsjail binary
pip install nsjail-python

# Use system-provided nsjail (no bundled binary)
pip install nsjail-python[system]

# Build nsjail from source during install
pip install nsjail-python[build]

# Add protobuf validation support
pip install nsjail-python[proto]
```
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: update README with binary distribution install patterns"
git push
```
