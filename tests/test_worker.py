"""Tests for the jailed worker module.

Security note: Uses pickle for serialization between parent and child
processes within the same trust domain (like multiprocessing).
"""

from pathlib import Path

from nsjail._worker import run_worker, _get_serializer


class TestWorkerSuccess:
    def test_simple_function(self, tmp_path):
        input_path = tmp_path / "input.pkl"
        output_path = tmp_path / "output.pkl"

        def add(a, b):
            return a + b

        with open(input_path, "wb") as f:
            _get_serializer().dump((add, (1, 2), {}), f)

        run_worker(tmp_path)

        with open(output_path, "rb") as f:
            is_error, result = _get_serializer().load(f)

        assert is_error is False
        assert result == 3

    def test_function_with_kwargs(self, tmp_path):
        input_path = tmp_path / "input.pkl"
        output_path = tmp_path / "output.pkl"

        def greet(name, greeting="hello"):
            return f"{greeting} {name}"

        with open(input_path, "wb") as f:
            _get_serializer().dump((greet, ("world",), {"greeting": "hi"}), f)

        run_worker(tmp_path)

        with open(output_path, "rb") as f:
            is_error, result = _get_serializer().load(f)

        assert is_error is False
        assert result == "hi world"

    def test_function_returning_none(self, tmp_path):
        input_path = tmp_path / "input.pkl"
        output_path = tmp_path / "output.pkl"

        def noop():
            pass

        with open(input_path, "wb") as f:
            _get_serializer().dump((noop, (), {}), f)

        run_worker(tmp_path)

        with open(output_path, "rb") as f:
            is_error, result = _get_serializer().load(f)

        assert is_error is False
        assert result is None


class TestWorkerErrors:
    def test_function_raises(self, tmp_path):
        input_path = tmp_path / "input.pkl"
        output_path = tmp_path / "output.pkl"

        def failing():
            raise ValueError("bad input")

        with open(input_path, "wb") as f:
            _get_serializer().dump((failing, (), {}), f)

        run_worker(tmp_path)

        with open(output_path, "rb") as f:
            is_error, result = _get_serializer().load(f)

        assert is_error is True
        assert isinstance(result, ValueError)
        assert "bad input" in str(result)

    def test_function_raises_custom_exception(self, tmp_path):
        input_path = tmp_path / "input.pkl"
        output_path = tmp_path / "output.pkl"

        class CustomError(Exception):
            pass

        def failing():
            raise CustomError("custom")

        with open(input_path, "wb") as f:
            _get_serializer().dump((failing, (), {}), f)

        run_worker(tmp_path)

        with open(output_path, "rb") as f:
            is_error, result = _get_serializer().load(f)

        assert is_error is True
        assert isinstance(result, CustomError)
