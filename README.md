# nsjail-python

Python wrapper for Google's nsjail sandboxing tool

[![PyPI](https://img.shields.io/pypi/v/nsjail-python)](https://pypi.org/project/nsjail-python/)
[![Python Version](https://img.shields.io/pypi/pyversions/nsjail-python)](https://pypi.org/project/nsjail-python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
# Core library only (expects nsjail on PATH or installed separately)
pip install nsjail-python

# Include pre-built nsjail binary (Linux x86_64/aarch64)
pip install nsjail-python[binary]

# Build nsjail from source during install (needs gcc, make, protoc, etc.)
pip install nsjail-python[build]

# Add protobuf validation support
pip install nsjail-python[proto]
```

## Quick Start

### Low-level: NsJailConfig dataclass

```python
from nsjail import NsJailConfig, MountPt, Exe

cfg = NsJailConfig(
    hostname="sandbox",
    time_limit=30,
    mount=[MountPt(src="/", dst="/", is_bind=True, rw=False)],
    exec_bin=Exe(path="/bin/sh", arg=["-c", "echo hello"]),
)
```

### Mid-level: sandbox() preset

```python
from nsjail import sandbox

cfg = sandbox(
    command=["python", "script.py"],
    memory_mb=512,
    timeout_sec=60,
    writable_dirs=["/workspace", "/tmp"],
)
```

### High-level: Jail() fluent builder

```python
from nsjail import Jail

cfg = (
    Jail()
    .sh("pytest tests/ -v")
    .memory(512, "MB")
    .timeout(60)
    .readonly_root()
    .writable("/workspace")
    .writable("/tmp", tmpfs=True, size="64M")
    .no_network()
    .build()
)
```

## Serialization

```python
from nsjail.serializers import to_textproto, to_cli_args, to_file

# Protobuf text format (for --config flag)
print(to_textproto(cfg))

# CLI arguments
args = to_cli_args(cfg, on_unsupported="skip")

# Write to file
to_file(cfg, "sandbox.cfg")
```

## Running nsjail

```python
from nsjail import Runner, Jail

runner = Runner(
    base_config=Jail()
        .command("python", "-m", "pytest")
        .memory(512, "MB")
        .timeout(300)
        .readonly_root()
        .writable("/workspace")
        .build(),
)

result = runner.run(extra_args=["tests/unit/", "-x"])
print(result.returncode, result.stdout)
```

## Documentation

Full documentation is available at [nsjail-python.readthedocs.io](https://nsjail-python.readthedocs.io).

## License

MIT
