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
from smah.settings.settings import Settings
from smah.runner import Runner
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
        settings = Settings(args)

        # If settings are not configured, ask user to provide necessary information
        show = args.verbose > 2
        if not settings.is_configured():
            settings.configure()
            show = True

        settings.log(print=show, format=args.gui)
        runner = Runner(args, settings)

        if args.query:
            __process_query(runner, args.query, pipe)
        elif args.instructions:
            __process_instructions(runner, args.instructions, pipe)
        else:
            runner.interactive(pipe=pipe)
    except Exception as e:
        logging.error("An unexpected error occurred in main: %s", str(e), exc_info=True)

def __process_query(runner: Runner, query: str, pipe: str) -> None:
    """
    Process a query using the provided runner.

    Args:
        runner (Runner): The runner instance to execute the query.
        query (str): The query string to be processed.
        pipe (str or None): Optional content read from standard input.

    Raises:
        Exception: If an error occurs during query processing.
    """
    try:
        if pipe:
            runner.pipe(query=query, pipe=pipe)
        else:
            runner.query(query=query)
    except Exception as e:
        logging.error("Error processing query: %s", str(e))

def __process_instructions(runner: Runner, instructions_file: str, pipe: str) -> None:
    """
    Process instructions from a file using the provided runner.

    Args:
        runner (Runner): The runner instance to execute the instructions.
        instructions_file (str): The path to the instructions file.
        pipe (str or None): Optional content read from standard input.

    Raises:
        FileNotFoundError: If the instructions file is not found.
        IOError: If an I/O error occurs while reading the file.
    """
    try:
        with open(instructions_file, 'r') as file:
            instructions = file.read()
            if instructions:
                if pipe:
                    runner.pipe(query=instructions, pipe=pipe)
                else:
                    runner.query(query=instructions)
    except FileNotFoundError:
        logging.error("Instruction file not found: %s", instructions_file)
    except IOError as e:
        logging.error("IO error reading file '%s': %s", instructions_file, str(e))

if __name__ == "__main__":
    main()