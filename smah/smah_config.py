import os
import textwrap

import rich.console
import rich.prompt
import yaml

def config_file(config = None):
    return os.path.expanduser("~/.smah/config.yaml") if config is None else config

def version_supported(version):
    return version <= config_version()

def config_version():
    return "0.0.1"

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

    def configured(self):
        if self.errors is not None:
            return False
        if self.version is None:
            return False
        if self.user is None or self.user.configured() is False:
            return False
        return True

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

    def configure_error(self, console):
        console.print("[bold red]Errors in configuration:[/bold red] must be resolved manually")
        for error in self.errors:
            console.print(error, style="bold red")
        raise Exception("Configuration errors must be resolved manually")

    def save(self):
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.config), exist_ok=True)

        # Write the YAML configuration to the file
        with open(self.config, 'w') as file:
            yaml_content = yaml.dump(self.to_yaml())
            file.write(yaml_content)

    def to_yaml(self):
        user = self.user.to_yaml() if self.user is not None else None
        return {
            "version": self.version,
            "user": user
        }

    class User:
        def __init__(self, config_data):
            self.name = None
            self.level = None
            self.version = None
            self.errors = None
            if config_data is not None:
                self.name = config_data["name"] if "name" in config_data else None
                self.level = config_data["level"] if "level" in config_data else None

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

        def configure(self, console):
            if self.errors is not None:
                self.configure_error(console)
            else:
                console.print("Lets get to know you", style="bold green")
                self.name = self.configure_name(console)
                self.level = self.configure_level(console)
                self.version = config_version()

        def configure_name(self, console):
            message = "What is your name?"
            if self.name is None:
                return rich.prompt.Prompt.ask(message)
            else:
                console.print(f"Name: {self.name}")
                if rich.prompt.Confirm.ask("Is this correct?"):
                    return self.name
                else:
                    return rich.prompt.Prompt.ask(message)

        def configure_level(self, console):
            message = textwrap.dedent("""
            What is your experience level?
            1 - Beginner
            2 - Intermediate
            3 - Advanced
            4 - Expert
            """)

            levels = {
                "1": "Beginner",
                "2": "Intermediate",
                "3": "Advanced",
                "4": "Expert"
            }


            if self.level is None:
                level = rich.prompt.Prompt.ask(message, choices=["1", "2", "3", "4"])
                return levels[level]
            else:
                console.print(f"Level: {self.level}")
                if rich.prompt.Confirm.ask("Is this correct?"):
                    return self.level
                else:
                    level = rich.prompt.Prompt.ask(message, choices=["1", "2", "3", "4"])
                    return levels[level]

        def configure_error(self, console):
            console.print("[bold red]Errors in User configuration:[/bold red] must be resolved manually")
            for error in self.errors:
                console.print(error, style="bold red")
            raise Exception("Configuration errors must be resolved manually")

        def to_yaml(self):
            return {
                "version": self.version,
                "name": self.name,
                "level": self.level
            }

