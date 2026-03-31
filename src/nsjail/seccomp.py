"""Seccomp policy builder and presets for nsjail.

Generates Kafel policy strings from a fluent Python API.
"""

from __future__ import annotations


class SeccompPolicy:
    """Builder for Kafel seccomp policy strings."""

    def __init__(self, name: str = "policy") -> None:
        self._name = name
        self._rules: list[tuple[str, list[str]]] = []
        self._default: str = "KILL"

    def allow(self, *syscalls: str) -> SeccompPolicy:
        self._add_rules("ALLOW", syscalls)
        return self

    def deny(self, *syscalls: str) -> SeccompPolicy:
        self._add_rules("KILL", syscalls)
        return self

    def errno(self, errno: int, *syscalls: str) -> SeccompPolicy:
        self._add_rules(f"ERRNO({errno})", syscalls)
        return self

    def log(self, *syscalls: str) -> SeccompPolicy:
        self._add_rules("LOG", syscalls)
        return self

    def trap(self, signo: int, *syscalls: str) -> SeccompPolicy:
        self._add_rules(f"TRAP({signo})", syscalls)
        return self

    def default_kill(self) -> SeccompPolicy:
        self._default = "KILL"
        return self

    def default_allow(self) -> SeccompPolicy:
        self._default = "ALLOW"
        return self

    def default_log(self) -> SeccompPolicy:
        self._default = "LOG"
        return self

    def default_errno(self, errno: int) -> SeccompPolicy:
        self._default = f"ERRNO({errno})"
        return self

    def _add_rules(self, action: str, syscalls: tuple[str, ...]) -> None:
        for existing_action, existing_syscalls in self._rules:
            if existing_action == action:
                existing_syscalls.extend(syscalls)
                return
        self._rules.append((action, list(syscalls)))

    def __str__(self) -> str:
        lines = [f"POLICY {self._name} {{"]
        for action, syscalls in self._rules:
            lines.append(f"  {action} {{ {', '.join(syscalls)} }}")
        lines.append(f"}} USE {self._name} DEFAULT {self._default}")
        return "\n".join(lines)
