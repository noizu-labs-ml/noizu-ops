from .base_info import BaseInfo
import subprocess

class BSDInfo(BaseInfo):
    """
    Represents BSD-specific OS details.

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
        return "BSD"

    @staticmethod
    def uname_details():
        """
        Retrieves OS details using the uname command.

        Returns:
            tuple: A tuple containing the source and details dictionary.
        """

        try:
            version_info = subprocess.check_output(['uname', '-v']).decode('utf-8')
            version_dict = {}
            parts = version_info.strip().split(':')
            if len(parts) == 2:
                key, value = parts
                key = key.strip().replace(' ', '-').lower()
                value = value.strip()
                version_dict[key] = value
            return "uname", version_dict
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def __init__(self, config_data, fetch=False):
        """
        Initializes the BSDDetails instance with the given configuration data.

        Args:
            config_data (dict): Configuration data for the OS details.
            fetch (bool): Whether to fetch the details.
        """
        super().__init__(config_data)

        if fetch:
            details = self.uname_details()
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