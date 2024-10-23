from typing import Optional
import platform
import rich.box
import logging
import os
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from .info import BaseInfo, LinuxInfo, WindowsInfo, DarwinInfo, BSDInfo
from .operating_system import OperatingSystem
from smah.console import std_console, err_console, prompt_choice, prompt_string

def operating_system_terminal_configurator(operating_system: Optional[OperatingSystem]) -> OperatingSystem:
    std_console.print(Markdown("### Configure Operating System"))
    operating_system = operating_system or OperatingSystem()

    if operating_system.is_configured():
        show(operating_system)
        if not Confirm.ask("edit?", default=False):
            return operating_system

    while True:
        operating_system = prompt(operating_system)

        std_console.print("\n")
        show(operating_system, label = "Confirm Operating System Settings", border_style="green bold")
        if Confirm.ask("confirm?", default=True):
            return operating_system

def details():
    os_type = None
    release = None
    version = None
    name = None
    try:
        os_type = platform.system()
        release = platform.release()
        version = platform.version()
        name = os.name
    except Exception as e:
        logging.error("Exception {e}", str(e))

    if os_type == "Darwin":
        os_type = "Darwin (macOs)"

    return {
        "type": os_type,
        "release": release,
        "version": version,
        "name": name,
    }


def prompt(operating_system: OperatingSystem) -> OperatingSystem:
    d = details()
    if Prompt.ask("Automatically Load Operating System Details"):
        operating_system.type = d["type"]
        operating_system.name = d["name"]
        operating_system.version = d["version"]
        operating_system.release = d["release"]
        # TODO - load existing
        operating_system.info = load_info(d["type"])
    else:
        operating_system.type = prompt_choice("Type", operating_system.type or d.get("type"), options=["Linux", "Windows", "Darwin (macOs)", "FreeBSD", "OpenBSD", "NetBSD"], other=True)
        operating_system.name = prompt_string("Name", operating_system.name or d.get("name"))
        operating_system.version = prompt_string("Version", operating_system.version or d.get("version"))
        operating_system.release = prompt_string("Release", operating_system.release or d.get("release"))
        # TODO - load existing
        operating_system.info = load_info(d["type"])
    return operating_system

def load_info(os_type: str) -> Optional[BaseInfo]:
    if os_type == "Linux":
        return LinuxInfo(fetch=True)
    elif os_type == "Windows":
        return WindowsInfo(fetch=True)
    elif os_type == "Darwin (macOs)":
        return DarwinInfo(fetch=True)
    elif "BSD" in os_type:
        return BSDInfo(fetch=True)
    else:
        return BaseInfo(os_type, fetch=True)

def show(operating_system: OperatingSystem, label = "Operating System Settings", border_style="white bold"):
    body = operating_system.show()
    template = Markdown(body)
    template = Panel(template, title=label, border_style=border_style, box=rich.box.ROUNDED)
    std_console.print(template)