import os
import argparse
import textwrap

import rich
from rich.markdown import Markdown

from smah.settings import Settings

def extract_args():
    parser = argparse.ArgumentParser(description="SMAH Command Line Tool")
    parser.add_argument('-q', '--query', type=str, help='The Query to process')
    parser.add_argument('-p', '--profile', type=str, help='Path to alternative config file')
    parser.add_argument('--gui', action=argparse.BooleanOptionalAction, help='Run in GUI mode', default=True)
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Set Verbosity Level, such as -vv")
    args = parser.parse_args()
    return parser, args

def main():
    parser, args = extract_args()
    settings = Settings(args)
    if not(settings.is_configured()):
        settings.configure()

    if args.verbose > 2:
        status = settings.status() or "[Error]"
        p = "# Status\nCurrent System Status\n\n"
        p +=  status or "N/A"
        console = rich.console.Console()
        p = Markdown(p)
        console.print(p)

