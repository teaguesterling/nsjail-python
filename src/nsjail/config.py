# GENERATED from nsjail config.proto — DO NOT EDIT
# Re-run: python -m _codegen.generate

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from nsjail.enums import LogLevel, Mode, RLimitType


@dataclass
class UserNet:
    enable: bool = False
    ip: str = "10.255.255.2"
    mask: str = "255.255.255.0"
    gw: str = "10.255.255.1"
    ip6: str = "fc00::2"
    mask6: str = "64"
    gw6: str = "fc00::1"
    ns_iface: str = "eth0"
    tcp_ports: str = "none"
    udp_ports: str = "none"
    enable_ip4_dhcp: bool = False
    enable_dns: bool = False
    dns_forward: str = ""
    enable_tcp: bool = True
    enable_udp: bool = True
    enable_icmp: bool = True
    no_map_gw: bool = False
    enable_ip6_dhcp: bool = False
    enable_ip6_ra: bool = False


@dataclass
class IdMap:
    inside_id: str = ""
    outside_id: str = ""
    count: int = 1
    use_newidmap: bool = False


@dataclass
class MountPt:
    src: str | None = None
    prefix_src_env: str | None = None
    src_content: bytes | None = None
    dst: str | None = None
    prefix_dst_env: str | None = None
    fstype: str | None = None
    options: str | None = None
    is_bind: bool = False
    rw: bool = False
    is_dir: bool | None = None
    mandatory: bool = True
    is_symlink: bool = False
    nosuid: bool = False
    nodev: bool = False
    noexec: bool = False


@dataclass
class Exe:
    path: str | None = None
    arg: list[str] = field(default_factory=list)
    arg0: str | None = None
    exec_fd: bool = False


@dataclass
class NsJailConfig:
    name: str | None = None
    description: list[str] = field(default_factory=list)
    mode: Mode = Mode.ONCE
    hostname: str = "NSJAIL"
    cwd: str = "/"
    no_pivotroot: bool = False
    port: int = 0
    bindhost: str = "::"
    max_conns: int = 0
    max_conns_per_ip: int = 0
    time_limit: int = 600
    daemon: bool = False
    max_cpus: int = 0
    nice_level: int = 19
    log_fd: int | None = None
    log_file: str | None = None
    log_level: LogLevel | None = None
    keep_env: bool = False
    envar: list[str] = field(default_factory=list)
    keep_caps: bool = False
    cap: list[str] = field(default_factory=list)
    silent: bool = False
    skip_setsid: bool = False
    stderr_to_null: bool = False
    pass_fd: list[int] = field(default_factory=list)
    disable_no_new_privs: bool = False
    forward_signals: bool = False
    disable_tsc: bool = False
    rlimit_as: int = 4096
    rlimit_as_type: RLimitType = RLimitType.VALUE
    rlimit_core: int = 0
    rlimit_core_type: RLimitType = RLimitType.VALUE
    rlimit_cpu: int = 600
    rlimit_cpu_type: RLimitType = RLimitType.VALUE
    rlimit_fsize: int = 1
    rlimit_fsize_type: RLimitType = RLimitType.VALUE
    rlimit_nofile: int = 32
    rlimit_nofile_type: RLimitType = RLimitType.VALUE
    rlimit_nproc: int = 1024
    rlimit_nproc_type: RLimitType = RLimitType.SOFT
    rlimit_stack: int = 8
    rlimit_stack_type: RLimitType = RLimitType.SOFT
    rlimit_memlock: int = 64
    rlimit_memlock_type: RLimitType = RLimitType.SOFT
    rlimit_rtprio: int = 0
    rlimit_rtprio_type: RLimitType = RLimitType.SOFT
    rlimit_msgqueue: int = 1024
    rlimit_msgqueue_type: RLimitType = RLimitType.SOFT
    disable_rl: bool = False
    persona_addr_compat_layout: bool = False
    persona_mmap_page_zero: bool = False
    persona_read_implies_exec: bool = False
    persona_addr_limit_3gb: bool = False
    persona_addr_no_randomize: bool = False
    clone_newnet: bool = True
    clone_newuser: bool = True
    clone_newns: bool = True
    clone_newpid: bool = True
    clone_newipc: bool = True
    clone_newuts: bool = True
    clone_newcgroup: bool = True
    clone_newtime: bool = False
    uidmap: list[IdMap] = field(default_factory=list)
    gidmap: list[IdMap] = field(default_factory=list)
    mount_proc: bool = False
    mount: list[MountPt] = field(default_factory=list)
    seccomp_policy_file: str | None = None
    seccomp_string: list[str] = field(default_factory=list)
    seccomp_log: bool = False
    cgroup_mem_max: int = 0
    cgroup_mem_memsw_max: int = 0
    cgroup_mem_swap_max: int = -1
    cgroup_mem_mount: str = "/sys/fs/cgroup/memory"
    cgroup_mem_parent: str = "NSJAIL"
    cgroup_pids_max: int = 0
    cgroup_pids_mount: str = "/sys/fs/cgroup/pids"
    cgroup_pids_parent: str = "NSJAIL"
    cgroup_net_cls_classid: int = 0
    cgroup_net_cls_mount: str = "/sys/fs/cgroup/net_cls"
    cgroup_net_cls_parent: str = "NSJAIL"
    cgroup_cpu_ms_per_sec: int = 0
    cgroup_cpu_mount: str = "/sys/fs/cgroup/cpu"
    cgroup_cpu_parent: str = "NSJAIL"
    cgroupv2_mount: str = "/sys/fs/cgroup"
    use_cgroupv2: bool = False
    detect_cgroupv2: bool = False
    iface_no_lo: bool = False
    iface_own: list[str] = field(default_factory=list)
    macvlan_iface: str | None = None
    macvlan_vs_ip: str = "192.168.0.2"
    macvlan_vs_nm: str = "255.255.255.0"
    macvlan_vs_gw: str = "192.168.0.1"
    macvlan_vs_ma: str = ""
    macvlan_vs_mo: str = "private"
    user_net: UserNet | None = None
    exec_bin: Exe | None = None

