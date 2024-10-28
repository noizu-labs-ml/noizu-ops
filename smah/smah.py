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

import logging
from typing import Optional

import smah.console
from smah.runner import Runner
from smah.settings import Settings, configurator
# from smah.runner import Runner
import smah.logs
import smah.args

def main():
    """
    The primary function that sets up application configuration and executes user-specified queries.

    This function configures logging, parses command-line arguments, initializes settings, and
    coordinates the execution based on user inputs. It handles different modes of operation such as
    processing queries, processing instructions from a file, or running in interactive mode.

    Raises:
        Exception: If an unexpected error occurs during execution.
    """
    # Configure logging
    smah.logs.configure()

    try:
        args, pipe = smah.args.extract_args()
        settings = Settings(config=args.config)

        # If settings are not configured, ask user to provide necessary information
        if not settings.is_configured() or args.configure:
            settings = configurator(settings, gui=args.gui)
            settings.log(print=True, format=True)
        else:
            settings.log(print=(args.verbose >= 3), format=True)
        runner = Runner(args, settings)

        query = __with_query(args)

        if args.interactive or not query:
            runner.interactive(query=query, pipe=pipe)
        else:
            if pipe:
                runner.pipe(query=query, pipe=pipe)
            else:
                runner.query(query=query)
    except Exception as e:
        logging.error("An unexpected error occurred in main: %s", str(e), exc_info=True)


def __with_query(args) -> Optional[str]:
    """
    Extracts the query from the command-line arguments.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.

    Returns:
        Optional[str]: The query string if provided, None otherwise.
    """
    if args.query:
        return args.query

    if args.instructions:
        try:
            with open(args.instructions, 'r') as file:
                return file.read()
        except FileNotFoundError as e:
            logging.error("Instruction file not found: %s", args.instructions)
            raise e
        except IOError as e:
            logging.error("IO error reading file '%s': %s", args.instructions, str(e))
            raise e

    return None

if __name__ == "__main__":
    main()