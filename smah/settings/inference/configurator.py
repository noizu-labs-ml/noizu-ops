import textwrap
from typing import Optional
import platform
import rich.box
import logging
import os

import yaml
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from .inference import Inference
from smah.console import std_console, err_console, prompt_choice, prompt_string

def inference_terminal_configurator(subject: Optional[Inference]):
    std_console.print(Markdown("## Configure Inference Settings"))
    subject = subject or Inference()
    if not subject.providers:
        subject = load_defaults()

    if subject.is_configured():
        show(subject)
        if not Confirm.ask("edit?", default=False):
            return subject

    while True:
        subject = prompt(subject)
        std_console.print("\n")
        show(subject, label = "Confirm Inference Settings", border_style="green bold")
        if Confirm.ask("confirm?", default=True):
            return subject

def prompt(subject: Inference) -> Inference:
    subject.instructions = prompt_string("Instructions", subject.instructions, required=False)
    if subject.providers:
        for k,p in subject.providers.items():
            api_key = p.settings.get("api_key", None) if p.settings else None
            api_key = prompt_string(f"{k}.api_key", api_key, required=False, label="API Key: [white]Leave blank to use environment variable[/white]")
            enable = Confirm.ask(f"{k}.enable", default=p.enabled)
            subject.providers[k].settings = subject.providers[k].settings or {}
            subject.providers[k].settings["api_key"] = api_key
            subject.providers[k].enabled = enable
    return subject

def show(subject: Inference, label = "Inference Settings", border_style="white bold"):
    body = subject.show({"save": True})
    template = textwrap.dedent(
        """
        **Inference:**
        ```yaml
        {body}
        ```
        """).strip().format(body=body)
    template = Markdown(template)
    template = Panel(template, title=label, border_style=border_style, box=rich.box.ROUNDED)
    std_console.print(template)

def load_defaults() -> Inference:
    try:
        with open(os.path.join(os.path.dirname(__file__), "inference_defaults.yaml"), 'r') as file:
            config_data = yaml.safe_load(file)
            return Inference(config_data)
    except Exception as e:
        logging.error(f"Failed to load config: {str(e)}")
        raise e