import os
import argparse
import textwrap
import yaml
import rich
from rich.prompt import Prompt, Confirm
import sys
from rich.markdown import Markdown

from smah.settings import Settings
from smah.runner import Runner

def extract_args():
    parser = argparse.ArgumentParser(description="SMAH Command Line Tool")
    parser.add_argument('-q', '--query', type=str, help='The Query to process')
    parser.add_argument('-i', '--instructions', type=str, help='The Instruction File to process')
    parser.add_argument('--profile', type=str, help='Path to alternative config file')
    parser.add_argument('--openai-api-tier', type=int, help='OpenAI Tier')
    parser.add_argument('--openai-api-key', type=str, help='OpenAI Api Key')
    parser.add_argument('--openai-api-org', type=str, help='OpenAI Api Org')

    parser.add_argument('--gui', action=argparse.BooleanOptionalAction, help='Run in GUI mode', default=True)
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Set Verbosity Level, such as -vv")
    args = parser.parse_args()

    # Grab Pipe
    pipe = None
    if sys.stdin.isatty():
        pipe = None
    else:
        pipe = sys.stdin.read()

    return parser, args, pipe

def log_settings(console, settings):
    contents = settings.to_yaml({"stats": True})
    header = textwrap.dedent("""
            Settings
            ================

            """)
    body = header + "```yaml\n" + yaml.dump({"settings": contents}, sort_keys=False) + "\n```"
    body = Markdown(body)
    console.print(body)

def main():
    console = rich.console.Console()
    parser, args, pipe = extract_args()
    settings = Settings(args)
    if not(settings.is_configured()):
        settings.configure()
        log_settings(console, settings)
    else:
        if args.verbose > 2:
            log_settings(console, settings)

    runner = Runner(args, settings)

    if args.query:
        if pipe:
            runner.pipe(query = args.query, pipe = pipe)
        else:
            runner.query(query = args.query)
    elif args.instructions:
        with open(args.instructions, 'r') as file:
            instructions = file.read()
            if instructions is not None:
                if pipe:
                    runner.pipe(query=instructions, pipe=pipe)
                else:
                    runner.query(query=instructions.query)
    else:
        runner.interactive(pipe = pipe)