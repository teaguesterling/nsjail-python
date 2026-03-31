API Reference
=============

Core Model
----------

.. autoclass:: nsjail.NsJailConfig
   :members:

.. autoclass:: nsjail.MountPt
   :members:

.. autoclass:: nsjail.IdMap
   :members:

.. autoclass:: nsjail.Exe
   :members:

Enums
-----

.. autoclass:: nsjail.Mode
   :members:

.. autoclass:: nsjail.LogLevel
   :members:

.. autoclass:: nsjail.RLimitType
   :members:

Builder
-------

.. autoclass:: nsjail.Jail
   :members:

Presets
-------

.. automodule:: nsjail.presets
   :members:

Runner
------

.. autoclass:: nsjail.Runner
   :members:

.. autoclass:: nsjail.NsJailResult
   :members:

Serializers
-----------

.. autofunction:: nsjail.serializers.to_textproto

.. autofunction:: nsjail.serializers.to_cli_args

.. autofunction:: nsjail.serializers.to_file

Seccomp
-------

.. autoclass:: nsjail.SeccompPolicy
   :members:

.. autodata:: nsjail.MINIMAL
.. autodata:: nsjail.DEFAULT_LOG
.. autodata:: nsjail.READONLY

Cgroup Stats
------------

.. autoclass:: nsjail.CgroupStats
   :members:

.. autoclass:: nsjail.cgroup.CgroupMonitor
   :members:

Mount Helpers
-------------

.. autofunction:: nsjail.bind_tree

.. autofunction:: nsjail.bind_paths

.. autofunction:: nsjail.overlay_mount

.. autofunction:: nsjail.system_libs

.. autofunction:: nsjail.dev_minimal

.. autofunction:: nsjail.python_env

.. autofunction:: nsjail.proc_mount

.. autofunction:: nsjail.tmpfs_mount

Exceptions
----------

.. autoclass:: nsjail.exceptions.NsjailError
.. autoclass:: nsjail.exceptions.UnsupportedCLIField
.. autoclass:: nsjail.exceptions.NsjailNotFound
