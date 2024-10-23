from .settings import Settings
from .user import User
from smah.console import std_console, err_console
import smah.settings
from rich.markdown import Markdown

def configurator(settings: Settings, gui=False) -> Settings:
    """
    Interactive Setup
    """
    if gui:
        return terminal_configurator(settings)
    else:
        return terminal_configurator(settings)

def terminal_configurator(settings: Settings) -> Settings:
    std_console.print(Markdown("# Configure"))
    smah.settings.user.configurator.terminal_configurator(settings.user)
    return settings