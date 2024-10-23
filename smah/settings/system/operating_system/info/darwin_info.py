from typing import Optional, Tuple

from .base_info import BaseInfo
import subprocess


class DarwinInfo(BaseInfo):
    """
    Represents Darwin (macOS)-specific OS details.

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
        return "Darwin (macOs)"

    @staticmethod
    def info() -> Optional[Tuple]:
        return DarwinInfo.darwin_details()

    @staticmethod
    def darwin_details() -> Optional[Tuple]:
        """
        Retrieves OS details using the sw_vers command.

        Returns:
            tuple: A tuple containing the source and details dictionary.
        """

        try:
            version_info = subprocess.check_output(['sw_vers']).decode('utf-8')
            version_dict = {}
            for line in version_info.split('\n'):
                parts = line.strip().split(':')
                if len(parts) == 2:
                    key, value = parts
                    key = key.strip().replace(' ', '-').lower()
                    value = value.strip()
                    version_dict[key] = value
            return "sw-vers", version_dict
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def __init__(self, config_data = None, fetch=False):
        """
        Initializes the DarwinDetails instance with the given configuration data.

        Args:
            config_data (dict): Configuration data for the OS details.
            fetch (bool): Whether to fetch the details.
        """
        super().__init__("Darwin (macOs)", config_data=config_data, fetch=fetch)
