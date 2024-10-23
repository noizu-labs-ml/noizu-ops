import textwrap
from typing import Optional

from .info import LinuxInfo, DarwinInfo, WindowsInfo, BSDInfo, BaseInfo


class OperatingSystem:
    CONFIG_VSN: str = "0.0.1"

    @staticmethod
    def config_vsn() -> str:
        """
        Returns the version of the configuration.

        Returns:
            str: The version of the configuration.
        """
        return OperatingSystem.CONFIG_VSN

    @staticmethod
    def version_supported(version) -> bool:
        """
        Checks if the given version is supported.

        Args:
            version (str): The version to check.

        Returns:
            bool: True if the version is supported, False otherwise.
        """
        if version is None:
            return False
        else:
            return version <= OperatingSystem.config_vsn()

    @staticmethod
    def load_info(config_data: Optional[dict]) -> Optional[BaseInfo]:
        """
        Loads OS-specific details from the configuration data.

        Args:
            config_data (dict): The configuration data.

        Returns:
            object: The OS-specific details.
        """
        config_data = config_data or {}
        kind = config_data.get("kind")
        if kind == "Linux":
            return LinuxInfo(config_data)
        elif kind == "Darwin (macOs)":
            return DarwinInfo(config_data)
        elif kind == "Windows":
            return WindowsInfo(config_data)
        elif kind == "BSD":
            return BSDInfo(config_data)
        elif kind:
            return BaseInfo(kind, config_data)
        else:
            return None

    def __init__(self, config_data = None):
        config_data = config_data or {}
        self.type: Optional[str] = config_data.get("type")
        self.name: Optional[str] = config_data.get("name")
        self.version: Optional[str] = config_data.get("version")
        self.release: Optional[str] = config_data.get("release")
        self.info: Optional[BaseInfo] = self.load_info(config_data.get("info"))
        self.vsn: Optional[str] = config_data.get("vsn")

    def is_configured(self):
        """
        Checks if the system is configured.

        Returns:
            bool: True if the system is configured, False otherwise.
        """
        if not self.type:
            return False
        if not self.name:
            return False
        if not self.version:
            return False
        if not self.release:
            return False
        if not self.info or not self.info.is_configured():
            return False
        if not self.vsn:
            return False
        return True

    def to_yaml(self, options = None):
        """
        Converts the system configuration to a YAML object.

        Args:
            options (dict): The options to include in the YAML object.

        Returns:
            dict: The system configuration as a YAML object.
        """
        return {
            "type": self.type,
            "name": self.name,
            "version": self.version,
            "release": self.release,
            "info": self.info.to_yaml(options=options) if self.info else None,
            "vsn": self.config_vsn()
        }

    def show(self, options = None):
        info = textwrap.indent(self.info.show(options=options), "  ") if self.info else None
        template = textwrap.dedent(
            """
            - type: {type}
            - name: {name}
            - version: {version}
            - release: {release}
            - info:
            {info}
            """
        ).strip().format(
            type=self.type,
            name=self.name,
            version=self.version,
            release=self.release,
            info=info
        )
        return template
