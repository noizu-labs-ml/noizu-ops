from .info import LinuxInfo, DarwinInfo, WindowsInfo, BSDInfo

class OperatingSystem:
    @staticmethod
    def load_info(config_data):
        """
        Loads OS-specific details from the configuration data.

        Args:
            config_data (dict): The configuration data.

        Returns:
            object: The OS-specific details.
        """
        kind = config_data.get("kind")
        if kind == "Linux":
            return LinuxInfo(config_data)
        elif kind == "Darwin":
            return DarwinInfo(config_data)
        elif kind == "Windows":
            return WindowsInfo(config_data)
        elif kind == "BSD":
            return BSDInfo(config_data)
        else:
            return None

    def __init__(self, config_data = None):
        config_data = config_data or {}
        self.type = config_data.get("type")
        self.name = config_data.get("name")
        self.version = config_data.get("version")
        self.release = config_data.get("release")
        self.info = self.load_info(config_data.get("info", {}))
        self.vsn = config_data.get("vsn")

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
        if not self.info:
            return False
        if not self.vsn:
            return False

        return True