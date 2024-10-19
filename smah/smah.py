from smah.config import config
from rich.console import Console
from rich.prompt import Confirm

console = Console()

def main():
    if not config.is_configured():
        config.config_missing(console = console)
    else:
        smahConfig = config.Config()
        print("smah user = ", smahConfig.user)