from .base_info import BaseInfo
import subprocess

class LinuxInfo(BaseInfo):
    """
    Represents Linux-specific OS details.

    Attributes:
        errors (list): List of errors encountered during initialization.
        source (str): The source of the OS details.
        details (dict): The OS details.
        vsn (str): Version string.
        configured (bool): Indicates if the details are configured.
    """

    @staticmethod
    def kind():
        """
        Returns the kind of the OS details.

        Returns:
            str: The kind of the OS details.
        """
        return "Linux"

    @staticmethod
    def os_release_details():
        """
        Retrieves OS release details from /etc/os-release.

        Returns:
            tuple: A tuple containing the source and details dictionary.
        """

        try:
            # Attempt to parse /etc/os-release first
            distro_info = {}
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
            for line in lines:
                parts = line.strip().split('=')
                if len(parts) == 2:
                    key = parts[0].strip().lower().replace('_', '-')
                    value = parts[1].strip().strip('"')
                    distro_info[key] = value
            return "os_release", distro_info
        except (FileNotFoundError, PermissionError):
            return None

    @staticmethod
    def uname_details():
        """
        Retrieves OS details using the uname command.

        Returns:
            tuple: A tuple containing the source and details dictionary.
        """

        try:
            uname_info = subprocess.check_output(['uname', '-a']).decode('utf-8').strip().split()
            distro_info = {'os_type': uname_info[0], 'os_release': uname_info[2], 'os_version': uname_info[3]}
            return "uname", distro_info
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
            return None

    @staticmethod
    def proc_details():
        """
        Retrieves OS details from /proc/version.

        Returns:
            tuple: A tuple containing the source and details dictionary.
        """
        try:
            # Fallback to parsing /proc/version
            with open('/proc/version', 'r') as f:
                version_info = f.readline().strip().split()
            distro_info = {'os_type': version_info[0], 'os_release': version_info[2], 'os_version': version_info[4]}
            return "proc", distro_info
        except (FileNotFoundError, PermissionError, IndexError):
            return None

    def __init__(self, config_data, fetch=False):
        """
        Initializes the LinuxDetails instance with the given configuration data.

        Args:
            config_data (dict): Configuration data for the OS details.
            fetch (bool): Whether to fetch the details.
        """
        super().__init__(config_data)

        if fetch:
            details = self.os_release_details() or self.uname_details() or self.proc_details()
            if details is not None:
                self.vsn = self.config_vsn()
                self.source, self.details = details
        elif config_data is not None:
            self.vsn = config_data["vsn"] if "vsn" in config_data else None
            self.source = config_data["source"] if "source" in config_data else None
            self.details = config_data["details"] if "details" in config_data else None

        if not self.errors:
            self.errors = None

        self.configured = self.is_configured()