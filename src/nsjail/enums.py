# GENERATED from nsjail config.proto — DO NOT EDIT
# Re-run: python -m _codegen.generate

from enum import IntEnum


class Mode(IntEnum):
    """nsjail execution mode."""
    LISTEN = 0
    ONCE = 1
    RERUN = 2
    EXECVE = 3


class LogLevel(IntEnum):
    """Log verbosity level."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    FATAL = 4


class RLimitType(IntEnum):
    """How to interpret an rlimit value."""
    VALUE = 0
    SOFT = 1
    HARD = 2
    INF = 3
