from rich.markdown import Markdown

from .user import User
from smah.console import std_console, err_console

def terminal_configurator(user: User | None) -> User:
    std_console.print(Markdown("## Configure User"))
    user = user or User()
    return user