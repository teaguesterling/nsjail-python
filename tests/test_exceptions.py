from nsjail.exceptions import (
    NsjailError,
    UnsupportedCLIField,
    NsjailNotFound,
    JailedExecutionError,
)


def test_nsjail_error_is_base_exception():
    assert issubclass(NsjailError, Exception)


def test_unsupported_cli_field_contains_field_name():
    err = UnsupportedCLIField("src_content")
    assert "src_content" in str(err)
    assert isinstance(err, NsjailError)


def test_nsjail_not_found_contains_install_hint():
    err = NsjailNotFound()
    msg = str(err)
    assert "nsjail" in msg.lower()
    assert isinstance(err, NsjailError)


def test_jailed_execution_error_is_nsjail_error():
    assert issubclass(JailedExecutionError, NsjailError)


def test_jailed_execution_error_message():
    err = JailedExecutionError("function failed")
    assert "function failed" in str(err)


def test_jailed_execution_error_with_traceback():
    err = JailedExecutionError("failed", original_traceback="Traceback...")
    assert err.original_traceback == "Traceback..."
