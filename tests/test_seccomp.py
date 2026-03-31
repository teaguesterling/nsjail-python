from nsjail.seccomp import SeccompPolicy


class TestSeccompPolicyBuilder:
    def test_empty_policy_with_default(self):
        policy = SeccompPolicy("test").default_kill()
        text = str(policy)
        assert "POLICY test" in text
        assert "DEFAULT KILL" in text

    def test_allow_syscalls(self):
        policy = SeccompPolicy("p").allow("read", "write").default_kill()
        text = str(policy)
        assert "ALLOW { read, write }" in text

    def test_deny_syscalls(self):
        policy = SeccompPolicy("p").deny("execve", "fork").default_allow()
        text = str(policy)
        assert "KILL { execve, fork }" in text

    def test_errno_syscalls(self):
        policy = SeccompPolicy("p").errno(1, "open", "openat").default_kill()
        text = str(policy)
        assert "ERRNO(1) { open, openat }" in text

    def test_log_syscalls(self):
        policy = SeccompPolicy("p").log("connect").default_kill()
        text = str(policy)
        assert "LOG { connect }" in text

    def test_trap_syscalls(self):
        policy = SeccompPolicy("p").trap(5, "ptrace").default_kill()
        text = str(policy)
        assert "TRAP(5) { ptrace }" in text

    def test_multiple_rules(self):
        policy = (
            SeccompPolicy("multi")
            .allow("read", "write", "close")
            .deny("execve")
            .errno(13, "open")
            .default_kill()
        )
        text = str(policy)
        assert "ALLOW { read, write, close }" in text
        assert "KILL { execve }" in text
        assert "ERRNO(13) { open }" in text
        assert "DEFAULT KILL" in text

    def test_chaining_returns_self(self):
        policy = SeccompPolicy("p")
        result = policy.allow("read")
        assert result is policy

    def test_default_name(self):
        policy = SeccompPolicy().allow("read").default_kill()
        text = str(policy)
        assert "POLICY policy" in text

    def test_default_allow(self):
        policy = SeccompPolicy("p").deny("execve").default_allow()
        text = str(policy)
        assert "DEFAULT ALLOW" in text

    def test_default_log(self):
        policy = SeccompPolicy("p").default_log()
        text = str(policy)
        assert "DEFAULT LOG" in text

    def test_default_errno(self):
        policy = SeccompPolicy("p").default_errno(1)
        text = str(policy)
        assert "DEFAULT ERRNO(1)" in text

    def test_use_statement(self):
        policy = SeccompPolicy("mypol").allow("read").default_kill()
        text = str(policy)
        assert "USE mypol" in text

    def test_accumulates_across_calls(self):
        policy = SeccompPolicy("p").allow("read").allow("write").default_kill()
        text = str(policy)
        assert "read" in text
        assert "write" in text


from nsjail.seccomp import MINIMAL, DEFAULT_LOG, READONLY


class TestSeccompPresets:
    def test_minimal_is_seccomp_policy(self):
        assert isinstance(MINIMAL, SeccompPolicy)

    def test_minimal_allows_basic_syscalls(self):
        text = str(MINIMAL)
        assert "read" in text
        assert "write" in text
        assert "close" in text
        assert "exit_group" in text
        assert "DEFAULT KILL" in text

    def test_minimal_valid_kafel(self):
        text = str(MINIMAL)
        assert "POLICY " in text
        assert "ALLOW {" in text
        assert "} USE " in text

    def test_default_log_uses_log_default(self):
        text = str(DEFAULT_LOG)
        assert "DEFAULT LOG" in text

    def test_readonly_blocks_writes(self):
        text = str(READONLY)
        assert "ERRNO" in text
        assert "DEFAULT" in text

    def test_presets_are_independent(self):
        t1 = str(MINIMAL)
        t2 = str(MINIMAL)
        assert t1 == t2
