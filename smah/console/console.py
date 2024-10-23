from rich.console import Console
import textwrap
from rich.prompt import Prompt, Confirm
from typing import Optional
# Initialize standard console for general output
std_console: Console = Console()

# Initialize error console for error output
err_console: Console = Console(stderr=True)


def prompt_string(
        field: str,
        value: Optional[str],
        required: bool = True,
        label: Optional[str] = None,
        style: Optional[str] = "green bold"
        ) -> str:
    if value:
        std_console.print(f"{field.capitalize()}: {value}")
        if not Confirm.ask("edit?", default=False):
            return value
    msg = f"[{style}]{label or field.capitalize()}[/{style}]"

    v = Prompt.ask(msg, default=value)
    while required and not v:
        v = Prompt.ask(msg, default=value)
    return v

def prompt_choice(
    field: str,
    value: Optional[str],
    options: list[str] | list[tuple[str, str]],
    required: bool = True,
    other: bool = False,
    label: Optional[str] = None,
    style: Optional[str] = "green bold") -> str:
    if value:
        std_console.print(f"{field.capitalize()}: {value}")
        if not Confirm.ask("edit?", default=False):
            return value

    lookup = {}
    reverse_lookup = {}
    i = 0
    for option in options:
        if isinstance(option, tuple):
            k, v = option
        else:
            i += 1
            k = str(i)
            v = option
        lookup[k] = v
        reverse_lookup[v] = k
    if other:
        lookup["o"] = "Other"

    o = "\n".join([f"{k} - {v}" for k, v in lookup.items()])
    o = textwrap.indent(o, " ")
    msg = f"[{style}]{label or field.capitalize()}[/{style}]\n{o}\n"

    d = reverse_lookup.get(value)
    d  = d or "o" if other and value else None

    choice = Prompt.ask(msg, choices=list(lookup.keys()), default=d)
    if other and choice == "o":
        v = Prompt.ask(f"[{style}]Other[/{style}]", default=value)
        while required and not v:
            v = Prompt.ask(f"[{style}]Other[/{style}]", default=value)
        return v

    return lookup[choice]
