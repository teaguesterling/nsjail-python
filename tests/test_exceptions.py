from nsjail.exceptions import (
    NsjailError,
    UnsupportedCLIField,
    NsjailNotFound,
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
