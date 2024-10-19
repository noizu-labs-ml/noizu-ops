import os
import textwrap

import rich.console
import rich.prompt
import yaml

import smah.smah_console


"""
Determine Config Path
"""
def config_file(config = None):
    return os.path.expanduser("~/.smah/config.yaml") if config is None else config

"""
Check if config version is supported.
"""
def version_supported(version):
    return version <= config_version()

"""
Default config version.
"""
def config_version():
    return "0.0.1"

"""
smah system details.
"""
class Config:
    def __init__(self, config=None):
        self.config = config_file(config)
        self.version = None
        self.errors = None
        self.user = None

        if os.path.exists(self.config):
            with open(self.config, 'r') as file:
                config_data = yaml.safe_load(file)
                version = config_data["version"]
                if version_supported(version):
                    self.version = version
                    if "user" in config_data:
                        self.user = self.User(config_data["user"])
                else:
                    self.errors = [f"Config version {version} is not supported by this version of SMAH"]

    """
    Check if config is fully configured.
    """
    def configured(self):
        if self.errors is not None:
            return False
        if self.version is None:
            return False
        if self.user is None or self.user.configured() is False:
            return False
        return True

    """
    Interactive configuration
    """
    def configure(self):
        console = rich.console.Console()
        if self.errors is not None:
            self.configure_error(console)
        else:
            console.print("Welcome to SMAH: lets get started", style="bold green")

            # Version
            self.version = config_version()

            # User
            if self.user is None:
                self.user = self.User({})
            if self.user.configured() is False:
                self.user.configure(console)

            # Save
            self.save()

    """
    Configuration error message
    """
    def configure_error(self, console):
        console.print("[bold red]Errors in configuration:[/bold red] must be resolved manually")
        for error in self.errors:
            console.print(error, style="bold red")
        raise Exception("Configuration errors must be resolved manually")

    """
    Save configuration to file
    """
    def save(self):
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.config), exist_ok=True)

        # Write the YAML configuration to the file
        with open(self.config, 'w') as file:
            yaml_content = yaml.dump(self.to_yaml())
            file.write(yaml_content)

    """
    Convert configuration to YAML dictionary
    """
    def to_yaml(self):
        user = self.user.to_yaml() if self.user is not None else None
        return {
            "version": self.version,
            "user": user
        }

    """
    User Configuration
    """
    class User:
        def __init__(self, config_data):
            self.version = None
            self.name = None
            self.level = None
            self.errors = None
            if config_data is not None:
                self.version = config_data["version"] if "version" in config_data else None
                self.name = config_data["name"] if "name" in config_data else None
                self.level = config_data["level"] if "level" in config_data else None


        """
        Check if configured.
        """
        def configured(self):
            if self.errors is not None:
                return False
            if self.version is None:
                return False
            if self.name is None:
                return False
            if self.level is None:
                return False
            return True

        """
        Interactive configuration
        """
        def configure(self, console):
            if self.errors is not None:
                self.configure_error(console)
            else:
                console.print("Lets get to know you", style="bold green")
                self.name = self.configure_name(console)
                self.level = self.configure_level(console)
                self.version = config_version()

        """
        Configure user name
        """
        def configure_name(self, console):
            message = "What is your name?"
            if self.name is None:
                return rich.prompt.Prompt.ask(message)
            else:
                console.print(f"Name: {self.name}")
                if not(rich.prompt.Confirm.ask("edit?", default=False)):
                    return self.name
                else:
                    return rich.prompt.Prompt.ask(message)

        """
        Configure user experience level
        """
        def configure_level(self, console):
            prompt = "Select User Experience Level:"
            choices = ["Beginner", "Intermediate", "Advanced", "Expert"]

            if self.level is None:
                return smah.smah_console.select_prompt(console, prompt, choices)
            else:
                console.print(f"Level: {self.level}")
                if not(rich.prompt.Confirm.ask("edit?", default=False)):
                    return self.level
                else:
                    return smah.smah_console.select_prompt(console, prompt, choices)

        """
        Configuration error message
        """
        def configure_error(self, console):
            console.print("[bold red]Errors in User configuration:[/bold red] must be resolved manually")
            for error in self.errors:
                console.print(error, style="bold red")
            raise Exception("Configuration errors must be resolved manually")

        """
        Convert configuration to YAML dictionary
        """
        def to_yaml(self):
            return {
                "version": self.version,
                "name": self.name,
                "level": self.level
            }

    class System:
        def __init__(self, config_data):
            self.version = None
            self.type = None
            self.os = None
            self.errors = None
            if config_data is not None:
                self.version = config_data["version"] if "version" in config_data else None
                self.type = config_data["type"] if "type" in config_data else None
                self.os = config_data["os"] if "os" in config_data else None

        def configured(self):
            if self.errors is not None:
                return False
            if self.version is None:
                return False
            if self.type is None:
                return False
            if self.os is None:
                return False
            return True

        def configure(self, console):
            if self.errors is not None:
                self.configure_error(console)
            else:
                console.print("Lets get to know your system", style="bold green")
                self.type = self.configure_type(console)
                self.os = self.configure_os(console)
                self.version = config_version()

        def configure_type(self, console):
            prompt = "Select Operating System Type"
            choices = ["linux", "windows", "macos"]
            if self.type is None:
                return smah.smah_console.select_prompt(console, prompt, choices)
            else:
                console.print(f"OS Type: {self.type}")
                if not(rich.prompt.Confirm.ask("edit?", default=False)):
                    return self.type
                else:
                    return smah.smah_console.select_prompt(console, prompt, choices)

        def configure_os(self, console):
            return "Ubuntu 22.04"

