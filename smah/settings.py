import os
import textwrap
import yaml
from typing import Optional, Dict, Any
from smah.inference_providers import InferenceProvider
from attr.converters import optional
from rich.prompt import Prompt, Confirm
from rich.console import Console
from smah._settings.user import User
from smah._settings.system import System
import logging

class Settings:
    YAML_VERSION = "0.0.1"
    DEFAULT_PROFILE = os.path.expanduser("~/.smah/profile.yaml")

    @staticmethod
    def default_profile(profile: Optional[str]) -> str:
        """
        Returns the default profile path if no profile is provided.

        Args:
            profile (Optional[str]): The profile path provided by the user.

        Returns:
            str: The default profile path or the provided profile path.
        """
        return Settings.DEFAULT_PROFILE if profile is None else profile

    @staticmethod
    def vsn_supported(vsn: Optional[str]) -> bool:
        """
        Checks if the provided version is supported.

        Args:
            vsn (Optional[str]): The version string to check.

        Returns:
            bool: True if the version is supported, False otherwise.
        """
        return vsn <= Settings.YAML_VERSION if vsn is not None else False

    def __init__(self, args: Any) -> None:
        """
        Initializes the Settings object with the provided arguments.

        Args:
            args (Any): The arguments provided to the Settings object.
        """
        self.args = args
        self.configured: Optional[bool] = None
        self.errors: Optional[list[str]] = []
        self.profile: str = Settings.default_profile(args.profile)
        self.vsn: Optional[str] = None
        self.user: Optional[User] = None
        self.system: Optional[System] = None
        self.providers = InferenceProvider(
            openai_api_tier=args.openai_api_tier,
            openai_api_key=args.openai_api_key,
            openai_api_org=args.openai_api_org,
        )

        self.load_profile()

    def load_profile(self) -> None:
        """
        Loads the profile from the profile path and sets the configuration values.
        """
        if os.path.exists(self.profile):
            try:
                with open(self.profile, 'r') as file:
                    config_data = yaml.safe_load(file)
                    vsn = config_data.get("vsn")
                    if self.vsn_supported(vsn):
                        self.vsn = vsn
                        self.user = User(config_data.get("user"))
                        self.system = System(config_data.get("system"))
                        self.errors.extend(self.user.errors or [])
                        self.errors.extend(self.system.errors or [])
                    else:
                        logging.error(f"Config version {vsn} is not supported by this version of SMAH")
                        self.errors.append(f"Config version {vsn} is not supported by this version of SMAH")
            except Exception as e:
                logging.error(f"Failed to load profile: {str(e)}")
                self.errors.append(f"Failed to load profile: {str(e)}")
        if not self.errors:
            self.errors = None
        self.configured = self.is_configured()

    def status(self) -> str:
        """
        Returns the status of the user and system configurations.

        Returns:
            str: The status of the user and system configurations.
        """
        user_status = self.user.status() if self.user else "Not Available"
        system_status = self.system.status() if self.system else "Not Available"
        status = textwrap.dedent(
            """
            ## Profile
            User Info
            {us}


            ## System
            System Details

            {ss}
            """
        ).strip().format(us=user_status, ss=system_status)
        return status

    def is_configured(self) -> bool:
        """
        Checks if the settings are fully configured.

        Returns:
            bool: True if the settings are configured, False otherwise.
        """
        if self.configured is None:
            if not self.vsn or not self.user or not self.system:
                return False
            if not self.user.is_configured() or not self.system.is_configured():
                return False
            return True
        return self.configured

    def configure(self) -> None:
        """
        Configures the settings using either GUI or terminal based on the arguments.
        """
        if self.args.gui:
            self.gui_configure()
        else:
            self.terminal_configure()
        self.configured = self.is_configured()
        self.save()

    def save(self) -> None:
        """
        Saves the current settings to the profile path.
        """
        try:
            os.makedirs(os.path.dirname(self.profile), exist_ok=True)
            with open(self.profile, 'w') as file:
                yaml_content = yaml.dump(self.to_yaml())
                file.write(yaml_content)
        except Exception as e:
            raise RuntimeError(f"Failed to save profile: {str(e)}")

    def to_yaml(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Converts the settings to a YAML-compatible dictionary.

        Args:
            options (Optional[Dict[str, Any]]): Additional options for the conversion.

        Returns:
            Dict[str, Any]: The settings as a YAML-compatible dictionary.
        """
        options = options or {}
        return {
            "vsn": self.vsn or Settings.YAML_VERSION,
            "user": self.user.to_yaml(options=options) if self.user else None,
            "system": self.system.to_yaml(options=options) if self.system else None
        }

    def terminal_configure(self) -> None:
        """
        Configures the settings using the terminal interface.
        """
        console = Console()
        console.print(f"Lets Setup Your Profile: {self.profile}")
        self.vsn = Settings.YAML_VERSION
        self.user = self.user or User(None)
        self.user.terminal_configure(console)
        self.system = self.system or System(None)
        self.system.terminal_configure(console)

    def gui_configure(self) -> None:
        """
        Configures the settings using the GUI interface.
        """
        print("GUI MODE", self.args.gui)
        self.terminal_configure()