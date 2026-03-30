# nsjail Binary Distribution Design Spec

**Date:** 2026-03-30
**Status:** Draft
**Scope:** Make nsjail-bin and nsjail-bin-build functional — ship pre-built static binaries and support build-from-source

## Context

nsjail-python v0.1.0 shipped with companion package scaffolding (`nsjail-bin`, `nsjail-bin-build`, `nsjail-bin-none`) but none of them actually provide an nsjail binary. Users must install nsjail separately. This spec makes the companion packages functional:

- `nsjail-bin` ships a fully static nsjail binary in platform-specific wheels
- `nsjail-bin-build` compiles nsjail from vendored source during `pip install`

## Part 1: nsjail-bin — Pre-built Static Binaries

### Build environment

A GitHub Actions workflow builds nsjail inside `manylinux_2_28` containers. Two platforms:

- `manylinux_2_28_x86_64`
- `manylinux_2_28_aarch64` (via QEMU emulation)

### Static build process

Inside the manylinux container:

1. Install build dependencies:
   ```bash
   yum install -y protobuf-compiler protobuf-devel protobuf-static \
       libnl3-devel libnl3-static libcap-devel libcap-static \
       bison flex autoconf libtool
   ```
   Note: manylinux_2_28 is based on AlmaLinux 8. Package names may vary — the workflow should handle this.

2. Build nsjail with static linking:
   ```bash
   cd _vendor/nsjail
   git submodule update --init  # kafel
   make -j$(nproc) LDFLAGS="-static"
   strip nsjail
   ```
   If the manylinux base doesn't have static libraries, build them from source (protobuf, libnl3, libcap) before building nsjail.

3. Verify the binary is static:
   ```bash
   file nsjail  # Should say "statically linked"
   ldd nsjail   # Should say "not a dynamic executable"
   ```

4. Copy binary into the package:
   ```bash
   cp nsjail ../../packages/nsjail-bin/src/nsjail_bin/_bin/nsjail
   chmod +x ../../packages/nsjail-bin/src/nsjail_bin/_bin/nsjail
   ```

### Platform-tagged wheel

`nsjail-bin` must produce platform-specific wheels since it contains a native binary. The pure-Python wheel tag (`py3-none-any`) won't work.

**Approach:** Use a custom hatch build hook that:
1. Includes the `_bin/nsjail` binary in the wheel
2. Sets the wheel platform tag to match the build platform

`packages/nsjail-bin/hatch_build.py`:
```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class NsjailBinBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Mark as platform-specific
        build_data["pure_python"] = False
        build_data["infer_tag"] = True
```

And in `packages/nsjail-bin/pyproject.toml`:
```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
```

### CI workflow: build-binaries.yml

```yaml
name: Build nsjail binaries

on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        include:
          - arch: x86_64
            runner: ubuntu-latest
          - arch: aarch64
            runner: ubuntu-latest  # Uses QEMU

    runs-on: ${{ matrix.runner }}
    container:
      image: quay.io/pypa/manylinux_2_28_${{ matrix.arch }}

    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Install build deps
        run: |
          # Install static libraries and build tools
          yum install -y protobuf-compiler protobuf-devel \
              libnl3-devel libcap-devel \
              bison flex autoconf libtool git

      - name: Build nsjail (static)
        run: |
          cd _vendor/nsjail
          make -j$(nproc)
          strip nsjail
          cp nsjail ../../packages/nsjail-bin/src/nsjail_bin/_bin/nsjail
          chmod +x ../../packages/nsjail-bin/src/nsjail_bin/_bin/nsjail

      - name: Build wheel
        run: |
          cd packages/nsjail-bin
          pip install build hatchling
          python -m build --wheel

      - uses: actions/upload-artifact@v4
        with:
          name: nsjail-bin-${{ matrix.arch }}
          path: packages/nsjail-bin/dist/*.whl

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: dist/
          merge-multiple: true
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/
```

For aarch64 builds, QEMU setup is needed before the container step:
```yaml
      - uses: docker/setup-qemu-action@v3
        if: matrix.arch == 'aarch64'
```

### Binary verification

The workflow should verify the built binary works:
```bash
# Inside the container
./nsjail --help  # Basic smoke test
```

## Part 2: nsjail-bin-build — Build from Source

### How it works

When a user runs `pip install nsjail-bin-build`, the build backend:
1. Includes the vendored nsjail source in the sdist
2. During wheel build, compiles nsjail from source
3. Places the binary at `src/nsjail_bin_build/_bin/nsjail`

### Custom build hook

`packages/nsjail-bin-build/hatch_build.py`:

The hook runs `make` on the vendored nsjail source during wheel creation. If build tools are missing, it fails with a clear error listing what's needed.

```python
import os
import shutil
import subprocess
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class NsjailBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        build_data["pure_python"] = False
        build_data["infer_tag"] = True

        # Find nsjail source
        root = Path(self.root)
        nsjail_src = root / "_vendor" / "nsjail"
        if not nsjail_src.exists():
            # In sdist, source is bundled alongside the package
            nsjail_src = root / "nsjail_src"

        if not nsjail_src.exists():
            raise RuntimeError(
                "nsjail source not found. This package requires the vendored "
                "nsjail source to build. Try: pip install nsjail-python "
                "(uses pre-built binary instead)."
            )

        # Check for required tools
        for tool in ["make", "g++", "protoc", "bison", "flex", "pkg-config"]:
            if not shutil.which(tool):
                raise RuntimeError(
                    f"Required build tool '{tool}' not found.\n"
                    f"Install build dependencies:\n"
                    f"  apt-get install gcc g++ make protobuf-compiler "
                    f"libprotobuf-dev libnl-route-3-dev libcap-dev "
                    f"bison flex pkg-config autoconf libtool\n"
                    f"Or use the pre-built binary: pip install nsjail-python"
                )

        # Build nsjail
        env = os.environ.copy()
        result = subprocess.run(
            ["make", f"-j{os.cpu_count() or 1}"],
            cwd=nsjail_src,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"nsjail build failed:\n{result.stderr}\n\n"
                f"Try: pip install nsjail-python (uses pre-built binary)"
            )

        # Copy binary
        bin_dir = root / "src" / "nsjail_bin_build" / "_bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        built_binary = nsjail_src / "nsjail"
        shutil.copy2(built_binary, bin_dir / "nsjail")
        os.chmod(bin_dir / "nsjail", 0o755)
```

### sdist configuration

The sdist must include the vendored nsjail source. In `packages/nsjail-bin-build/pyproject.toml`:

```toml
[tool.hatch.build.targets.sdist]
include = [
    "src/",
    "nsjail_src/",
    "hatch_build.py",
]
```

A pre-build script copies `_vendor/nsjail/` to `packages/nsjail-bin-build/nsjail_src/` before building the sdist. This avoids git submodule issues in the sdist.

### System requirements

Documented in error messages and README:
- gcc/g++ (C++20)
- make, pkg-config, bison, flex, autoconf, libtool
- libprotobuf-dev, protobuf-compiler
- libnl-route-3-dev (libnl3)
- libcap-dev

## Part 3: Package Updates

### nsjail-python pyproject.toml

Add `nsjail-bin` as a default dependency (as originally designed):

```toml
dependencies = ["nsjail-bin"]

[project.optional-dependencies]
build = ["nsjail-bin-build"]
system = ["nsjail-bin-none"]
```

This means `pip install nsjail-python` pulls `nsjail-bin` (pre-built binary). Users override with `pip install nsjail-python[system]` or `pip install nsjail-python[build]`.

### Publish workflow updates

The existing `publish.yml` publishes `nsjail-python`. A new `build-binaries.yml` publishes `nsjail-bin` platform wheels. Both trigger on release.

`nsjail-bin-build` and `nsjail-bin-none` are published as pure sdist/wheel (no CI build needed) — they can be added to the existing publish workflow or have their own.

## Testing

- **nsjail-bin:** CI builds the binary, runs `nsjail --help` as smoke test, verifies it's statically linked
- **nsjail-bin-build:** Test in a Docker container with build deps installed. Verify `pip install` succeeds and the binary works.
- **Integration:** Test that `Runner()` finds and uses the bundled binary via `resolve_nsjail_path()`

## Scope Boundaries

**In scope:**
- GitHub Actions workflow for building static nsjail binaries (x86_64, aarch64)
- hatch build hook for nsjail-bin (platform-tagged wheels)
- hatch build hook for nsjail-bin-build (compile from source)
- sdist configuration for nsjail-bin-build
- Update nsjail-python to depend on nsjail-bin by default
- Publish workflows for companion packages

**Out of scope:**
- macOS/Windows builds (nsjail is Linux-only)
- Alpine/musl builds (can be added later)
- Seccomp policy helpers
- Cgroup stats recovery
