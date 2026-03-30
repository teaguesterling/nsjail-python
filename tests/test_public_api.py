def test_top_level_imports():
    from nsjail import (
        NsJailConfig,
        MountPt,
        IdMap,
        Exe,
        Mode,
        LogLevel,
        RLimitType,
        Jail,
        Runner,
        NsJailResult,
        sandbox,
    )
    assert NsJailConfig is not None
    assert Jail is not None
    assert Runner is not None


def test_serializer_imports():
    from nsjail.serializers import to_textproto, to_cli_args, to_file
    assert callable(to_textproto)
    assert callable(to_cli_args)
    assert callable(to_file)


def test_exception_imports():
    from nsjail.exceptions import NsjailError, UnsupportedCLIField, NsjailNotFound
    assert issubclass(UnsupportedCLIField, NsjailError)
