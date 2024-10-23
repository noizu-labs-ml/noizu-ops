from typing import Optional

import rich.box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from .operating_system import OperatingSystem
from smah.console import std_console, err_console, prompt_choice, prompt_string
import textwrap

def terminal_configurator(operating_system: Optional[OperatingSystem]) -> OperatingSystem:
    std_console.print(Markdown("### Configure Operating System"))
    operating_system = operating_system or OperatingSystem()

    if operating_system.is_configured():
        show(operating_system)
        if not Confirm.ask("edit?"):
            return operating_system

    while True:
        operating_system = prompt(operating_system)

        std_console.print("\n")
        show(operating_system, label = "Confirm Operating System Settings", border_style="green bold")
        if Confirm.ask("confirm?"):
            return operating_system

def prompt(operating_system: OperatingSystem) -> OperatingSystem:
    return operating_system

def show(operating_system: OperatingSystem, label = "Operating System Settings", border_style="white bold"):
    body = operating_system.show()
    template = Markdown(body)
    template = Panel(template, title=label, border_style=border_style, box=rich.box.ROUNDED)
    std_console.print(template)