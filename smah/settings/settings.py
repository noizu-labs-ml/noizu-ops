import os
import yaml
import logging
from typing import Optional
from smah.settings.user import User
from smah.settings.system import System
from smah.settings.inference import Inference

class Settings:
    CONFIG_VSN = "0.0.1"

    @staticmethod
    def config_vsn() -> str:
        return Settings.CONFIG_VSN

    @staticmethod
    def default_config() -> str:
        return os.path.expanduser("~/.smah/config.yaml")

    @staticmethod
    def vsn_supported(vsn: Optional[str]) -> bool:
        """
        Checks if the provided version is supported.

        Args:
            vsn (Optional[str]): The version string to check.

        Returns:
            bool: True if the version is supported, False otherwise.
        """
        if not vsn:
            return False
        return vsn <= Settings.config_vsn()

    def __init__(self, config = None):
        self.vsn: Optional[str] = None
        self.config: str = config or self.default_config()
        self.user: Optional[User] = None
        self.system: Optional[System] = None
        self.inference: Optional[Inference] = None
        self.load()

    def is_configured(self):
        """
        Checks if the settings are fully configured.

        Returns:
            bool: True if the settings are configured, False otherwise.
        """
        if not self.user or not self.user.is_configured():
            return False
        if not self.system or not self.system.is_configured():
            return False
        #if not self.inference or not self.inference.is_configured():
        #    return False
        return True

    def load(self) -> None:
        """
        Loads the profile from the profile path and sets the configuration values.
        """
        if os.path.exists(self.config):
            try:
                with open(self.config, 'r') as file:
                    config_data = yaml.safe_load(file)
                    vsn = config_data.get("vsn")
                    if self.vsn_supported(vsn):
                        self.vsn = vsn
                        self.user = User(config_data.get("user"))
                        self.system = System(config_data.get("system"))
                        self.inference = Inference(config_data.get("inference"))
                    else:
                        logging.error(f"Config version {vsn} is not supported by this version of SMAH")
                        raise Exception(f"Config version {vsn} is not supported by this version of SMAH")
            except Exception as e:
                logging.error(f"Failed to load config: {str(e)}")
                raise e
        else:
            logging.error(f"Config file not found: {self.config}")

    def to_yaml(self, options = None) -> dict:
        """
        Returns the settings as a YAML dictionary.

        Returns:
            dict: The settings as a YAML dictionary.
        """
        return {
            "vsn": self.config_vsn(),
            "user": self.user.to_yaml(options=options) if self.user else None,
            "system": self.system.to_yaml(options=options) if self.system else None,
            "inference": self.inference.to_yaml(options=options) if self.inference else None
        }

    def save(self) -> None:
        """
        Saves the current settings to the profile path.
        """
        try:
            os.makedirs(os.path.dirname(self.config), exist_ok=True)
            with open(self.config, 'w') as file:
                yaml_content = yaml.dump(self.to_yaml())
                file.write(yaml_content)
        except Exception as e:
            raise RuntimeError(f"Failed to save profile: {str(e)}")