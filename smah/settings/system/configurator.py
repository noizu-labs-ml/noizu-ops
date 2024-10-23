from typing import Optional

import rich.box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from .system import System
from smah.console import std_console, err_console, prompt_choice, prompt_string

def terminal_configurator(system: Optional[System]) -> System:
    std_console.print(Markdown("## Configure System"))
    system = system or System()

    if system.is_configured():
        show(system)
        if not Confirm.ask("edit?"):
            return system

    while True:
        system = prompt(system)

        std_console.print("\n")
        show(system, label = "Confirm System Settings", border_style="green bold")
        if Confirm.ask("confirm?"):
            return system

def prompt(system: System) -> System:
    return system

def show(system: System, label = "System Settings", border_style="white bold"):
    body = system.show()
    template = Markdown(body)
    template = Panel(template, title=label, border_style=border_style, box=rich.box.ROUNDED)
    std_console.print(template)