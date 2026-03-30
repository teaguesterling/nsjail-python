import pytest
import logging

from nsjail.config import NsJailConfig, MountPt, IdMap, Exe
from nsjail.enums import Mode
from nsjail.exceptions import UnsupportedCLIField
from nsjail.serializers import to_cli_args


class TestCliScalars:
    def test_empty_config_returns_empty(self):
        cfg = NsJailConfig()
        args = to_cli_args(cfg, on_unsupported="skip")
        assert args == []

    def test_changed_string_field(self):
        cfg = NsJailConfig(hostname="sandbox")
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--hostname" in args
        idx = args.index("--hostname")
        assert args[idx + 1] == "sandbox"

    def test_changed_int_field(self):
        cfg = NsJailConfig(time_limit=30)
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--time_limit" in args
        idx = args.index("--time_limit")
        assert args[idx + 1] == "30"

    def test_bool_flag_true(self):
        cfg = NsJailConfig(keep_env=True)
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--keep_env" in args

    def test_default_values_not_emitted(self):
        cfg = NsJailConfig()
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--hostname" not in args
        assert "--time_limit" not in args

    def test_repeated_string_field(self):
        cfg = NsJailConfig(envar=["A=1", "B=2"])
        args = to_cli_args(cfg, on_unsupported="skip")
        assert args.count("--env") == 2


class TestCliUnsupported:
    def test_unsupported_field_raises_by_default(self):
        cfg = NsJailConfig(mount=[MountPt(src="/", dst="/", is_bind=True)])
        with pytest.raises(UnsupportedCLIField):
            to_cli_args(cfg, on_unsupported="raise")

    def test_unsupported_field_skip(self):
        cfg = NsJailConfig(mount=[MountPt(src="/", dst="/", is_bind=True)])
        args = to_cli_args(cfg, on_unsupported="skip")
        # mount has no direct CLI flag, should be skipped
        assert not any("mount" in a for a in args)

    def test_unsupported_field_warn(self, caplog):
        cfg = NsJailConfig(mount=[MountPt(src="/", dst="/", is_bind=True)])
        with caplog.at_level(logging.WARNING):
            args = to_cli_args(cfg, on_unsupported="warn")
        assert "mount" in caplog.text.lower()
