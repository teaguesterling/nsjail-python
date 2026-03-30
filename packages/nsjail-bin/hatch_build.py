"""Hatch build hook for nsjail-bin.

Marks the wheel as platform-specific since it contains a native binary.
"""

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class NsjailBinBuildHook(BuildHookInterface):
    PLUGIN_NAME = "nsjail-bin"

    def initialize(self, version, build_data):
        build_data["pure_python"] = False
        build_data["infer_tag"] = True
