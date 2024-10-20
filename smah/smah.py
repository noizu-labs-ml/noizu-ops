"""
smah.py

This module serves as the entry point for the SMAH Command Line Tool. It is responsible for parsing
command line arguments, initializing settings, and coordinating execution based on user inputs.
The module utilizes the `argparse` library for command-line argument parsing and `rich` for enhanced
console outputs.

Classes and Functions:
- extract_args: Parses and extracts command-line arguments.
- log_settings: Logs current application settings using `rich`.
- main: The primary function that sets up application configuration and executes user-specified queries.

Dependencies:
- `os`, `argparse`, `textwrap`, and `yaml` for OS operations, argument parsing, text manipulation, and YAML operations.
- `rich` for enhanced console outputs, utilized throughout the module for logging and interactive feedback.
- `smah.settings.Settings` and `smah.runner.Runner`, which are the other core modules facilitating configuration handling and executing user queries.

Use Cases:
- Can be run with flags to execute specific instructions or queries, configure settings, and manage output verbosity.

Note:
Ensure the environment is set up with the necessary dependencies before executing this script.
"""


import os
import argparse
import textwrap
import yaml
import rich
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.console import Console
import logging
import sys

from smah.settings import Settings
from smah.runner import Runner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(created)f %(filename)s:%(lineno)d [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("smah.log"),
        logging.StreamHandler(sys.stdout)  # For console output
    ]
)

console = Console()
err_console = Console(stderr=True)

def extract_args():
    """
    Parses and extracts command-line arguments for the SMAH CLI tool.

    Returns:
        parser (ArgumentParser): The argument parser with configured options.
        args (Namespace): Parsed arguments and options.
        pipe (str or None): Content read from standard input if available.
    """
    parser = initialize_argument_parser()
    add_general_arguments(parser)
    add_ai_arguments(parser)
    add_gui_arguments(parser)
    args = parser.parse_args()
    return parser, args, get_pipe()


def initialize_argument_parser():
    """
    Initialize the argument parser with basic configurations.

    Returns:
        ArgumentParser: A configured argument parser.
    """
    return argparse.ArgumentParser(
        description="SMAH Command Line Tool",
        formatter_class=argparse.RawTextHelpFormatter
    )

def add_general_arguments(parser):
    """
    Add general command-line arguments to the parser.

    Args:
        parser (ArgumentParser): The argument parser to which general arguments are added.
    """
    parser.add_argument('-q', '--query', type=str, help='The Query to process')
    parser.add_argument('-i', '--instructions', type=str, help='The Instruction File to process')
    parser.add_argument('--profile', type=str, help='Path to alternative config file')
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Set Verbosity Level, such as -vv")

def add_ai_arguments(parser):
    """
    Add specific AI-related command-line arguments to the parser.

    Args:
        parser (ArgumentParser): The argument parser to which AI-related arguments are added.
    """
    parser.add_argument('--openai-api-tier', type=int, help='OpenAI Tier')
    parser.add_argument('--openai-api-key', type=str, help='OpenAI Api Key')
    parser.add_argument('--openai-api-org', type=str, help='OpenAI Api Org')

def add_gui_arguments(parser):
    """
    Add GUI-related command-line arguments to the parser.

    Args:
        parser (ArgumentParser): The argument parser to which GUI-related arguments are added.
    """
    parser.add_argument('--gui', action=argparse.BooleanOptionalAction, help='Run in GUI mode', default=True)

def get_pipe():
    """
    Reads data from standard input if present and available.

    Returns:
        str or None: The content available from standard input; otherwise, None if input is not a TTY.
    """
    if sys.stdin.isatty():
        return None
    else:
        return sys.stdin.read()

def log_settings(settings, format=True, print_settings=False):
    """
    Log current application settings and print them in a configured format.

    Args:
        settings (Settings): Application settings object.
    """
    try:
        settings_yaml = yaml.dump({"settings": settings.to_yaml({"stats": True})}, sort_keys=False)
        logging.info("[Settings]\n%s", settings_yaml)
        if print_settings:
            t = textwrap.dedent(
                """
                Settings
                ========
                ```yaml
                {c}
                ```
                """
            ).strip().format(c=settings_yaml)
            console.print(Markdown(t) if format else t)
    except Exception as e:
        logging.error("Exception Raised: %s", str(e))

def main():
    try:
        parser, args, pipe = extract_args()
        settings = Settings(args)

        print_settings=args.verbose > 2
        # If settings are not configured, ask user to provide necessary information
        if not settings.is_configured():
            settings.configure()
            print_settings = True
        log_settings(settings, print_settings=print_settings, format=args.gui)

        runner = Runner(args, settings)

        if args.query:
            process_query(console, runner, args.query, pipe)
        elif args.instructions:
            process_instructions(console, runner, args.instructions, pipe)
        else:
            runner.interactive(pipe=pipe)
    except Exception as e:
        logging.error("An unexpected error occurred in main: %s", str(e))
        console.print(f"An unexpected error occurred: {e}", style="bold red")


def process_query(console, runner, query, pipe):
    try:
        if pipe:
            runner.pipe(query=query, pipe=pipe)
        else:
            runner.query(query=query)
    except Exception as e:
        logging.error("Error processing query: %s", str(e))
        console.print(f"Error processing query: {e}", style="bold red")

def process_instructions(console, runner, instructions_file, pipe):
    try:
        with open(instructions_file, 'r') as file:
            instructions = file.read()
            if instructions:
                if pipe:
                    runner.pipe(query=instructions, pipe=pipe)
                else:
                    runner.query(query=instructions.query)
    except FileNotFoundError:
        logging.error("Instruction file not found: %s", instructions_file)
        console.print(f"Error: Instruction file '{instructions_file}' not found.", style="bold red")
    except IOError as e:
        logging.error("IO error reading file '%s': %s", instructions_file, str(e))
        console.print(f"Error reading file '{instructions_file}': {e}", style="bold red")