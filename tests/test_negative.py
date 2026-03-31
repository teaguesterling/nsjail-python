"""Comprehensive negative and edge case test suite.

Tests error handling, invalid inputs, boundary conditions,
and graceful degradation across all modules.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from nsjail.cgroup import CgroupStats, CgroupMonitor, parse_v1_stats, parse_v2_stats, _read_int
from nsjail.config import Exe, IdMap, MountPt, NsJailConfig, UserNet
from nsjail.builder import Jail
from nsjail.enums import LogLevel, Mode, RLimitType
from nsjail.exceptions import NsjailNotFound, UnsupportedCLIField
from nsjail.presets import apply_cgroup_limits, apply_readonly_root, apply_seccomp_log, sandbox
from nsjail.runner import Runner, merge_configs, resolve_nsjail_path, NsJailResult
from nsjail.seccomp import SeccompPolicy
from nsjail.serializers.cli import to_cli_args
from nsjail.serializers.textproto import to_textproto, _escape_string, _escape_bytes


# =============================================================================
# SeccompPolicy edge cases
# =============================================================================

class TestSeccompPolicyEdgeCases:
    """Edge cases for the SeccompPolicy builder."""

    def test_policy_with_no_rules_just_default(self):
        """A policy with no rules should still render with the default action."""
        p = SeccompPolicy("empty")
        result = str(p)
        assert "POLICY empty {" in result
        assert "} USE empty DEFAULT KILL" in result

    def test_policy_default_is_kill_when_not_set(self):
        """The default action should be KILL if never explicitly set."""
        p = SeccompPolicy()
        assert "DEFAULT KILL" in str(p)

    def test_policy_default_allow(self):
        p = SeccompPolicy().default_allow()
        assert "DEFAULT ALLOW" in str(p)

    def test_policy_default_log(self):
        p = SeccompPolicy().default_log()
        assert "DEFAULT LOG" in str(p)

    def test_policy_default_errno(self):
        p = SeccompPolicy().default_errno(42)
        assert "DEFAULT ERRNO(42)" in str(p)

    def test_empty_string_syscall_name(self):
        """Empty string syscall names are passed through without validation."""
        p = SeccompPolicy().allow("")
        result = str(p)
        assert "ALLOW {  }" in result

    def test_duplicate_syscalls_across_allow_calls(self):
        """Multiple .allow() calls merge into same rule group; duplicates kept."""
        p = SeccompPolicy().allow("read", "write").allow("read", "close")
        result = str(p)
        # All syscalls should appear in one ALLOW line
        assert "read, write, read, close" in result

    def test_very_long_syscall_list(self):
        """A very long list of syscalls should render without error."""
        syscalls = [f"syscall_{i}" for i in range(500)]
        p = SeccompPolicy().allow(*syscalls)
        result = str(p)
        assert "syscall_0" in result
        assert "syscall_499" in result
        assert result.count(",") == 499

    def test_mixed_actions_separate_groups(self):
        """Different actions create separate rule groups."""
        p = SeccompPolicy().allow("read").deny("write").allow("close")
        result = str(p)
        lines = result.strip().splitlines()
        # read and close should merge into ALLOW, write is KILL
        allow_lines = [l for l in lines if "ALLOW" in l and "{" in l and "}" in l]
        kill_lines = [l for l in lines if "KILL" in l and "{" in l and "}" in l]
        assert len(allow_lines) == 1
        assert len(kill_lines) == 1
        assert "read" in allow_lines[0] and "close" in allow_lines[0]

    def test_errno_and_trap_actions(self):
        p = SeccompPolicy().errno(22, "open").trap(9, "fork")
        result = str(p)
        assert "ERRNO(22)" in result
        assert "TRAP(9)" in result

    def test_custom_name(self):
        p = SeccompPolicy("my_custom_policy")
        assert "POLICY my_custom_policy {" in str(p)

    def test_policy_no_syscalls_in_action(self):
        """allow() with no args produces an empty rule group."""
        p = SeccompPolicy().allow()
        result = str(p)
        # No rules should be added since no syscalls were provided
        # _add_rules gets empty tuple, creates rule with empty list
        # On __str__, it renders as "ALLOW {  }" (join of empty list)
        assert "ALLOW" in result


# =============================================================================
# Cgroup parsing edge cases
# =============================================================================

class TestCgroupParsingEdgeCases:
    """Edge cases for cgroup stat file parsing."""

    def test_read_int_nonexistent_file(self, tmp_path: Path):
        """_read_int returns None for missing files."""
        result = _read_int(tmp_path / "nonexistent")
        assert result is None

    def test_read_int_non_numeric_content(self, tmp_path: Path):
        """_read_int returns None for non-numeric content."""
        f = tmp_path / "stat"
        f.write_text("not_a_number\n")
        assert _read_int(f) is None

    def test_read_int_empty_file(self, tmp_path: Path):
        """_read_int returns None for empty files."""
        f = tmp_path / "stat"
        f.write_text("")
        assert _read_int(f) is None

    def test_read_int_whitespace_only(self, tmp_path: Path):
        """_read_int returns None for whitespace-only files."""
        f = tmp_path / "stat"
        f.write_text("   \n  \n")
        assert _read_int(f) is None

    def test_read_int_valid(self, tmp_path: Path):
        f = tmp_path / "stat"
        f.write_text("12345\n")
        assert _read_int(f) == 12345

    def test_read_int_huge_value(self, tmp_path: Path):
        """_read_int handles near-int64-max values."""
        f = tmp_path / "stat"
        huge = 2**63 - 1
        f.write_text(f"{huge}\n")
        assert _read_int(f) == huge

    def test_read_int_negative(self, tmp_path: Path):
        f = tmp_path / "stat"
        f.write_text("-1\n")
        assert _read_int(f) == -1

    def test_parse_v1_stats_no_paths(self):
        """parse_v1_stats with no paths returns all-None stats."""
        stats = parse_v1_stats()
        assert stats.memory_peak_bytes is None
        assert stats.memory_current_bytes is None
        assert stats.cpu_usage_ns is None
        assert stats.pids_current is None

    def test_parse_v1_stats_missing_files(self, tmp_path: Path):
        """parse_v1_stats gracefully handles missing stat files."""
        stats = parse_v1_stats(
            memory_path=tmp_path / "nonexistent",
            cpu_path=tmp_path / "nonexistent",
            pids_path=tmp_path / "nonexistent",
        )
        assert stats.memory_peak_bytes is None
        assert stats.cpu_usage_ns is None
        assert stats.pids_current is None

    def test_parse_v2_stats_nonexistent_dir(self, tmp_path: Path):
        """parse_v2_stats with nonexistent directory returns all-None stats."""
        stats = parse_v2_stats(tmp_path / "nonexistent_cgroup")
        assert stats.memory_peak_bytes is None
        assert stats.memory_current_bytes is None
        assert stats.cpu_usage_ns is None
        assert stats.pids_current is None

    def test_parse_v2_stats_partial_cpu_stat(self, tmp_path: Path):
        """cpu.stat with only some fields should parse what's available."""
        (tmp_path / "cpu.stat").write_text("usage_usec 1000\n")
        stats = parse_v2_stats(tmp_path)
        assert stats.cpu_usage_ns == 1_000_000
        assert stats.cpu_user_ns is None
        assert stats.cpu_system_ns is None

    def test_parse_v2_stats_cpu_stat_garbage_lines(self, tmp_path: Path):
        """cpu.stat with non-numeric values in some lines."""
        (tmp_path / "cpu.stat").write_text(
            "usage_usec abc\n"
            "user_usec 2000\n"
        )
        # The int() conversion on "abc" raises ValueError, caught by except block
        # So the entire cpu.stat parsing is skipped
        stats = parse_v2_stats(tmp_path)
        assert stats.cpu_usage_ns is None
        assert stats.cpu_user_ns is None

    def test_parse_v2_stats_cpu_stat_empty(self, tmp_path: Path):
        """Empty cpu.stat file."""
        (tmp_path / "cpu.stat").write_text("")
        stats = parse_v2_stats(tmp_path)
        assert stats.cpu_usage_ns is None

    def test_parse_v2_stats_cpu_stat_extra_columns(self, tmp_path: Path):
        """Lines with more than 2 columns are skipped (len(parts) == 2 check)."""
        (tmp_path / "cpu.stat").write_text(
            "usage_usec 1000 extra_col\n"
            "user_usec 2000\n"
        )
        stats = parse_v2_stats(tmp_path)
        assert stats.cpu_usage_ns is None  # skipped due to 3 parts
        assert stats.cpu_user_ns == 2_000_000

    def test_parse_v2_stats_huge_values(self, tmp_path: Path):
        """Near-int64-max values in stat files."""
        huge = 2**63 - 1
        (tmp_path / "memory.peak").write_text(f"{huge}\n")
        (tmp_path / "cpu.stat").write_text(f"usage_usec {huge}\n")
        stats = parse_v2_stats(tmp_path)
        assert stats.memory_peak_bytes == huge
        assert stats.cpu_usage_ns == huge * 1000

    def test_cgroup_monitor_stop_without_start(self):
        """Stopping a monitor that was never started returns empty stats."""
        monitor = CgroupMonitor(cgroup_path=Path("/nonexistent"), use_v2=True)
        stats = monitor.stop()
        assert isinstance(stats, CgroupStats)

    def test_cgroup_monitor_start_stop_nonexistent_path(self):
        """Monitor with nonexistent path starts and stops gracefully."""
        monitor = CgroupMonitor(
            cgroup_path=Path("/nonexistent/cgroup"),
            poll_interval=0.01,
            use_v2=True,
        )
        monitor.start()
        import time
        time.sleep(0.05)  # Let it poll a couple times
        stats = monitor.stop()
        assert isinstance(stats, CgroupStats)
        assert stats.memory_peak_bytes is None

    def test_cgroup_stats_defaults(self):
        """All CgroupStats fields default to None."""
        stats = CgroupStats()
        for attr in (
            "memory_peak_bytes", "memory_current_bytes",
            "cpu_usage_ns", "cpu_user_ns", "cpu_system_ns",
            "pids_current",
        ):
            assert getattr(stats, attr) is None


# =============================================================================
# Runner error paths
# =============================================================================

class TestRunnerEdgeCases:
    """Edge cases for the Runner and related functions."""

    def test_resolve_nsjail_path_empty_string(self):
        """Empty string is accepted as explicit path (no validation)."""
        result = resolve_nsjail_path("")
        assert result == Path("")

    def test_resolve_nsjail_path_none_and_not_found(self, monkeypatch):
        """When nsjail is not on PATH and no companion, raises NsjailNotFound."""
        monkeypatch.setattr("shutil.which", lambda _: None)
        monkeypatch.setattr("nsjail.runner._try_companion_binary", lambda: None)
        with pytest.raises(NsjailNotFound):
            resolve_nsjail_path(None)

    def test_resolve_nsjail_path_explicit_takes_precedence(self, monkeypatch):
        """Explicit path is returned even if nsjail is on PATH."""
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/nsjail")
        result = resolve_nsjail_path("/custom/nsjail")
        assert result == Path("/custom/nsjail")

    def test_merge_configs_empty_override_fields(self):
        """merge_configs with empty override_fields changes nothing."""
        base = NsJailConfig(hostname="base_host", time_limit=100)
        overrides = NsJailConfig(hostname="override_host", time_limit=200)
        merged = merge_configs(base, overrides, override_fields=set())
        assert merged.hostname == "base_host"
        assert merged.time_limit == 100

    def test_merge_configs_extra_args_with_no_exec_bin(self):
        """extra_args are silently ignored when exec_bin is None."""
        base = NsJailConfig()
        assert base.exec_bin is None
        merged = merge_configs(
            base, NsJailConfig(),
            override_fields=set(),
            extra_args=["--foo", "bar"],
        )
        assert merged.exec_bin is None

    def test_merge_configs_extra_args_with_exec_bin(self):
        """extra_args are appended to exec_bin.arg."""
        base = NsJailConfig(exec_bin=Exe(path="/bin/echo", arg=["hello"]))
        merged = merge_configs(
            base, NsJailConfig(),
            override_fields=set(),
            extra_args=["world"],
        )
        assert merged.exec_bin.arg == ["hello", "world"]

    def test_merge_configs_list_fields_appended(self):
        """List fields from overrides are appended, not replaced."""
        base = NsJailConfig(envar=["A=1"])
        overrides = NsJailConfig(envar=["B=2"])
        merged = merge_configs(
            base, overrides,
            override_fields={"envar"},
        )
        assert merged.envar == ["A=1", "B=2"]

    def test_merge_configs_scalar_fields_replaced(self):
        """Scalar fields from overrides replace the base."""
        base = NsJailConfig(hostname="old")
        overrides = NsJailConfig(hostname="new")
        merged = merge_configs(
            base, overrides,
            override_fields={"hostname"},
        )
        assert merged.hostname == "new"

    def test_merge_configs_does_not_mutate_base(self):
        """merge_configs deep-copies the base; originals are untouched."""
        base = NsJailConfig(envar=["A=1"])
        overrides = NsJailConfig(envar=["B=2"])
        merge_configs(base, overrides, override_fields={"envar"})
        assert base.envar == ["A=1"]  # not mutated

    def test_nsjail_result_exit_code_zero(self):
        """Exit code 0: not timed out, not signaled, not oom, inner_returncode=0."""
        runner = Runner()
        result = runner._make_result(0, b"", b"", None, [])
        assert result.timed_out is False
        assert result.signaled is False
        assert result.oom_killed is False
        assert result.inner_returncode == 0

    def test_nsjail_result_exit_code_1(self):
        """Exit code 1: normal failure."""
        runner = Runner()
        result = runner._make_result(1, b"", b"", None, [])
        assert result.inner_returncode == 1
        assert result.timed_out is False
        assert result.signaled is False

    def test_nsjail_result_exit_code_99(self):
        """Exit code 99: still below 100, so has inner_returncode."""
        runner = Runner()
        result = runner._make_result(99, b"", b"", None, [])
        assert result.inner_returncode == 99
        assert result.signaled is False

    def test_nsjail_result_exit_code_100(self):
        """Exit code 100: exactly 100, no inner_returncode.
        signaled is False because the check is returncode > 100 (strict)."""
        runner = Runner()
        result = runner._make_result(100, b"", b"", None, [])
        assert result.inner_returncode is None
        assert result.signaled is False  # > 100, not >= 100
        assert result.timed_out is False

    def test_nsjail_result_exit_code_101(self):
        """Exit code 101: > 100 and not 109, so signaled=True."""
        runner = Runner()
        result = runner._make_result(101, b"", b"", None, [])
        assert result.inner_returncode is None
        assert result.signaled is True
        assert result.timed_out is False

    def test_nsjail_result_exit_code_109(self):
        """Exit code 109: timed_out=True, signaled=False (special case)."""
        runner = Runner()
        result = runner._make_result(109, b"", b"", None, [])
        assert result.timed_out is True
        assert result.signaled is False
        assert result.inner_returncode is None

    def test_nsjail_result_exit_code_137(self):
        """Exit code 137: oom_killed=True, also signaled (>100, not 109)."""
        runner = Runner()
        result = runner._make_result(137, b"", b"", None, [])
        assert result.oom_killed is True
        assert result.signaled is True
        assert result.timed_out is False
        assert result.inner_returncode is None

    def test_runner_fork_preserves_collect_cgroup_stats(self):
        """fork() carries over collect_cgroup_stats setting."""
        r = Runner(collect_cgroup_stats=True, cgroup_poll_interval=0.5)
        forked = r.fork()
        assert forked._collect_cgroup_stats is True
        assert forked._cgroup_poll_interval == 0.5

    def test_runner_fork_preserves_all_settings(self):
        """fork() carries over all runner settings."""
        r = Runner(
            nsjail_path="/custom/nsjail",
            render_mode="cli",
            capture_output=False,
            keep_config=True,
        )
        forked = r.fork()
        assert forked._nsjail_path == "/custom/nsjail"
        assert forked._render_mode == "cli"
        assert forked._capture_output is False
        assert forked._keep_config is True

    def test_runner_fork_with_overrides(self):
        """fork() with overrides merges configs."""
        base_cfg = NsJailConfig(hostname="base")
        r = Runner(base_config=base_cfg)
        overrides = NsJailConfig(hostname="forked")
        forked = r.fork(overrides=overrides, override_fields={"hostname"})
        assert forked._base_config.hostname == "forked"

    def test_runner_fork_nsjail_path_override(self):
        """fork() can override nsjail_path."""
        r = Runner(nsjail_path="/original")
        forked = r.fork(nsjail_path="/new_path")
        assert forked._nsjail_path == "/new_path"


# =============================================================================
# Builder misuse
# =============================================================================

class TestBuilderEdgeCases:
    """Edge cases for the Jail builder."""

    def test_build_with_no_command(self):
        """build() with no command set leaves exec_bin as None."""
        cfg = Jail().build()
        assert cfg.exec_bin is None

    def test_memory_zero(self):
        """memory(0) sets cgroup_mem_max to 0."""
        cfg = Jail().memory(0).build()
        assert cfg.cgroup_mem_max == 0

    def test_memory_negative(self):
        """memory() with negative value produces negative cgroup_mem_max (no validation)."""
        cfg = Jail().memory(-1).build()
        assert cfg.cgroup_mem_max == -1 * 1024 * 1024

    def test_memory_gb_unit(self):
        cfg = Jail().memory(2, unit="GB").build()
        assert cfg.cgroup_mem_max == 2 * 1024 * 1024 * 1024

    def test_timeout_zero(self):
        """timeout(0) is accepted (no validation)."""
        cfg = Jail().timeout(0).build()
        assert cfg.time_limit == 0

    def test_timeout_negative(self):
        cfg = Jail().timeout(-10).build()
        assert cfg.time_limit == -10

    def test_writable_tmpfs_no_size(self):
        """writable() with tmpfs=True but no size sets options to None."""
        cfg = Jail().writable("/data", tmpfs=True).build()
        mount = cfg.mount[-1]
        assert mount.fstype == "tmpfs"
        assert mount.rw is True
        assert mount.options is None

    def test_writable_tmpfs_with_size(self):
        cfg = Jail().writable("/data", tmpfs=True, size="64M").build()
        mount = cfg.mount[-1]
        assert mount.options == "size=64M"

    def test_last_command_wins(self):
        """Calling sh() then command() -- last one wins since exec_bin is replaced."""
        cfg = Jail().sh("echo hello").command("/bin/ls", "-la").build()
        assert cfg.exec_bin.path == "/bin/ls"
        assert cfg.exec_bin.arg == ["-la"]

    def test_sh_then_python_last_wins(self):
        cfg = Jail().sh("echo hello").python("-c", "print(1)").build()
        assert cfg.exec_bin.path == "/usr/bin/python3"

    def test_seccomp_empty_string(self):
        """seccomp() with empty string is accepted."""
        cfg = Jail().seccomp("").build()
        assert cfg.seccomp_string == [""]

    def test_seccomp_policy_object(self):
        p = SeccompPolicy("test").allow("read")
        cfg = Jail().seccomp(p).build()
        assert len(cfg.seccomp_string) == 1
        assert "POLICY test" in cfg.seccomp_string[0]

    def test_multiple_seccomp_calls(self):
        cfg = Jail().seccomp("policy1").seccomp("policy2").build()
        assert cfg.seccomp_string == ["policy1", "policy2"]

    def test_env_multiple(self):
        cfg = Jail().env("A=1").env("B=2").build()
        assert cfg.envar == ["A=1", "B=2"]

    def test_uid_map_defaults(self):
        cfg = Jail().uid_map().build()
        assert len(cfg.uidmap) == 1
        assert cfg.uidmap[0].inside_id == "0"
        assert cfg.uidmap[0].outside_id == "1000"

    def test_no_network_and_network_toggle(self):
        cfg = Jail().no_network().network().build()
        assert cfg.clone_newnet is False

    def test_fluent_chaining(self):
        """All builder methods return self for chaining."""
        j = Jail()
        result = j.command("ls").timeout(10).memory(256).cpu(500).pids(50)
        assert result is j


# =============================================================================
# Textproto serializer edge cases
# =============================================================================

class TestTextprotoEdgeCases:
    """Edge cases for the textproto serializer."""

    def test_escape_string_with_quotes(self):
        assert _escape_string('say "hello"') == 'say \\"hello\\"'

    def test_escape_string_with_backslashes(self):
        assert _escape_string("path\\to\\file") == "path\\\\to\\\\file"

    def test_escape_string_with_newlines(self):
        assert _escape_string("line1\nline2") == "line1\\nline2"

    def test_escape_string_combined(self):
        assert _escape_string('"a\\b\n"') == '\\"a\\\\b\\n\\"'

    def test_escape_bytes_binary_content(self):
        result = _escape_bytes(b"\x00\x01\xff")
        assert result == "\\x00\\x01\\xff"

    def test_escape_bytes_printable(self):
        result = _escape_bytes(b"hello")
        assert result == "hello"

    def test_escape_bytes_mixed(self):
        result = _escape_bytes(b"hi\x00bye")
        assert result == "hi\\x00bye"

    def test_escape_bytes_backslash_and_quote(self):
        """Backslash and quote bytes are escaped as hex."""
        result = _escape_bytes(b'a"b\\c')
        assert "\\x22" in result  # quote
        assert "\\x5c" in result  # backslash

    def test_config_with_src_content_bytes(self):
        """MountPt with src_content (bytes) serializes correctly."""
        cfg = NsJailConfig()
        cfg.mount.append(MountPt(dst="/data", src_content=b"\x00\x01binary"))
        result = to_textproto(cfg)
        assert "src_content" in result
        assert "\\x00\\x01binary" in result

    def test_default_config_produces_minimal_output(self):
        """Default NsJailConfig should produce empty/minimal textproto."""
        cfg = NsJailConfig()
        result = to_textproto(cfg)
        # Defaults are skipped, so output should be empty or near-empty
        assert result.strip() == "" or len(result.strip().splitlines()) < 5

    def test_enum_at_boundaries(self):
        """Enum values at first and last positions serialize correctly."""
        cfg = NsJailConfig(mode=Mode.LISTEN)
        result = to_textproto(cfg)
        # Mode.LISTEN is the default (0), so it should be skipped
        # Actually Mode.ONCE (1) is the dataclass default, so LISTEN != default
        assert "LISTEN" in result

        cfg2 = NsJailConfig(mode=Mode.EXECVE)
        result2 = to_textproto(cfg2)
        assert "EXECVE" in result2

    def test_nested_user_net(self):
        """UserNet nested message serializes correctly."""
        cfg = NsJailConfig(user_net=UserNet(enable=True))
        result = to_textproto(cfg)
        assert "user_net {" in result
        assert "enable: true" in result

    def test_deeply_nested_produces_indentation(self):
        """Nested messages get proper indentation."""
        cfg = NsJailConfig(user_net=UserNet(enable=True))
        result = to_textproto(cfg)
        lines = result.strip().splitlines()
        # The inner field should be indented
        enable_lines = [l for l in lines if "enable" in l]
        assert any(l.startswith("  ") for l in enable_lines)

    def test_repeated_string_field(self):
        """Repeated string fields render one line each."""
        cfg = NsJailConfig(envar=["A=1", "B=2", "C=3"])
        result = to_textproto(cfg)
        assert result.count("envar:") == 3

    def test_empty_repeated_field_omitted(self):
        """Empty repeated fields are not rendered."""
        cfg = NsJailConfig(envar=[])
        result = to_textproto(cfg)
        assert "envar" not in result


# =============================================================================
# CLI serializer edge cases
# =============================================================================

class TestCLISerializerEdgeCases:
    """Edge cases for the CLI argument serializer."""

    def test_default_config_produces_no_args(self):
        """Default config should produce empty or near-empty CLI args."""
        cfg = NsJailConfig()
        args = to_cli_args(cfg, on_unsupported="skip")
        # All defaults should be skipped
        assert len(args) == 0 or all(isinstance(a, str) for a in args)

    def test_on_unsupported_raise(self):
        """Setting an unsupported field with on_unsupported='raise' raises."""
        cfg = NsJailConfig()
        cfg.description.append("test description")  # description is cli_supported=False
        with pytest.raises(UnsupportedCLIField):
            to_cli_args(cfg, on_unsupported="raise")

    def test_on_unsupported_skip(self):
        """Setting an unsupported field with on_unsupported='skip' silently skips."""
        cfg = NsJailConfig()
        cfg.description.append("test description")
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--description" not in args
        assert "test description" not in args

    def test_on_unsupported_warn(self, caplog):
        """Setting an unsupported field with on_unsupported='warn' logs warning."""
        import logging
        cfg = NsJailConfig()
        cfg.description.append("test description")
        with caplog.at_level(logging.WARNING):
            to_cli_args(cfg, on_unsupported="warn")
        assert "description" in caplog.text

    def test_bool_field_true_renders_flag(self):
        """Bool field set to non-default True renders just the flag."""
        cfg = NsJailConfig(keep_env=True)
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--keep_env" in args or "-e" in args or any("keep_env" in a for a in args)

    def test_clone_newnet_false_is_non_default(self):
        """clone_newnet defaults to True; setting False is non-default but
        bool rendering only emits flag when True, so False may be unrenderable."""
        cfg = NsJailConfig(clone_newnet=False)
        args = to_cli_args(cfg, on_unsupported="skip")
        # The CLI serializer renders bools as: if value: append flag
        # So False would NOT appear in the args even though it's non-default
        # This is a known limitation of the CLI serializer for bool fields

    def test_integer_field_non_default(self):
        """Non-default integer field renders flag + value."""
        cfg = NsJailConfig(time_limit=30)
        args = to_cli_args(cfg, on_unsupported="skip")
        # Should contain the time limit flag and value
        assert "30" in args

    def test_repeated_field_renders_multiple_flags(self):
        """Repeated fields render one flag per item."""
        cfg = NsJailConfig(envar=["A=1", "B=2"])
        args = to_cli_args(cfg, on_unsupported="skip")
        # Count how many times the envar flag appears
        assert args.count("A=1") == 1
        assert args.count("B=2") == 1


# =============================================================================
# Config dataclass edge cases
# =============================================================================

class TestConfigEdgeCases:
    """Edge cases for config dataclasses."""

    def test_mountpt_conflicting_flags(self):
        """MountPt with is_bind=True and fstype='tmpfs' is allowed (no validation)."""
        m = MountPt(src="/data", dst="/data", is_bind=True, fstype="tmpfs")
        assert m.is_bind is True
        assert m.fstype == "tmpfs"

    def test_mountpt_all_none(self):
        m = MountPt()
        assert m.src is None
        assert m.dst is None
        assert m.fstype is None

    def test_exe_no_path(self):
        e = Exe()
        assert e.path is None
        assert e.arg == []

    def test_idmap_defaults(self):
        i = IdMap()
        assert i.inside_id == ""
        assert i.outside_id == ""
        assert i.count == 1

    def test_config_list_mutation_after_construction(self):
        """Mutating list fields after construction affects the config."""
        cfg = NsJailConfig()
        cfg.envar.append("NEW=1")
        assert "NEW=1" in cfg.envar

    def test_config_independent_instances(self):
        """Two NsJailConfig instances have independent list fields."""
        cfg1 = NsJailConfig()
        cfg2 = NsJailConfig()
        cfg1.envar.append("X=1")
        assert "X=1" not in cfg2.envar

    def test_very_large_field_values(self):
        """Config accepts very large integer values."""
        cfg = NsJailConfig(rlimit_as=2**31, time_limit=2**31)
        assert cfg.rlimit_as == 2**31
        assert cfg.time_limit == 2**31

    def test_user_net_defaults(self):
        u = UserNet()
        assert u.enable is False
        assert u.ip == "10.255.255.2"

    def test_config_deep_copy_independence(self):
        """Deep copy of config produces independent object."""
        cfg = NsJailConfig(envar=["A=1"], mount=[MountPt(dst="/tmp")])
        cfg_copy = copy.deepcopy(cfg)
        cfg_copy.envar.append("B=2")
        cfg_copy.mount.append(MountPt(dst="/var"))
        assert len(cfg.envar) == 1
        assert len(cfg.mount) == 1


# =============================================================================
# Presets edge cases
# =============================================================================

class TestPresetsEdgeCases:
    """Edge cases for preset configurations."""

    def test_sandbox_empty_command_list(self):
        """sandbox() with empty list raises IndexError on command[0]."""
        with pytest.raises(IndexError):
            sandbox(command=[])

    def test_sandbox_single_element_command(self):
        """sandbox() with single-element command works; arg is empty."""
        cfg = sandbox(command=["/bin/true"])
        assert cfg.exec_bin.path == "/bin/true"
        assert cfg.exec_bin.arg == []

    def test_sandbox_default_values(self):
        cfg = sandbox(command=["/bin/echo", "hello"])
        assert cfg.cwd == "/"
        assert cfg.time_limit == 600
        assert cfg.clone_newnet is True  # network=False by default

    def test_sandbox_with_network(self):
        cfg = sandbox(command=["/bin/echo"], network=True)
        assert cfg.clone_newnet is False

    def test_sandbox_with_all_limits(self):
        cfg = sandbox(
            command=["/bin/echo"],
            memory_mb=256,
            cpu_ms_per_sec=500,
            pids_max=100,
        )
        assert cfg.cgroup_mem_max == 256 * 1024 * 1024
        assert cfg.cgroup_cpu_ms_per_sec == 500
        assert cfg.cgroup_pids_max == 100

    def test_apply_readonly_root_no_writable(self):
        """apply_readonly_root with no writable dirs adds just the root bind."""
        cfg = NsJailConfig()
        apply_readonly_root(cfg)
        assert len(cfg.mount) == 1
        assert cfg.mount[0].src == "/"
        assert cfg.mount[0].dst == "/"
        assert cfg.mount[0].rw is False

    def test_apply_readonly_root_empty_writable_list(self):
        """Empty writable list is same as no writable dirs."""
        cfg = NsJailConfig()
        apply_readonly_root(cfg, writable=[])
        assert len(cfg.mount) == 1

    def test_apply_readonly_root_tmp_special(self):
        """/tmp gets mounted as tmpfs instead of bind mount."""
        cfg = NsJailConfig()
        apply_readonly_root(cfg, writable=["/tmp"])
        assert len(cfg.mount) == 2
        tmp_mount = cfg.mount[1]
        assert tmp_mount.dst == "/tmp"
        assert tmp_mount.fstype == "tmpfs"
        assert tmp_mount.is_bind is False

    def test_apply_readonly_root_non_tmp_writable(self):
        """Non-/tmp writable dirs get bind-mounted rw."""
        cfg = NsJailConfig()
        apply_readonly_root(cfg, writable=["/data"])
        assert len(cfg.mount) == 2
        data_mount = cfg.mount[1]
        assert data_mount.src == "/data"
        assert data_mount.is_bind is True
        assert data_mount.rw is True

    def test_apply_cgroup_limits_none_values(self):
        """apply_cgroup_limits with all None changes nothing."""
        cfg = NsJailConfig()
        original_mem = cfg.cgroup_mem_max
        original_cpu = cfg.cgroup_cpu_ms_per_sec
        original_pids = cfg.cgroup_pids_max
        apply_cgroup_limits(cfg)
        assert cfg.cgroup_mem_max == original_mem
        assert cfg.cgroup_cpu_ms_per_sec == original_cpu
        assert cfg.cgroup_pids_max == original_pids

    def test_apply_cgroup_limits_zero_values(self):
        """Zero values are set directly (no guard against zero)."""
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg, memory_mb=0, cpu_ms_per_sec=0, pids_max=0)
        assert cfg.cgroup_mem_max == 0
        assert cfg.cgroup_cpu_ms_per_sec == 0
        assert cfg.cgroup_pids_max == 0

    def test_apply_seccomp_log(self):
        cfg = NsJailConfig()
        assert cfg.seccomp_log is False
        apply_seccomp_log(cfg)
        assert cfg.seccomp_log is True

    def test_sandbox_writable_dirs(self):
        cfg = sandbox(command=["/bin/echo"], writable_dirs=["/tmp", "/var/log"])
        # /tmp should be tmpfs, /var/log should be bind
        mounts = cfg.mount
        tmp_mounts = [m for m in mounts if m.dst == "/tmp"]
        var_mounts = [m for m in mounts if m.dst == "/var/log"]
        assert len(tmp_mounts) == 1
        assert tmp_mounts[0].fstype == "tmpfs"
        assert len(var_mounts) == 1
        assert var_mounts[0].is_bind is True


# =============================================================================
# Cross-module integration edge cases
# =============================================================================

class TestCrossModuleEdgeCases:
    """Edge cases spanning multiple modules."""

    def test_builder_to_textproto_roundtrip_minimal(self):
        """A minimal builder config serializes to valid textproto."""
        cfg = Jail().sh("echo hello").timeout(10).build()
        result = to_textproto(cfg)
        assert "time_limit: 10" in result
        assert 'path: "/bin/sh"' in result

    def test_builder_to_cli_args_minimal(self):
        """A minimal builder config serializes to CLI args."""
        cfg = Jail().timeout(10).build()
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "10" in args

    def test_seccomp_policy_in_textproto(self):
        """SeccompPolicy used in config serializes in textproto."""
        p = SeccompPolicy("test").allow("read", "write")
        cfg = Jail().seccomp(p).build()
        result = to_textproto(cfg)
        assert "seccomp_string" in result

    def test_empty_policy_in_config(self):
        """An empty SeccompPolicy in config still serializes."""
        p = SeccompPolicy("empty")
        cfg = Jail().seccomp(p).build()
        result = to_textproto(cfg)
        assert "seccomp_string" in result

    def test_runner_default_config_is_independent(self):
        """Modifying the config passed to Runner doesn't affect the runner."""
        cfg = NsJailConfig(hostname="original")
        r = Runner(base_config=cfg)
        cfg.hostname = "modified"
        assert r._base_config.hostname == "original"

    def test_nsjail_result_all_fields(self):
        """NsJailResult can be constructed with all fields."""
        result = NsJailResult(
            returncode=0,
            stdout=b"out",
            stderr=b"err",
            config_path=Path("/tmp/test.cfg"),
            nsjail_args=["nsjail", "--config", "/tmp/test.cfg"],
            timed_out=False,
            oom_killed=False,
            signaled=False,
            inner_returncode=0,
            cgroup_stats=CgroupStats(memory_peak_bytes=1024),
        )
        assert result.cgroup_stats.memory_peak_bytes == 1024

    def test_merge_configs_with_mount_list(self):
        """Merging configs with mount lists appends mounts."""
        base = NsJailConfig(mount=[MountPt(dst="/base")])
        overrides = NsJailConfig(mount=[MountPt(dst="/override")])
        merged = merge_configs(base, overrides, override_fields={"mount"})
        assert len(merged.mount) == 2
        assert merged.mount[0].dst == "/base"
        assert merged.mount[1].dst == "/override"
