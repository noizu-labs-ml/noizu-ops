import textwrap
from rich.prompt import Prompt, Confirm
from smah.console import std_console
class User:
    YAML_VERSION = "0.0.1"

    @staticmethod
    def vsn_supported(vsn):
        if vsn is None:
            return False
        else:
            return vsn <= User.YAML_VERSION

    def __init__(self, config_data = None):
        config_data = config_data or {}
        self.name = config_data.get("name")
        self.experience_level = config_data.get("experience_level")
        self.role = config_data.get("role")
        self.about = config_data.get("about")
        self.vsn = config_data.get("vsn")

    def is_configured(self):
        if not self.name:
            return False
        if not self.experience_level:
            return False
        if not self.role:
            return False
        if not self.about:
            return False
        return True

    def terminal_configure(self):
        std_console.print("Lets get to know you", style="bold green")
        self.name = self.prompt_name()
        self.experience_level = self.prompt_experience_level()
        self.role = self.prompt_role()
        self.about = self.prompt_about()

    def to_yaml(self):
        return {
            "vsn": User.YAML_VERSION,
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
            std_console.print(f"Name: {self.name}")
            if Confirm.ask("correct?", default=True):
                return self.name
            else:
                return Prompt.ask(message, default = self.name)

    def prompt_experience_level(self):
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
            std_console.print(f"Experience Level: {self.experience_level}")
            if Confirm.ask("correct?", default=True):
                return self.experience_level
            else:
                default_level = reverse_levels[self.experience_level] if self.experience_level in reverse_levels else None
                level = Prompt.ask(message, choices=["1", "2", "3", "4"], default = default_level)
                return levels[level]

    def prompt_role(self):
        message = "[bold green]What is your role?[/bold green] (Developer, Tester, User, Student, Admin, ...)"
        if self.role is None:
            return Prompt.ask(message)
        else:
            std_console.print(f"Role: {self.role}")
            if Confirm.ask("correct?", default=True):
                return self.role
            else:
                return Prompt.ask(message, default=self.role)

    def prompt_about(self):
        message = "[bold green]Tell us about yourself[/bold green]"
        if self.about is None:
            return Prompt.ask(message)
        else:
            std_console.print(f"About: {self.about}")
            if Confirm.ask("correct?", default=True):
                return self.about
            else:
                a = Prompt.ask(message)
                if a is None or a == "":
                    return self.about
                else:
                    return a