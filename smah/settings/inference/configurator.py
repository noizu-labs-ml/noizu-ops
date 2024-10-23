from typing import Optional
import platform
import rich.box
import logging
import os
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from .inference import Inference
from smah.console import std_console, err_console, prompt_choice, prompt_string

def inference_terminal_configurator(subject: Inference):
    std_console.print(Markdown("## Configure Inference Settings"))
    return subject