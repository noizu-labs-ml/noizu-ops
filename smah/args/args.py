import argparse
import sys
import logging

def merge_args(args: argparse.Namespace, config: dict) -> argparse.Namespace:
    """
    Merges parsed command-line arguments with configuration settings.

    Args:
        args (Namespace): Parsed command-line arguments.
        config (dict): Configuration settings.

    Returns:
        Namespace: Merged arguments and settings.
    """
    for key, value in config.items():
        if key in args and getattr(args, key) is None:
            setattr(args, key, value)
    return args

def extract_args() -> tuple[argparse.Namespace, str | None]:
    """
    Parses and extracts command-line arguments for the SMAH CLI tool.

    Returns:
        parser (ArgumentParser): The argument parser with configured options.
        args (Namespace): Parsed arguments and options.
        pipe (str or None): Content read from standard input if available.
    """
    parser = __initialize_argument_parser()
    __add_general_arguments(parser)
    __add_ai_arguments(parser)
    __add_gui_arguments(parser)
    a = parser.parse_args()
    return a, __get_pipe()

def __initialize_argument_parser():
    """
    Initialize the argument parser with basic configurations.

    Returns:
        ArgumentParser: A configured argument parser.
    """
    return argparse.ArgumentParser(
        description="SMAH Command Line Tool",
        formatter_class=argparse.RawTextHelpFormatter
    )


def __add_general_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add general command-line arguments to the parser.

    Args:
        parser (ArgumentParser): The argument parser to which general arguments are added.
    """
    parser.add_argument('-q', '--query', type=str, help='The Query to process')
    parser.add_argument('-i', '--instructions', type=str, help='The Instruction File to process')
    parser.add_argument('--interactive', action=argparse.BooleanOptionalAction, help='Run in interactive mode', default=False)
    parser.add_argument('-c', '--config', type=str, help='Path to alternative config file')
    parser.add_argument('--database', type=str, help='Path to sqlite smah database')
    parser.add_argument('--configure', action=argparse.BooleanOptionalAction, help='Enter Config Setup', default=False)
    parser.add_argument('--continue', dest="resume", action=argparse.BooleanOptionalAction, help='Continue Last Conversation', default=False)
    parser.add_argument('--session', type=int, help='Resume Session')
    parser.add_argument('--history', action=argparse.BooleanOptionalAction, help='Resume Recent Session', default=False)
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Set Verbosity Level, such as -vv")

def __add_ai_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add specific AI-related command-line arguments to the parser.

    Args:
        parser (ArgumentParser): The argument parser to which AI-related arguments are added.
    """
    parser.add_argument('--model', type=str, help='Default Model')
    parser.add_argument('--model-picker', type=str, help='Picker Model')
    parser.add_argument('--model-query', type=str, help='Query Model')
    parser.add_argument('--model-pipe', type=str, help='Pipe Processing Model')
    parser.add_argument('--model-interactive', type=str, help='Interactive Processing Model')
    parser.add_argument('--model-review', type=str, help='Output Reviewer Model')
    parser.add_argument('--model-edit', type=str, help='Output Editor Model')

    parser.add_argument('--openai-api-tier', type=int, help='OpenAI Tier')
    parser.add_argument('--openai-api-key', type=str, help='OpenAI Api Key')
    parser.add_argument('--openai-api-org', type=str, help='OpenAI Api Org')

def __add_gui_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add GUI-related command-line arguments to the parser.

    Args:
        parser (ArgumentParser): The argument parser to which GUI-related arguments are added.
    """
    parser.add_argument('--gui', action=argparse.BooleanOptionalAction, help='Run in GUI mode', default=False)
    parser.add_argument('--rich', action=argparse.BooleanOptionalAction, help='Rich Format Output', default=True)

def __get_pipe():
    """
    Reads data from standard input if present and available.

    Returns:
        str or None: The content available from standard input; otherwise, None if input is not a TTY.
    """
    if sys.stdin.isatty():
        return None
    else:
        return sys.stdin.read()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    args, pipe = extract_args()
    logging.debug("Parsed arguments: %s", args)
    logging.debug("Pipe content: %s", pipe)