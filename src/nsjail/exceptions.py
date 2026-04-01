"""Exception types for nsjail-python."""


class NsjailError(Exception):
    """Base exception for all nsjail-python errors."""


class UnsupportedCLIField(NsjailError):
    """Raised when a config field has no CLI flag equivalent."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(
            f"Config field {field_name!r} has no CLI flag equivalent. "
            f"Use textproto rendering instead, or pass on_unsupported='skip'."
        )


class NsjailNotFound(NsjailError):
    """Raised when the nsjail binary cannot be found."""

    def __init__(self) -> None:
        super().__init__(
            "nsjail binary not found. Install it via:\n"
            "  pip install nsjail-python          # includes pre-built binary\n"
            "  pip install nsjail-python[build]    # build from source\n"
            "  apt-get install nsjail              # system package\n"
            "Or specify the path: Runner(nsjail_path='/path/to/nsjail')"
        )


class JailedExecutionError(NsjailError):
    """Raised when a jailed function execution fails."""

    def __init__(self, message: str, original_traceback: str | None = None) -> None:
        self.original_traceback = original_traceback
        super().__init__(message)
