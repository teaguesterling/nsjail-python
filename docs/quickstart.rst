Quick Start
===========

Installation
-----------

.. code-block:: bash

   # Core library (expects nsjail on PATH)
   pip install nsjail-python

   # Include pre-built nsjail binary (Linux x86_64/aarch64)
   pip install nsjail-python[binary]

   # Build nsjail from source during install
   pip install nsjail-python[build]

   # Enable protobuf validation
   pip install nsjail-python[proto]

Three API Levels
----------------

**Low-level: Direct dataclass construction**

.. code-block:: python

   from nsjail import NsJailConfig, MountPt, Exe

   cfg = NsJailConfig(
       hostname="sandbox",
       time_limit=30,
       mount=[MountPt(src="/", dst="/", is_bind=True, rw=False)],
       exec_bin=Exe(path="/bin/sh", arg=["-c", "echo hello"]),
   )

**Mid-level: Presets**

.. code-block:: python

   from nsjail import sandbox

   cfg = sandbox(
       command=["python", "script.py"],
       memory_mb=512,
       timeout_sec=60,
       writable_dirs=["/workspace", "/tmp"],
   )

**High-level: Fluent builder**

.. code-block:: python

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

Serialization
-------------

.. code-block:: python

   from nsjail.serializers import to_textproto, to_cli_args, to_file

   # Protobuf text format (for --config flag)
   print(to_textproto(cfg))

   # CLI arguments
   args = to_cli_args(cfg, on_unsupported="skip")

   # Write to file
   to_file(cfg, "sandbox.cfg")

Running nsjail
--------------

**Sync execution:**

.. code-block:: python

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

**Async execution:**

.. code-block:: python

   result = await runner.async_run(extra_args=["tests/unit/"])

**Direct from builder:**

.. code-block:: python

   result = (
       Jail()
       .sh("echo hello")
       .timeout(10)
       .run()  # Creates a default Runner
   )

Mount Helpers
-------------

Ergonomic functions for common filesystem patterns:

.. code-block:: python

   from nsjail import (
       Jail, system_libs, dev_minimal, python_env,
       bind_tree, tmpfs_mount, overlay_mount,
   )

   cfg = (
       Jail()
       .sh("python script.py")
       .readonly_root()
       .mounts(system_libs())       # /lib, /usr/lib, /usr/bin, etc.
       .mounts(dev_minimal())       # /dev/null, /dev/zero, /dev/urandom
       .mounts(python_env())        # Current Python installation
       .mounts(tmpfs_mount("/tmp", size="64M"))
       .writable("/workspace")
       .build()
   )

**Overlay filesystem (copy-on-write):**

.. code-block:: python

   from nsjail import overlay_mount

   cfg = (
       Jail()
       .sh("make build")
       .mounts(overlay_mount(
           lower="/workspace",           # read-only base
           upper="/tmp/overlay/upper",   # writable layer
           work="/tmp/overlay/work",     # overlay workdir
           dst="/workspace",
       ))
       .build()
   )

Seccomp Policies
----------------

Build seccomp policies in Python instead of writing raw Kafel:

.. code-block:: python

   from nsjail import Jail, SeccompPolicy, MINIMAL

   # Use a preset
   cfg = Jail().sh("echo hi").seccomp(MINIMAL).build()

   # Or build a custom policy
   policy = (
       SeccompPolicy("custom")
       .allow("read", "write", "close", "exit_group")
       .deny("execve", "fork")
       .default_kill()
   )
   cfg = Jail().sh("echo hi").seccomp(policy).build()

**Available presets:** ``MINIMAL``, ``DEFAULT_LOG``, ``READONLY``

Cgroup Stats
------------

Capture resource usage during sandbox execution:

.. code-block:: python

   from nsjail import Runner

   runner = Runner(
       base_config=cfg,
       collect_cgroup_stats=True,
   )
   result = runner.run()

   if result.cgroup_stats:
       print(f"Peak memory: {result.cgroup_stats.memory_peak_bytes}")
       print(f"CPU time: {result.cgroup_stats.cpu_usage_ns}ns")
       print(f"Processes: {result.cgroup_stats.pids_current}")
