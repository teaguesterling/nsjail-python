from _codegen.generate import (
    parse_proto,
    ProtoEnum,
    ProtoMessage,
)


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


from _codegen.generate import emit_enums


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
