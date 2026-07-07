"""Tests for the jailed worker module.

The worker reads its input via pickle (parent -> jail, trusted) and writes its
result via a safe, non-executing JSON transport by default (jail -> parent,
untrusted). An opt-in "pickle" output mode exists for fully-trusted code.
"""

import json

from nsjail._worker import run_worker, _get_serializer


def _write_input(tmp_path, func, args, kwargs):
    with open(tmp_path / "input.pkl", "wb") as f:
        _get_serializer().dump((func, args, kwargs), f)


def _read_json_output(tmp_path):
    with open(tmp_path / "output.json") as f:
        return json.load(f)


class TestWorkerSuccess:
    def test_simple_function(self, tmp_path):
        def add(a, b):
            return a + b

        _write_input(tmp_path, add, (1, 2), {})
        run_worker(tmp_path)

        doc = _read_json_output(tmp_path)
        assert doc == {"ok": True, "value": 3}

    def test_function_with_kwargs(self, tmp_path):
        def greet(name, greeting="hello"):
            return f"{greeting} {name}"

        _write_input(tmp_path, greet, ("world",), {"greeting": "hi"})
        run_worker(tmp_path)

        doc = _read_json_output(tmp_path)
        assert doc == {"ok": True, "value": "hi world"}

    def test_function_returning_none(self, tmp_path):
        def noop():
            pass

        _write_input(tmp_path, noop, (), {})
        run_worker(tmp_path)

        doc = _read_json_output(tmp_path)
        assert doc == {"ok": True, "value": None}

    def test_unserializable_result_reported_not_crashed(self, tmp_path):
        def make_obj():
            return object()  # not JSON-serializable

        _write_input(tmp_path, make_obj, (), {})
        run_worker(tmp_path)

        doc = _read_json_output(tmp_path)
        assert doc["ok"] is False
        assert doc["error"]["type"] == "UnserializableResult"
        assert "unsafe_pickle_output" in doc["error"]["message"]


class TestWorkerErrors:
    def test_function_raises(self, tmp_path):
        def failing():
            raise ValueError("bad input")

        _write_input(tmp_path, failing, (), {})
        run_worker(tmp_path)

        doc = _read_json_output(tmp_path)
        assert doc["ok"] is False
        assert doc["error"]["type"] == "ValueError"
        assert "bad input" in doc["error"]["message"]

    def test_function_raises_custom_exception(self, tmp_path):
        class CustomError(Exception):
            pass

        def failing():
            raise CustomError("custom")

        _write_input(tmp_path, failing, (), {})
        run_worker(tmp_path)

        doc = _read_json_output(tmp_path)
        assert doc["ok"] is False
        assert doc["error"]["type"] == "CustomError"
        assert "custom" in doc["error"]["message"]


class TestWorkerUnsafePickleMode:
    def test_pickle_output_roundtrips(self, tmp_path):
        def add(a, b):
            return a + b

        _write_input(tmp_path, add, (2, 3), {})
        run_worker(tmp_path, output_format="pickle")

        with open(tmp_path / "output.pkl", "rb") as f:
            is_error, result = _get_serializer().load(f)

        assert is_error is False
        assert result == 5
