from nsjail.config import NsJailConfig, MountPt, IdMap, Exe
from nsjail.enums import Mode
from nsjail.serializers import to_textproto


class TestTextProtoScalars:
    def test_empty_config_emits_nothing(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert text.strip() == ""

    def test_changed_scalar_string(self):
        cfg = NsJailConfig(hostname="sandbox")
        text = to_textproto(cfg)
        assert 'hostname: "sandbox"' in text

    def test_unchanged_scalar_not_emitted(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert "hostname" not in text

    def test_changed_scalar_int(self):
        cfg = NsJailConfig(time_limit=30)
        text = to_textproto(cfg)
        assert "time_limit: 30" in text

    def test_changed_bool_false_to_true(self):
        cfg = NsJailConfig(clone_newtime=True)
        text = to_textproto(cfg)
        assert "clone_newtime: true" in text

    def test_changed_bool_true_to_false(self):
        cfg = NsJailConfig(clone_newnet=False)
        text = to_textproto(cfg)
        assert "clone_newnet: false" in text

    def test_none_field_not_emitted(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert "log_file" not in text

    def test_none_field_set_to_value(self):
        cfg = NsJailConfig(log_file="/var/log/nsjail.log")
        text = to_textproto(cfg)
        assert 'log_file: "/var/log/nsjail.log"' in text

    def test_enum_field(self):
        cfg = NsJailConfig(mode=Mode.LISTEN)
        text = to_textproto(cfg)
        assert "mode: LISTEN" in text


class TestTextProtoRepeated:
    def test_repeated_string(self):
        cfg = NsJailConfig(envar=["HOME=/home/user", "PATH=/usr/bin"])
        text = to_textproto(cfg)
        assert 'envar: "HOME=/home/user"' in text
        assert 'envar: "PATH=/usr/bin"' in text

    def test_empty_repeated_not_emitted(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert "envar" not in text


class TestTextProtoMessage:
    def test_mount_message(self):
        cfg = NsJailConfig(mount=[
            MountPt(src="/", dst="/", is_bind=True, rw=False),
        ])
        text = to_textproto(cfg)
        assert "mount {" in text
        assert 'src: "/"' in text
        assert 'dst: "/"' in text
        assert "is_bind: true" in text

    def test_exec_bin_message(self):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo hi"]),
        )
        text = to_textproto(cfg)
        assert "exec_bin {" in text
        assert 'path: "/bin/sh"' in text
        assert 'arg: "-c"' in text
        assert 'arg: "echo hi"' in text

    def test_nested_message_none_not_emitted(self):
        cfg = NsJailConfig()
        text = to_textproto(cfg)
        assert "exec_bin" not in text


class TestTextProtoRoundTrip:
    def test_complex_config(self):
        cfg = NsJailConfig(
            hostname="mybox",
            time_limit=60,
            clone_newnet=True,
            clone_newtime=True,
            mount=[
                MountPt(src="/", dst="/", is_bind=True),
                MountPt(dst="/tmp", fstype="tmpfs", rw=True, options="size=64M"),
            ],
            uidmap=[IdMap(inside_id="0", outside_id="1000")],
            envar=["HOME=/home/user"],
            exec_bin=Exe(path="/usr/bin/python3", arg=["script.py"]),
        )
        text = to_textproto(cfg)
        assert text.count("mount {") == 2
        assert text.count("uidmap {") == 1
        assert text.count("exec_bin {") == 1
        assert text.count("{") == text.count("}")
