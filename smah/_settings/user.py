import os
import textwrap
import yaml
from attr.converters import optional
from prompt_toolkit.layout import is_container

from rich.prompt import Prompt, Confirm
from rich.console import Console

class User:
    YAML_VERSION = "0.0.1"

    @staticmethod
    def version_supported(version):
        if version is None:
            return False
        else:
            return version <= User.YAML_VERSION

    def __init__(self, config_data):
        self.errors = []
        self.configured = None

        if config_data is None:
            self.errors = ["User data is missing"]
            self.name = None
            self.skill_level = None
            self.role = None
            self.about = None
            self.version = None
        else:
            self.name = config_data["name"] if "name" in config_data else None
            self.skill_level = config_data["skill_level"] if "skill_level" in config_data else None
            self.role = config_data["role"] if "role" in config_data else None
            self.about = config_data["about"] if "about" in config_data else None
            self.version = config_data["version"] if "version" in config_data else None

        if not self.errors:
            self.errors = None

        self.configured = self.is_configured()


    def is_configured(self):
        if (self.configured is None):
            return not(self.name is None or self.skill_level is None)
        else:
            return self.configured

    def terminal_configure(self, console):
        console.print("Lets get to know you", style="bold green")
        self.name = self.prompt_name(console)
        self.skill_level = self.prompt_skill_level(console)
        self.role = self.prompt_role(console)
        self.about = self.prompt_about(console)
        self.configured = None
        self.configured = self.is_configured()

    def to_yaml(self):
        return {
            "name": self.name,
            "skill_level": self.skill_level,
            "role": self.role,
            "about": self.about,
            "version": self.version if self.version is not None else User.YAML_VERSION
        }

    def prompt_name(self, console):
        message = "[bold green]What is your name?[/bold green]"
        if self.name is None:
            return Prompt.ask(message)
        else:
            console.print(f"Name: {self.name}")
            if Confirm.ask("correct?", default=False):
                return self.name
            else:
                return Prompt.ask(message)

    def prompt_skill_level(self, console):
        message = textwrap.dedent(
            """
            [bold green]What is your experience level?[/bold green]
            1 - Beginner
            2 - Intermediate
            3 - Advanced
            4 - Expert
            """
        )
        levels = {
            "1": "Beginner",
            "2": "Intermediate",
            "3": "Advanced",
            "4": "Expert"
        }
        if self.skill_level is None:
            level =  Prompt.ask(message, choices=["1", "2", "3", "4"])
            return levels[level]
        else:
            console.print(f"Experience Level: {self.skill_level}")
            if Confirm.ask("correct?", default=False):
                return self.skill_level
            else:
                level = Prompt.ask(message, choices=["1", "2", "3", "4"])
                return levels[level]

    def prompt_role(self, console):
        message = "[bold green]What is your role?[/bold green] (Developer, Tester, User, Student, Admin, ...)"
        if self.role is None:
            return Prompt.ask(message)
        else:
            console.print(f"Role: {self.role}")
            if Confirm.ask("correct?", default=False):
                return self.role
            else:
                return Prompt.ask(message)

    def prompt_about(self, console):
        message = "[bold green]Tell us about yourself[/bold green]"
        if self.about is None:
            return Prompt.ask(message)
        else:
            console.print(f"About: {self.about}")
            if Confirm.ask("correct?", default=False):
                return self.about
            else:
                return Prompt.ask(message)