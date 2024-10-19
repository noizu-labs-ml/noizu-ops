import os
import textwrap
import yaml
from attr.converters import optional

from rich.prompt import Prompt, Confirm
from rich.console import Console

from smah._settings.user import User
from smah._settings.system import System

class Settings:
    YAML_VERSION = "0.0.1"
    DEFAULT_PROFILE = os.path.expanduser("~/.smah/profile.yaml")

    @staticmethod
    def default_profile(profile):
        return Settings.DEFAULT_PROFILE if profile is None else profile

    @staticmethod
    def vsn_supported(vsn):
        if vsn is None:
            return False
        else:
            return vsn <= Settings.YAML_VERSION

    def __init__(self, args):
        # status
        self.args = args
        self.configured = None
        self.errors = []
        self.profile = Settings.default_profile(args.profile)

        # state
        self.vsn = None
        self.user = None
        self.system = None

        if os.path.exists(self.profile):
            with open(self.profile, 'r') as file:
                config_data = yaml.safe_load(file)
                vsn = config_data["vsn"] if "vsn" in config_data else None
                if self.vsn_supported(vsn):
                    self.vsn = vsn

                    # Load User Settings
                    self.user = User(config_data["user"] if "user" in config_data else None)
                    if self.user.errors:
                        self.errors = self.errors + self.user.errors

                    # Load System Settings
                    self.system = System(config_data["system"] if "system" in config_data else None)
                    if self.system.errors:
                        self.errors = self.errors + self.system.errors

                else:
                    self.errors = [f"Config version {vsn} is not supported by this version of SMAH"]
        if not self.errors:
            self.errors = None
        self.configured = self.is_configured()

    def status(self):
        user = self.user.status() if self.user is not None else None
        system = self.system.status() if self.system is not None else None

        status = "## Profile\nUser Info\n\n"
        status += user or "Not Available"
        status += "\n\n## System\nSystem Details.\n\n"
        status += system or "Not Available"
        return textwrap.dedent(status).strip()

    def is_configured(self):
        if (self.configured is None):
            if self.vsn is None or self.user is None or self.system is None:
                return False
            elif self.user.is_configured() is False:
                return False
            elif self.system.is_configured() is False:
                return False
            else:
                return True
        else:
            return self.configured

    def configure(self):
        if self.args.gui:
            self.gui_configure()
        else:
            self.terminal_configure()
        self.configured = None
        self.configured = self.is_configured()
        self.save()

    def save(self):
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.profile), exist_ok=True)

        # Write the YAML configuration to the file
        with open(self.profile, 'w') as file:
            yaml_content = yaml.dump(self.to_yaml())
            file.write(yaml_content)

    def to_yaml(self):

        return {
            "vsn": self.vsn if self.vsn is not None else Settings.YAML_VERSION,
            "user": self.user.to_yaml() if self.user is not None else None,
            "system": self.system.to_yaml() if self.system is not None else None
        }

    def terminal_configure(self):
        console = Console()
        console.print(f"Lets Setup Your Profile: {self.profile}")
        self.vsn = Settings.YAML_VERSION
        if self.user is None:
            self.user = User(None)
        self.user.terminal_configure(console)

        if self.system is None:
            self.system = System(None)
        self.system.terminal_configure(console)

    def gui_configure(self):
        print("GUI MODE", self.args.gui)
        self.terminal_configure()