"""Tests for jail_call execution engine."""

import pytest
from pathlib import Path
from unittest.mock import patch

from nsjail._worker import _get_serializer
from nsjail.call import _build_jail_config, _serialize_input, _deserialize_output, jailed, JailContext
from nsjail.config import NsJailConfig
from nsjail.exceptions import JailedExecutionError


class TestSerializeInput:
    def test_serialize_and_read_back(self, tmp_path):
        pkl = _get_serializer()

        def add(a, b):
            return a + b

        input_path = _serialize_input(tmp_path, add, (1, 2), {"extra": True})
        assert input_path.exists()

        with open(input_path, "rb") as f:
            func, args, kwargs = pkl.load(f)

        assert func(1, 2) == 3
        assert args == (1, 2)
        assert kwargs == {"extra": True}

    def test_serialize_with_none_kwargs(self, tmp_path):
        pkl = _get_serializer()

        def noop():
            pass

        input_path = _serialize_input(tmp_path, noop, (), None)

        with open(input_path, "rb") as f:
            func, args, kwargs = pkl.load(f)

        assert kwargs == {}


class TestDeserializeOutput:
    def test_success_result(self, tmp_path):
        pkl = _get_serializer()
        output_path = tmp_path / "output.pkl"
        with open(output_path, "wb") as f:
            pkl.dump((False, 42), f)

        result = _deserialize_output(output_path)
        assert result == 42

    def test_error_result_reraises(self, tmp_path):
        pkl = _get_serializer()
        output_path = tmp_path / "output.pkl"
        with open(output_path, "wb") as f:
            pkl.dump((True, ValueError("bad")), f)

        with pytest.raises(ValueError, match="bad"):
            _deserialize_output(output_path)

    def test_missing_output_raises(self, tmp_path):
        output_path = tmp_path / "output.pkl"

        with pytest.raises(JailedExecutionError, match="output"):
            _deserialize_output(output_path)


class TestBuildJailConfig:
    def test_basic_config(self):
        cfg = _build_jail_config(
            io_dir="/tmp/test_io",
            timeout_sec=30,
        )
        assert isinstance(cfg, NsJailConfig)
        assert cfg.time_limit == 30
        assert cfg.exec_bin is not None
        assert "-m" in cfg.exec_bin.arg
        assert "nsjail._worker" in cfg.exec_bin.arg

    def test_memory_limit(self):
        cfg = _build_jail_config(
            io_dir="/tmp/test_io",
            timeout_sec=30,
            memory_mb=512,
        )
        assert cfg.cgroup_mem_max == 512 * 1024 * 1024

    def test_no_network_default(self):
        cfg = _build_jail_config(io_dir="/tmp/test_io", timeout_sec=30)
        assert cfg.clone_newnet is True

    def test_network_enabled(self):
        cfg = _build_jail_config(
            io_dir="/tmp/test_io",
            timeout_sec=30,
            network=True,
        )
        assert cfg.clone_newnet is False

    def test_io_dir_in_mounts(self):
        cfg = _build_jail_config(io_dir="/tmp/test_io", timeout_sec=30)
        io_mounts = [m for m in cfg.mount if m.dst == "/tmp/test_io"]
        assert len(io_mounts) >= 1
        assert io_mounts[0].rw is True


class TestJailedDecorator:
    def test_decorator_wraps_function(self):
        @jailed(timeout_sec=10)
        def add(a, b):
            return a + b

        assert callable(add)
        assert add.__name__ == "add"

    def test_decorator_calls_jail_call(self):
        with patch("nsjail.call.jail_call", return_value=42) as mock:
            @jailed(timeout_sec=10, memory_mb=256)
            def compute(x):
                return x * 2

            result = compute(21)

        assert result == 42
        mock.assert_called_once()
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs["timeout_sec"] == 10
        assert call_kwargs["memory_mb"] == 256

    def test_decorator_passes_args_and_kwargs(self):
        with patch("nsjail.call.jail_call", return_value="ok") as mock:
            @jailed(timeout_sec=10)
            def greet(name, greeting="hello"):
                return f"{greeting} {name}"

            greet("world", greeting="hi")

        call_args = mock.call_args
        assert call_args[0][1] == ("world",)
        assert call_args[0][2] == {"greeting": "hi"}


class TestJailContext:
    def test_context_manager_creates_io_dir(self):
        with JailContext(timeout_sec=10) as jail:
            assert jail._io_dir is not None
            assert jail._io_dir.exists()

    def test_context_manager_cleans_up(self):
        with JailContext(timeout_sec=10) as jail:
            io_dir = jail._io_dir
        assert not io_dir.exists()

    def test_call_delegates_to_jail_call(self):
        with patch("nsjail.call.jail_call", return_value=42) as mock:
            with JailContext(timeout_sec=10, memory_mb=256) as jail:
                result = jail.call(lambda x: x, 21)

        assert result == 42
        mock.assert_called_once()
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs["timeout_sec"] == 10
        assert call_kwargs["memory_mb"] == 256
        assert call_kwargs["_io_dir"] is not None

    def test_multiple_calls_share_io_dir(self):
        with patch("nsjail.call.jail_call", return_value=0) as mock:
            with JailContext(timeout_sec=10) as jail:
                jail.call(lambda: 1)
                jail.call(lambda: 2)

        calls = mock.call_args_list
        assert calls[0].kwargs["_io_dir"] == calls[1].kwargs["_io_dir"]
