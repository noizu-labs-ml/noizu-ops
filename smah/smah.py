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
import textwrap
from typing import Optional

import lxml.etree
from rich.prompt import Prompt

import smah.console
from smah.database import Database
from smah.runner import Runner
from smah.settings import Settings, configurator
import smah.logs
import smah.args
from lxml import etree

def pick_session(args) -> int:
    """
    Picks a recent session from the database.
    """
    db = Database(args)
    sessions = db.history()
    choices = [""]
    choice_lookup = {}
    count = 0
    prompt = ""
    for session in sessions:
        count += 1
        choices.append(f"{count}")
        choice_lookup[str(count)] = session['id']
        prompt += f"[bold green]{count}[/bold green] - (#{session['id']}) {session['title']}\n"
    prompt += "[bold green]Select a session number to resume:[/bold green] (enter to cancel)"

    choice = Prompt.ask(prompt)
    if not choice:
        exit(0)
    while choice not in choices:
        choice = Prompt.ask("[bold red]Pick Valid Session[/bold red]")
        if not choice:
            exit(0)
    return choice_lookup[str(choice)]

def resume_session(args, session: Optional[int] = None):
    """
    Resumes the last conversation from the database.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
    """
    db = Database(args)
    if session:
        session = db.session(session)
    else:
        session = db.last_session()

    if session:
        args = smah.args.merge_args(args, session['args'])
        settings = Settings(config=args.config)

        # If settings are not configured, ask user to provide necessary information
        if not settings.is_configured() or args.configure:
            settings = configurator(settings, gui=args.gui)
            settings.log(print=True, format=True)
        else:
            settings.log(print=(args.verbose >= 3), format=True)
        runner = Runner(args, settings)
        runner.resume(id=session['id'], title=session['title'], plan=session['plan'], pipe=session['pipe'], messages=session['messages'])
    else:
        print("No previous session found.")
        exit(1)


class ExecTag(etree.ElementBase):
    def _init(self):
        self.tag = "exec"
        # shell = f"{self.shell}"
        # title = self.cssselect("title")
        # if len(title) > 0:
        #     title = title[0]
        #     title.text = textwrap.dedent(title.text.strip())
        #     title.tail = "\n"
        # else:
        #     title = None
        #
        # purpose = self.cssselect("purpose")
        # if len(purpose) > 0:
        #     purpose = purpose[0]
        #     purpose.text = textwrap.dedent(purpose.text.strip())
        #     purpose.tail = "\n"
        # else:
        #     purpose = None
        #
        # command = self.cssselect("command")
        # if len(command) > 0:
        #     command = command[0]
        #     command.tail = "\n"
        # else:
        #     command = None
        #
        # self.clear()
        # self.set("shell", shell)
        # self.text = "\n"
        # self.tail = "\n\n"
        # self.append(title) if title is not None else None
        # self.append(purpose) if purpose is not None else None
        # self.append(command) if command is not None else None

    @property
    def shell(self):
        return self.get("shell")


class SmahLookup(etree.CustomElementClassLookup):
    def lookup(self, node_type, document, namespace, name):
        if node_type == "element":
            if name == "exec":
                return ExecTag
        return None



def main2():
    parser = etree.XMLPullParser(events={'end'})
    parser.set_element_class_lookup(SmahLookup())
    raw = textwrap.dedent(
        """
        To use `ufw`, the command would be:
        <p>Para</p>
        <exec shell="bash" h="hey">        
        <title>Lock Port 5312 using UFW</title>
        <purpose>Prevent all traffic on port 5312 using UFW</purpose>
        <command>
        sudo ufw deny 5312
        sudo ufw deny 5313
        </command>
        </exec>
        
        <exec shell="bash" h="hey">        
        <title>Lock Port 5312 using UFW</title>
        <purpose>Prevent all traffic on port 5312 using UFW</purpose>
        <command>
        sudo ufw status
        </command>
        </exec>
        
        <cot type="inner-critic">I provided commands using both `iptables` and `ufw`, which covers different user
        preferences. I should also remind the user to verify their current firewall settings to ensure they do not
        unintentionally disrupt other services.</cot>
        
        If you would like to check your current `iptables` rules after executing these commands, you can run:         
        """
    )
    events = parser.read_events()
    parser.feed("<m>" + raw + "</m>")

    for action, elem in events:
        if action == "end":
            if elem.tag == 'exec':
                ps = elem.getprevious()
                p = elem.getparent()
                t = elem.cssselect("command")[0].text
                if ps is not None:
                    ps.tail += f"\nEXEC - {t} \n"
                elif p is not None:
                    p.text += f"\nEXEC - {t} \n"

                if p is not None:
                    p.remove(elem)






    root = parser.close()

    print("root", etree.tostring(root, pretty_print=True).decode())





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

        if args.resume:
            resume_session(args)
        elif args.session:
            resume_session(args, session=args.session)
        elif args.history:
            session = pick_session(args)
            resume_session(args, session=session)
        else:
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