from enum import IntEnum

from nsjail.enums import Mode, LogLevel, RLimitType


def test_mode_values():
    assert Mode.LISTEN == 0
    assert Mode.ONCE == 1
    assert Mode.RERUN == 2
    assert Mode.EXECVE == 3


def test_log_level_values():
    assert LogLevel.DEBUG == 0
    assert LogLevel.INFO == 1
    assert LogLevel.WARNING == 2
    assert LogLevel.ERROR == 3
    assert LogLevel.FATAL == 4


def test_rlimit_type_values():
    assert RLimitType.VALUE == 0
    assert RLimitType.SOFT == 1
    assert RLimitType.HARD == 2
    assert RLimitType.INF == 3


def test_all_are_int_enums():
    assert issubclass(Mode, IntEnum)
    assert issubclass(LogLevel, IntEnum)
    assert issubclass(RLimitType, IntEnum)
