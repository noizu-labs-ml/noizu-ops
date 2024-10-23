from typing import Optional

import rich.box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from .user import User
from smah.console import std_console, err_console, prompt_choice, prompt_string
import textwrap

def user_terminal_configurator(user: Optional[User]) -> User:
    std_console.print(Markdown("## Configure User"))
    user = user or User()

    if user.is_configured():
        show(user)
        if not Confirm.ask("edit?", default=False):
            return user
        else:
            std_console.print("\n")

    while(True):
        user = prompt(user)

        std_console.print("\n")
        show(user, label = "Confirm User Settings", border_style="green bold")
        if Confirm.ask("confirm?", default=True):
            return user

def prompt(user: User) -> User:
    user.name = prompt_string("Name", user.name, label="What is your name?")
    user.system_admin_experience = prompt_choice(
        "Experience Level",
        user.system_admin_experience,
        label = "What is your experience level?",
        options = ["Novice", "Beginner", "Intermediate", "Advanced", "Expert"]
    )
    user.role = prompt_choice(
        "Role",
        user.role,
        label = "What is your role?",
        options = ["Developer", "Administrator", "Student", "User"],
        other=True
    )
    user.about = prompt_string(
        "About",
        user.about,
        label="Tell us about yourself"
    )
    return user

def show(user: User, border_style="white bold", label = "User Settings"):
    body = user.show()
    template = Markdown(body)
    template = Panel(template, title=label, border_style=border_style, box=rich.box.ROUNDED)
    std_console.print(template)