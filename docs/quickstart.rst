Quick Start
===========

Installation
-----------

.. code-block:: bash

   pip install nsjail-python

The default install includes a pre-built nsjail binary. For other options:

.. code-block:: bash

   pip install nsjail-python[system]  # Use system-provided nsjail
   pip install nsjail-python[build]   # Build nsjail from source
   pip install nsjail-python[proto]   # Enable protobuf validation

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
