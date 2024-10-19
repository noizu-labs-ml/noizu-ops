import os
import argparse
from smah.config import config
from rich.console import Console
import textwrap
from openai import OpenAI

console = Console()

def extract_args():
    parser = argparse.ArgumentParser(description="SMAH - Smart as Hell CLI Tool")

    parser.add_argument('-c', '--command', type=str, help='Execute a single command')
    parser.add_argument('-i', '--interactive', action='store_true', help='Start interactive mode')
    # parser.add_argument('-v', '--version', action='version', version='SMAH 1.0', help='Display the version of the tool')
    # parser.add_argument('-l', '--log', type=str, help='Specify a log file to write logs')
    # parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode for more verbose output')

    args = parser.parse_args()
    return (parser, args)


def get_client(args, smahConfig: config.Config):
    client = OpenAI(api_key=smahConfig.openai_api_key)
    return client

def run_command(args, smahConfig: config.Config):
    print(f"Info:\n", smahConfig.config_info())
    print(f"Executing command: {args.command}")
    client = get_client(args, smahConfig)
    system_prompt = textwrap.dedent(f"""
    You are a command line helper tool called SMAH (System Management and Automation Helper) aka (SMart As Hell).
    Your user and their current system configuration is as follows:
    [config]
    {smahConfig.config_info()}
    [/config]
    """)

    request_message = textwrap.dedent(f"""
    Please Help I Want To: 
    {args.command}
    """)

    thread = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": request_message
        }

    ]
    chat_completion = client.chat.completions.create(messages = thread, model="gpt-4o")
    print(chat_completion.choices[0].message.content)




def main():
    # Load Args
    parser, args = extract_args()

    # Load Config
    smahConfig = config.Config()

    if args.command:
        run_command(args, smahConfig)

    elif args.interactive:
        print("Starting interactive mode...")
    else:
        parser.print_help()

    # if not config.is_configured():
    #     config.config_missing(console = console)
    # else:
    #     smahConfig = config.Config()
    #     print("smah user = ", smahConfig.user)