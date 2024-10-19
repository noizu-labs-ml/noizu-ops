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
    def vsn_supported(vsn):
        if vsn is None:
            return False
        else:
            return vsn <= User.YAML_VERSION

    def __init__(self, config_data):
        self.errors = []
        self.configured = None

        if config_data is None:
            self.errors = ["User data is missing"]
            self.name = None
            self.experience_level = None
            self.role = None
            self.about = None
            self.vsn = None
        else:
            self.name = config_data["name"] if "name" in config_data else None
            self.experience_level = config_data["experience_level"] if "experience_level" in config_data else None
            self.role = config_data["role"] if "role" in config_data else None
            self.about = config_data["about"] if "about" in config_data else None
            self.vsn = config_data["vsn"] if "vsn" in config_data else None

        if not self.errors:
            self.errors = None

        self.configured = self.is_configured()

    def status(self):
        status = f"""
        - name: {self.name}
        - role: {self.role}
        - experience: {self.experience_level}
        - about:
        {textwrap.indent(self.about or "","  ")}
        """
        return textwrap.dedent(status).strip()

    def is_configured(self):
        if (self.configured is None):
            return not(self.name is None or self.experience_level is None)
        else:
            return self.configured

    def terminal_configure(self, console):
        console.print("Lets get to know you", style="bold green")
        self.name = self.prompt_name(console)
        self.experience_level = self.prompt_experience_level(console)
        self.role = self.prompt_role(console)
        self.about = self.prompt_about(console)
        self.configured = None
        self.configured = self.is_configured()

    def to_yaml(self, options = {}):
        return {
            "vsn": self.vsn if self.vsn is not None else User.YAML_VERSION,
            "name": self.name,
            "experience_level": self.experience_level,
            "role": self.role,
            "about": self.about,
        }

    def prompt_name(self, console):
        message = "[bold green]What is your name?[/bold green]"
        if self.name is None:
            return Prompt.ask(message)
        else:
            console.print(f"Name: {self.name}")
            if Confirm.ask("correct?", default=True):
                return self.name
            else:
                return Prompt.ask(message, default = self.name)

    def prompt_experience_level(self, console):
        message = textwrap.dedent(
            """
            [bold green]What is your experience level?[/bold green]
            0 - Novice
            1 - Beginner
            2 - Intermediate
            3 - Advanced
            4 - Expert
            """
        )
        levels = {
            "0": "Novice",
            "1": "Beginner",
            "2": "Intermediate",
            "3": "Advanced",
            "4": "Expert"
        }
        reverse_levels = {
            "Novice": "0",
            "Beginner": "1",
            "Intermediate": "2",
            "Advanced": "3",
            "Expert": "4"
        }

        if self.experience_level is None:
            level =  Prompt.ask(message, choices=["0","1", "2", "3", "4"])
            return levels[level]
        else:
            console.print(f"Experience Level: {self.experience_level}")
            if Confirm.ask("correct?", default=True):
                return self.experience_level
            else:
                default_level = reverse_levels[self.experience_level] if self.experience_level in reverse_levels else None
                level = Prompt.ask(message, choices=["1", "2", "3", "4"], default = default_level)
                return levels[level]

    def prompt_role(self, console):
        message = "[bold green]What is your role?[/bold green] (Developer, Tester, User, Student, Admin, ...)"
        if self.role is None:
            return Prompt.ask(message)
        else:
            console.print(f"Role: {self.role}")
            if Confirm.ask("correct?", default=True):
                return self.role
            else:
                return Prompt.ask(message, default=self.role)

    def prompt_about(self, console):
        message = "[bold green]Tell us about yourself[/bold green]"
        if self.about is None:
            return Prompt.ask(message)
        else:
            console.print(f"About: {self.about}")
            if Confirm.ask("correct?", default=True):
                return self.about
            else:
                a = Prompt.ask(message)
                if a is None or a == "":
                    return self.about
                else:
                    return a