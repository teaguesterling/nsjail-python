"""Security regression tests for the jail return path.

These guard the invariant that nothing the *jailed* (untrusted) process can
place on the return channel is able to cause code execution in the unjailed
parent. See GHSA-w6j4-3xhv-r968.

The payloads here are bounded and self-contained: the only side effect an
exploit would have is writing a canary file into a pytest ``tmp_path``. They
never touch the network or real user files.
"""

import json
import pickle

import pytest

from nsjail.call import _deserialize_output
from nsjail.config import Exe, MountPt, NsJailConfig
from nsjail.exceptions import JailedExecutionError, UnsupportedCLIField
from nsjail.runner import Runner


# --- Exploit primitive -------------------------------------------------------
# A module-level function + object so pickle can reference them by qualified
# name. On unpickling, ``__reduce__`` runs ``_write_canary`` in the parent.

def _write_canary(path: str) -> str:
    with open(path, "w") as f:
        f.write("SECRET-CANARY")
    return "pwned"


class _Exploit:
    def __init__(self, canary_path: str) -> None:
        self._canary_path = canary_path

    def __reduce__(self):
        return (_write_canary, (self._canary_path,))


def test_hostile_jail_output_does_not_execute_in_parent(tmp_path):
    """A hostile ``__reduce__`` payload on the return channel must be inert.

    Pre-fix, the parent ``pickle.load``s jail output and the canary appears.
    Post-fix, the parent uses a non-executing (JSON) transport, so the payload
    is rejected and the canary is never created.
    """
    canary = tmp_path / "SECRET-CANARY"
    output_path = tmp_path / "output.pkl"

    # The untrusted jail writes a pickle whose deserialization runs code.
    output_path.write_bytes(pickle.dumps((False, _Exploit(str(canary)))))

    # Reading the jail's output must never execute jail-controlled code. The
    # safe path may legitimately *reject* the bytes (raising) -- that is fine;
    # what must never happen is the side effect.
    try:
        _deserialize_output(output_path)
    except JailedExecutionError:
        pass  # safe path refuses to interpret the non-JSON payload

    assert not canary.exists(), (
        "SANDBOX ESCAPE: the parent executed a jail-controlled __reduce__ "
        "payload while reading the return channel"
    )


def test_safe_output_roundtrips_legit_result(tmp_path):
    """The safe transport still returns a legitimate jailed result."""
    output_path = tmp_path / "output.json"
    output_path.write_text(json.dumps({"ok": True, "value": {"answer": 42}}))

    assert _deserialize_output(output_path) == {"answer": 42}


def test_safe_output_reports_jailed_error(tmp_path):
    """A jailed exception is surfaced as JailedExecutionError, not re-executed."""
    output_path = tmp_path / "output.json"
    output_path.write_text(
        json.dumps(
            {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": "bad input",
                    "traceback": "Traceback ...",
                },
            }
        )
    )

    with pytest.raises(JailedExecutionError, match="ValueError"):
        _deserialize_output(output_path)


# --- CLI vs library parity: mounts ------------------------------------------

def test_cli_render_refuses_to_drop_mounts():
    """CLI and library entry points must agree on the effective jail config.

    The library (textproto) honors mounts; the CLI renderer cannot express
    them. Rather than silently dropping the isolation, the runner must refuse.
    """
    base = NsJailConfig(
        exec_bin=Exe(path="/bin/sh"),
        mount=[MountPt(src="/", dst="/", is_bind=True, rw=False)],
    )

    # Library / textproto path honors the mount.
    textproto_runner = Runner(
        base_config=base, nsjail_path="/usr/bin/nsjail", render_mode="textproto"
    )
    _, config_path, _ = textproto_runner._prepare_run(None, None, None)
    assert config_path is not None
    rendered = config_path.read_text()
    config_path.unlink(missing_ok=True)
    assert "mount" in rendered, "textproto path should honor the mount"

    # CLI path must refuse rather than silently drop the mount.
    cli_runner = Runner(
        base_config=base, nsjail_path="/usr/bin/nsjail", render_mode="cli"
    )
    with pytest.raises(UnsupportedCLIField):
        cli_runner._prepare_run(None, None, None)
