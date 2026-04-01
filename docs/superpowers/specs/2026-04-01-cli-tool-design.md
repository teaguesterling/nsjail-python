# CLI Tool Design Spec

**Date:** 2026-04-01
**Status:** Draft
**Scope:** `nsjail-py` command-line tool with run, config, and call subcommands

## Context

nsjail-python has a rich Python API but no command-line interface. A CLI makes the package accessible from shell scripts, CI pipelines, and for users who don't want to write Python. The entry point is `nsjail-py` (registered as a console script) with `python -m nsjail` as a fallback.

## Entry Points

```toml
[project.scripts]
nsjail-py = "nsjail.cli:main"
```

Also: `src/nsjail/__main__.py` imports and calls `main()` for `python -m nsjail` support.

## Subcommands

### `nsjail-py run` — Run a command in a sandbox

```bash
nsjail-py run echo hello
nsjail-py run --memory 512M --timeout 30 --no-network -- python script.py
nsjail-py run --readonly-root --writable /workspace -- make build
nsjail-py run --seccomp minimal -- ./untrusted
```

Builds an NsJailConfig from flags, runs via Runner, prints stdout/stderr, exits with the sandboxed process's exit code.

### `nsjail-py config` — Generate a config file

```bash
nsjail-py config --memory 512M --readonly-root -o sandbox.cfg
nsjail-py config --memory 1G --timeout 60 --no-network
```

Builds an NsJailConfig from flags, serializes to textproto, writes to file (`-o`) or stdout. Does not run nsjail.

### `nsjail-py call` — Run a Python function

```bash
nsjail-py call mymodule:my_function
nsjail-py call mymodule:func --timeout 30 --memory 512M
```

Imports the function from `module:name` notation, calls it via `jail_call()`, prints the return value. Useful for sandboxed one-off tasks.

## Shared Flags

All subcommands accept these flags:

| Flag | Short | Type | Maps to |
|---|---|---|---|
| `--memory SIZE` | `-m` | string (512M, 1G) | `memory_mb` |
| `--timeout SECS` | `-t` | int | `timeout_sec` |
| `--cpu MS` | | int | `cpu_ms_per_sec` |
| `--pids MAX` | | int | `pids_max` |
| `--no-network` | | flag | `clone_newnet=True` |
| `--network` | | flag | `clone_newnet=False` |
| `--readonly-root` | | flag | `apply_readonly_root()` |
| `--writable PATH` | `-w` | repeatable | writable dirs |
| `--mount SRC:DST` | | repeatable | bind mounts (readonly) |
| `--mount-rw SRC:DST` | | repeatable | bind mounts (read-write) |
| `--tmpfs PATH[:SIZE]` | | repeatable | tmpfs mounts |
| `--env KEY=VAL` | `-e` | repeatable | environment vars |
| `--cwd PATH` | | string | working directory |
| `--hostname NAME` | | string | sandbox hostname |
| `--seccomp PRESET` | | choice | MINIMAL, READONLY, DEFAULT_LOG |
| `--nsjail-path PATH` | | string | nsjail binary location |

### Size parsing

`--memory` accepts human-readable sizes: `512M`, `1G`, `256m`, `2g`. Parsed to megabytes.

### `run`-specific flags

| Flag | Type | Purpose |
|---|---|---|
| `--quiet` / `-q` | flag | Suppress nsjail's own stderr output |
| `--keep-config` | flag | Don't delete the temp config file |

### `config`-specific flags

| Flag | Type | Purpose |
|---|---|---|
| `-o FILE` / `--output FILE` | path | Write config to file (default: stdout) |
| `--format` | choice | `textproto` (default) or `cli` |

### `call`-specific flags

| Flag | Type | Purpose |
|---|---|---|
| `--json` | flag | Print return value as JSON |

## Module Structure

```
src/nsjail/
    cli.py           # argparse setup, subcommand handlers
    __main__.py      # python -m nsjail support
```

`cli.py` is a single file. Each subcommand is a function:
- `cmd_run(args)` — builds config, runs via Runner, exits with result code
- `cmd_config(args)` — builds config, serializes, outputs
- `cmd_call(args)` — imports function, calls via jail_call, prints result

A shared `build_config_from_args(args)` function translates parsed arguments into an NsJailConfig.

## Exit Codes

- `nsjail-py run`: exits with the sandboxed process's exit code
- `nsjail-py config`: exits 0 on success, 1 on error
- `nsjail-py call`: exits 0 if function succeeds, 1 if it raises

## Testing

- Unit tests: argument parsing, size parsing, config building from args
- Integration tests (mocked Runner): verify correct config is built and passed to Runner
- No real nsjail needed for CLI tests

## Scope Boundaries

**In scope:**
- `nsjail-py` console script entry point
- `python -m nsjail` support
- Three subcommands: run, config, call
- Shared flag parsing with human-readable sizes
- textproto and CLI output formats for config subcommand

**Out of scope:**
- Interactive mode / REPL
- Config file input (loading existing .cfg files)
- Shell completion scripts
- Daemon mode
