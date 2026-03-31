nsjail-python
=============

Python wrapper for Google's nsjail sandboxing tool.

**Features:**

- **120+ field config model** mirroring nsjail's config.proto
- **Three API levels:** dataclasses, presets, fluent builder
- **Serializers:** protobuf text format, CLI args, compiled protobuf
- **Runner** with sync/async execution, config merging, cgroup stats
- **Seccomp policy builder** with presets (MINIMAL, READONLY, DEFAULT_LOG)
- **Mount helpers** for system libs, /dev, Python env, overlay, tmpfs
- **Companion packages** for bundled nsjail binaries

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
