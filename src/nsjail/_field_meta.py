# GENERATED from nsjail config.proto — DO NOT EDIT
# Re-run: python -m _codegen.generate

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldMeta:
    """Metadata about a single proto field."""
    number: int
    proto_type: str
    default: object
    cli_flag: str | None
    cli_supported: bool
    is_repeated: bool
    is_message: bool


FIELD_REGISTRY: dict[tuple[str, str], FieldMeta] = {}


def _r(msg: str, name: str, **kwargs: object) -> None:
    FIELD_REGISTRY[(msg, name)] = FieldMeta(**kwargs)  # type: ignore[arg-type]


# ── MountPt (15 fields) ──────────────────────────────────────────────────────
_r("MountPt", "src",            number=1,  proto_type="string", default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "prefix_src_env", number=2,  proto_type="string", default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "src_content",    number=3,  proto_type="bytes",  default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "dst",            number=4,  proto_type="string", default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "prefix_dst_env", number=5,  proto_type="string", default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "fstype",         number=6,  proto_type="string", default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "options",        number=7,  proto_type="string", default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "is_bind",        number=8,  proto_type="bool",   default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "rw",             number=9,  proto_type="bool",   default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "is_dir",         number=10, proto_type="bool",   default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "mandatory",      number=11, proto_type="bool",   default=True,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "is_symlink",     number=12, proto_type="bool",   default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "nosuid",         number=13, proto_type="bool",   default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "nodev",          number=14, proto_type="bool",   default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("MountPt", "noexec",         number=15, proto_type="bool",   default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)

# ── IdMap (4 fields) ─────────────────────────────────────────────────────────
_r("IdMap", "inside_id",    number=1, proto_type="string", default="",    cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("IdMap", "outside_id",   number=2, proto_type="string", default="",    cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("IdMap", "count",        number=3, proto_type="uint32", default=1,     cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("IdMap", "use_newidmap", number=4, proto_type="bool",   default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)

# ── Exe (4 fields) ───────────────────────────────────────────────────────────
_r("Exe", "path",    number=1, proto_type="string", default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("Exe", "arg",     number=2, proto_type="string", default=[],    cli_flag=None, cli_supported=False, is_repeated=True,  is_message=False)
_r("Exe", "arg0",    number=3, proto_type="string", default=None,  cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("Exe", "exec_fd", number=4, proto_type="bool",   default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)

# ── NsJailConfig ─────────────────────────────────────────────────────────────
# Identity
_r("NsJailConfig", "name",        number=1, proto_type="string", default=None,     cli_flag="--name",     cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "description", number=2, proto_type="string", default=[],       cli_flag=None,         cli_supported=False, is_repeated=True,  is_message=False)
_r("NsJailConfig", "mode",        number=3, proto_type="enum",   default=1,        cli_flag=None,         cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "hostname",    number=8, proto_type="string", default="NSJAIL", cli_flag="--hostname", cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "cwd",         number=9, proto_type="string", default="/",      cli_flag="--cwd",      cli_supported=True,  is_repeated=False, is_message=False)

# Listen
_r("NsJailConfig", "port",             number=10, proto_type="uint32", default=0,    cli_flag="--port",             cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "bindhost",         number=11, proto_type="string", default="::", cli_flag="--bindhost",         cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "max_conns",        number=12, proto_type="uint32", default=0,    cli_flag="--max_conns",        cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "max_conns_per_ip", number=13, proto_type="uint32", default=0,    cli_flag="--max_conns_per_ip", cli_supported=True,  is_repeated=False, is_message=False)

# Execution
_r("NsJailConfig", "time_limit",           number=14, proto_type="uint32", default=600,  cli_flag="--time_limit",           cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "daemon",               number=15, proto_type="bool",   default=False, cli_flag="--daemon",               cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "max_cpus",             number=16, proto_type="uint32", default=0,    cli_flag="--max_cpus",             cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "nice_level",           number=17, proto_type="int32",  default=19,   cli_flag="--nice_level",           cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "keep_env",             number=18, proto_type="bool",   default=False, cli_flag="--keep_env",             cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "envar",                number=19, proto_type="string", default=[],   cli_flag="--env",                  cli_supported=True,  is_repeated=True,  is_message=False)
_r("NsJailConfig", "silent",               number=20, proto_type="bool",   default=False, cli_flag="--silent",               cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "skip_setsid",          number=21, proto_type="bool",   default=False, cli_flag="--skip_setsid",          cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "stderr_to_null",       number=22, proto_type="bool",   default=False, cli_flag="--stderr_to_null",       cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "pass_fd",              number=23, proto_type="int32",  default=[],   cli_flag="--pass_fd",              cli_supported=True,  is_repeated=True,  is_message=False)
_r("NsJailConfig", "disable_no_new_privs", number=24, proto_type="bool",   default=False, cli_flag="--disable_no_new_privs", cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "forward_signals",      number=25, proto_type="bool",   default=False, cli_flag="--forward_signals",      cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "disable_tsc",          number=26, proto_type="bool",   default=False, cli_flag="--disable_tsc",          cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "oom_score_adj",        number=27, proto_type="int32",  default=None,  cli_flag="--oom_score_adj",        cli_supported=True,  is_repeated=False, is_message=False)

# Logging
_r("NsJailConfig", "log_fd",    number=30, proto_type="int32",  default=None, cli_flag="--log_fd",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "log_file",  number=31, proto_type="string", default=None, cli_flag="--log",     cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "log_level", number=32, proto_type="enum",   default=None, cli_flag=None,        cli_supported=False, is_repeated=False, is_message=False)

# Capabilities
_r("NsJailConfig", "keep_caps", number=33, proto_type="bool",   default=False, cli_flag="--keep_caps", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "cap",       number=34, proto_type="string", default=[],   cli_flag="--cap",       cli_supported=True, is_repeated=True,  is_message=False)

# Rlimits
_r("NsJailConfig", "rlimit_as",            number=35, proto_type="uint64", default=4096, cli_flag="--rlimit_as",   cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_as_type",       number=36, proto_type="enum",   default=0,    cli_flag=None,            cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_core",          number=37, proto_type="uint64", default=0,    cli_flag="--rlimit_core", cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_core_type",     number=38, proto_type="enum",   default=0,    cli_flag=None,            cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_cpu",           number=39, proto_type="uint64", default=600,  cli_flag="--rlimit_cpu",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_cpu_type",      number=40, proto_type="enum",   default=0,    cli_flag=None,            cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_fsize",         number=41, proto_type="uint64", default=1,    cli_flag="--rlimit_fsize",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_fsize_type",    number=42, proto_type="enum",   default=0,    cli_flag=None,              cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_nofile",        number=43, proto_type="uint64", default=32,   cli_flag="--rlimit_nofile",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_nofile_type",   number=44, proto_type="enum",   default=0,    cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_nproc",         number=45, proto_type="uint64", default=1024, cli_flag="--rlimit_nproc",   cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_nproc_type",    number=46, proto_type="enum",   default=1,    cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_stack",         number=47, proto_type="uint64", default=8,    cli_flag="--rlimit_stack",   cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_stack_type",    number=48, proto_type="enum",   default=1,    cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_memlock",       number=49, proto_type="uint64", default=64,   cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_memlock_type",  number=50, proto_type="enum",   default=0,    cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_rtprio",        number=51, proto_type="uint64", default=0,    cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_rtprio_type",   number=52, proto_type="enum",   default=0,    cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_msgqueue",      number=53, proto_type="uint64", default=1024, cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "rlimit_msgqueue_type", number=54, proto_type="enum",   default=0,    cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "disable_rl",           number=55, proto_type="bool",   default=False, cli_flag="--disable_rl",    cli_supported=True,  is_repeated=False, is_message=False)

# Personality
_r("NsJailConfig", "persona_addr_compat_layout", number=56, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "persona_mmap_page_zero",     number=57, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "persona_read_implies_exec",  number=58, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "persona_addr_limit_3gb",     number=59, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "persona_addr_no_randomize",  number=60, proto_type="bool", default=False, cli_flag=None, cli_supported=False, is_repeated=False, is_message=False)

# Namespaces
_r("NsJailConfig", "clone_newnet",    number=61, proto_type="bool", default=True,  cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newuser",   number=62, proto_type="bool", default=True,  cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newns",     number=63, proto_type="bool", default=True,  cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newpid",    number=64, proto_type="bool", default=True,  cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newipc",    number=65, proto_type="bool", default=True,  cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newuts",    number=66, proto_type="bool", default=True,  cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newcgroup", number=67, proto_type="bool", default=True,  cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "clone_newtime",   number=68, proto_type="bool", default=False, cli_flag=None, cli_supported=True, is_repeated=False, is_message=False)

# UID/GID mapping
_r("NsJailConfig", "uidmap", number=69, proto_type="message", default=[], cli_flag="--uid_mapping", cli_supported=True,  is_repeated=True, is_message=True)
_r("NsJailConfig", "gidmap", number=70, proto_type="message", default=[], cli_flag="--gid_mapping", cli_supported=True,  is_repeated=True, is_message=True)

# Mounts
_r("NsJailConfig", "mount_proc",   number=71, proto_type="bool",    default=False, cli_flag="--mount_proc", cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "mount",        number=72, proto_type="message", default=[],   cli_flag=None,           cli_supported=False, is_repeated=True,  is_message=True)
_r("NsJailConfig", "no_pivotroot", number=73, proto_type="bool",    default=False, cli_flag="--no_pivotroot", cli_supported=True,  is_repeated=False, is_message=False)

# Seccomp
_r("NsJailConfig", "seccomp_policy_file", number=74, proto_type="string", default=None, cli_flag="--seccomp_policy", cli_supported=True, is_repeated=False, is_message=False)
_r("NsJailConfig", "seccomp_string",      number=75, proto_type="string", default=[],   cli_flag="--seccomp_string", cli_supported=True, is_repeated=True,  is_message=False)
_r("NsJailConfig", "seccomp_log",         number=76, proto_type="bool",   default=False, cli_flag="--seccomp_log",   cli_supported=True, is_repeated=False, is_message=False)

# Cgroup v1 memory
_r("NsJailConfig", "cgroup_mem_max",      number=77, proto_type="uint64", default=0,                      cli_flag="--cgroup_mem_max",      cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_mem_memsw_max",number=78, proto_type="uint64", default=0,                      cli_flag="--cgroup_mem_memsw_max",cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_mem_swap_max", number=79, proto_type="int64",  default=-1,                     cli_flag="--cgroup_mem_swap_max", cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_mem_mount",    number=80, proto_type="string", default="/sys/fs/cgroup/memory", cli_flag=None,                   cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_mem_parent",   number=81, proto_type="string", default="NSJAIL",               cli_flag=None,                   cli_supported=False, is_repeated=False, is_message=False)

# Cgroup v1 pids
_r("NsJailConfig", "cgroup_pids_max",    number=82, proto_type="uint64", default=0,                   cli_flag="--cgroup_pids_max", cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_pids_mount",  number=83, proto_type="string", default="/sys/fs/cgroup/pids", cli_flag=None,              cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_pids_parent", number=84, proto_type="string", default="NSJAIL",            cli_flag=None,               cli_supported=False, is_repeated=False, is_message=False)

# Cgroup v1 net_cls
_r("NsJailConfig", "cgroup_net_cls_classid", number=85, proto_type="uint32", default=0,                       cli_flag="--cgroup_net_cls_classid", cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_net_cls_mount",   number=86, proto_type="string", default="/sys/fs/cgroup/net_cls", cli_flag=None,                      cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_net_cls_parent",  number=87, proto_type="string", default="NSJAIL",                cli_flag=None,                      cli_supported=False, is_repeated=False, is_message=False)

# Cgroup v1 cpu
_r("NsJailConfig", "cgroup_cpu_ms_per_sec", number=88, proto_type="uint32", default=0,                   cli_flag="--cgroup_cpu_ms_per_sec", cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_cpu_mount",      number=89, proto_type="string", default="/sys/fs/cgroup/cpu", cli_flag=None,                     cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "cgroup_cpu_parent",     number=90, proto_type="string", default="NSJAIL",            cli_flag=None,                     cli_supported=False, is_repeated=False, is_message=False)

# Cgroup v2
_r("NsJailConfig", "cgroupv2_mount",   number=91, proto_type="string", default="/sys/fs/cgroup", cli_flag=None,                 cli_supported=False, is_repeated=False, is_message=False)
_r("NsJailConfig", "use_cgroupv2",     number=92, proto_type="bool",   default=False,            cli_flag="--use_cgroupv2",     cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "detect_cgroupv2",  number=93, proto_type="bool",   default=False,            cli_flag="--detect_cgroupv2",  cli_supported=True,  is_repeated=False, is_message=False)

# Networking
_r("NsJailConfig", "iface_no_lo",    number=94, proto_type="bool",   default=False,          cli_flag="--iface_no_lo",    cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "iface_own",      number=95, proto_type="string", default=[],             cli_flag="--iface_own",      cli_supported=True,  is_repeated=True,  is_message=False)
_r("NsJailConfig", "macvlan_iface",  number=96, proto_type="string", default=None,           cli_flag="--macvlan_iface",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_ip",  number=97, proto_type="string", default="192.168.0.2",  cli_flag="--macvlan_vs_ip",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_nm",  number=98, proto_type="string", default="255.255.255.0",cli_flag="--macvlan_vs_nm",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_gw",  number=99, proto_type="string", default="192.168.0.1",  cli_flag="--macvlan_vs_gw",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_ma",  number=100, proto_type="string", default="",            cli_flag="--macvlan_vs_ma",  cli_supported=True,  is_repeated=False, is_message=False)
_r("NsJailConfig", "macvlan_vs_mo",  number=101, proto_type="string", default="private",     cli_flag="--macvlan_vs_mo",  cli_supported=True,  is_repeated=False, is_message=False)

# Traffic rules
_r("NsJailConfig", "traffic_rule", number=102, proto_type="message", default=[], cli_flag=None, cli_supported=False, is_repeated=True,  is_message=True)

# User-mode networking
_r("NsJailConfig", "user_net", number=103, proto_type="message", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=True)

# Execution binary
_r("NsJailConfig", "exec_bin", number=104, proto_type="message", default=None, cli_flag=None, cli_supported=False, is_repeated=False, is_message=True)

del _r
