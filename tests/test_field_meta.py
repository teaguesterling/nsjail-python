from nsjail._field_meta import FieldMeta, FIELD_REGISTRY


def test_field_meta_has_required_attrs():
    meta = FieldMeta(
        number=1,
        proto_type="string",
        default=None,
        cli_flag="--name",
        cli_supported=True,
        is_repeated=False,
        is_message=False,
    )
    assert meta.number == 1
    assert meta.proto_type == "string"
    assert meta.cli_flag == "--name"


def test_registry_has_nsjailconfig_hostname():
    meta = FIELD_REGISTRY[("NsJailConfig", "hostname")]
    assert meta.proto_type == "string"
    assert meta.default == "NSJAIL"
    assert meta.cli_supported is True


def test_registry_has_mount_dst():
    meta = FIELD_REGISTRY[("MountPt", "dst")]
    assert meta.proto_type == "string"
    assert meta.default is None


def test_registry_has_nsjailconfig_mount():
    meta = FIELD_REGISTRY[("NsJailConfig", "mount")]
    assert meta.is_repeated is True
    assert meta.is_message is True


def test_registry_has_nsjailconfig_clone_newnet():
    meta = FIELD_REGISTRY[("NsJailConfig", "clone_newnet")]
    assert meta.proto_type == "bool"
    assert meta.default is True


def test_unsupported_cli_field():
    meta = FIELD_REGISTRY[("MountPt", "src_content")]
    assert meta.cli_supported is False


def test_all_nsjailconfig_fields_in_registry():
    from dataclasses import fields as dc_fields
    from nsjail.config import NsJailConfig

    for f in dc_fields(NsJailConfig):
        key = ("NsJailConfig", f.name)
        assert key in FIELD_REGISTRY, f"Missing registry entry for {key}"
