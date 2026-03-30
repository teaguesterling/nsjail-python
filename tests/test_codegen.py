from _codegen.generate import (
    parse_proto,
    emit_enums,
    emit_config,
    emit_field_meta,
    ProtoEnum,
    ProtoMessage,
)
from _codegen.cli_flags import CLI_FLAGS
from pathlib import Path
import pytest


SAMPLE_PROTO = """
syntax = "proto2";
package nsjail;

enum Mode {
    LISTEN = 0;
    ONCE = 1;
    RERUN = 2;
    EXECVE = 3;
}

enum LogLevel {
    DEBUG = 0;
    INFO = 1;
    WARNING = 2;
    ERROR = 3;
    FATAL = 4;
}

message NsJailConfig {
    enum RLimit {
        VALUE = 0;
        SOFT = 1;
        HARD = 2;
        INF = 3;
    }
    optional string hostname = 8 [default = "NSJAIL"];
    optional uint32 time_limit = 14 [default = 600];
    optional bool clone_newnet = 60 [default = true];
    repeated string envar = 19;
    optional RLimit rlimit_as_type = 36 [default = VALUE];
}
"""


class TestParseProto:
    def test_parses_top_level_enums(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        assert len(enums) == 2
        assert enums[0].name == "Mode"

    def test_parses_nested_enum(self):
        items = parse_proto(SAMPLE_PROTO)
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        cfg = messages[0]
        assert len(cfg.enums) == 1
        assert cfg.enums[0].name == "RLimit"

    def test_parses_fields_with_defaults(self):
        items = parse_proto(SAMPLE_PROTO)
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        cfg = messages[0]
        hostname = next(f for f in cfg.fields if f.name == "hostname")
        assert hostname.default == '"NSJAIL"'

    def test_parses_repeated_fields(self):
        items = parse_proto(SAMPLE_PROTO)
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        cfg = messages[0]
        envar = next(f for f in cfg.fields if f.name == "envar")
        assert envar.label == "repeated"


class TestEmitEnums:
    def test_emit_top_level_enums(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_enums(enums, messages)
        assert "class Mode(IntEnum):" in output
        assert "LISTEN = 0" in output
        assert "class LogLevel(IntEnum):" in output
        assert "class RLimitType(IntEnum):" in output
        assert "VALUE = 0" in output


class TestEmitConfig:
    def test_emit_produces_valid_python(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_config(messages, enums)
        compile(output, "<test>", "exec")

    def test_emit_has_dataclass(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_config(messages, enums)
        assert "@dataclass" in output
        assert "class NsJailConfig:" in output

    def test_emit_has_correct_defaults(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_config(messages, enums)
        assert 'hostname: str = "NSJAIL"' in output
        assert "time_limit: int = 600" in output
        assert "clone_newnet: bool = True" in output

    def test_emit_repeated_field(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        output = emit_config(messages, enums)
        assert "envar: list[str] = field(default_factory=list)" in output


class TestEmitFieldMeta:
    def test_emit_produces_valid_python(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        emit_config(messages, enums)
        output = emit_field_meta(messages, CLI_FLAGS, top_enums=enums)
        compile(output, "<test>", "exec")

    def test_emit_has_hostname_entry(self):
        items = parse_proto(SAMPLE_PROTO)
        enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        emit_config(messages, enums)
        output = emit_field_meta(messages, CLI_FLAGS, top_enums=enums)
        assert '"NsJailConfig", "hostname"' in output
        assert '"NSJAIL"' in output


class TestFullGeneration:
    def test_generate_against_vendored_proto(self):
        proto_path = Path("_vendor/nsjail/config.proto")
        if not proto_path.exists():
            pytest.skip("Vendored config.proto not available")
        text = proto_path.read_text()
        items = parse_proto(text)
        top_enums = [i for i in items if isinstance(i, ProtoEnum)]
        messages = [i for i in items if isinstance(i, ProtoMessage)]
        enums_out = emit_enums(top_enums, messages)
        compile(enums_out, "enums.py", "exec")
        config_out = emit_config(messages, top_enums)
        compile(config_out, "config.py", "exec")
        meta_out = emit_field_meta(messages, CLI_FLAGS, top_enums=top_enums)
        compile(meta_out, "_field_meta.py", "exec")
