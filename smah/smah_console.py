

from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich import box
from readchar import readkey, key

def select_prompt(console, prompt, choices, title = "Select"):
    selected_index = 0
    console.print(prompt)

    def choice_box():
        entries = []
        for index, option in enumerate(choices):
            prefix = "* " if index == selected_index else "  "
            choice_text = Text(f"{prefix}{option}")
            if index == selected_index:
                choice_text.stylize("bold green")
            entries.append(choice_text)
        return Panel(
            "\n".join([str(text) for text in entries]),
            title=title,
            expand=False,
            border_style="white",
            box=box.ROUNDED)

    with Live(choice_box(), refresh_per_second=10) as live:
        while True:
            k = readkey()

            if k == key.UP:
                selected_index -= 1
            elif k == key.DOWN:
                selected_index += 1
            elif k == key.ENTER:
                return choices[selected_index]

            if selected_index < 0:
                selected_index = len(choices) - 1
            elif selected_index >= len(choices):
                selected_index = 0

            live.update(choice_box())