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

Exceptions
----------

.. autoclass:: nsjail.exceptions.NsjailError
.. autoclass:: nsjail.exceptions.UnsupportedCLIField
.. autoclass:: nsjail.exceptions.NsjailNotFound
