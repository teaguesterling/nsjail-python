import pytest

pytest.importorskip("google.protobuf")

from google.protobuf import text_format

from nsjail.config import NsJailConfig, MountPt, Exe, IdMap
from nsjail.serializers.protobuf import to_protobuf
from nsjail.serializers.textproto import to_textproto


class TestToProtobuf:
    def test_empty_config(self):
        cfg = NsJailConfig()
        msg = to_protobuf(cfg)
        assert msg is not None

    def test_simple_fields(self):
        cfg = NsJailConfig(hostname="sandbox", time_limit=30)
        msg = to_protobuf(cfg)
        assert msg.hostname == "sandbox"
        assert msg.time_limit == 30

    def test_mount(self):
        cfg = NsJailConfig(mount=[
            MountPt(src="/", dst="/", is_bind=True, rw=False),
        ])
        msg = to_protobuf(cfg)
        assert len(msg.mount) == 1
        assert msg.mount[0].src == "/"
        assert msg.mount[0].is_bind is True

    def test_exec_bin(self):
        cfg = NsJailConfig(exec_bin=Exe(path="/bin/sh", arg=["-c", "echo hi"]))
        msg = to_protobuf(cfg)
        assert msg.exec_bin.path == "/bin/sh"
        assert list(msg.exec_bin.arg) == ["-c", "echo hi"]

    def test_round_trip_matches_textproto(self):
        cfg = NsJailConfig(
            hostname="test",
            time_limit=60,
            envar=["A=1"],
            mount=[MountPt(src="/lib", dst="/lib", is_bind=True)],
            exec_bin=Exe(path="/bin/sh"),
        )
        our_text = to_textproto(cfg)
        msg = to_protobuf(cfg)
        from nsjail._proto import config_pb2
        msg_from_ours = config_pb2.NsJailConfig()
        text_format.Parse(our_text, msg_from_ours)
        assert msg_from_ours == msg
