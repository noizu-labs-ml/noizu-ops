from rich.console import Console

# Initialize standard console for general output
std_console: Console = Console()

# Initialize error console for error output
err_console: Console = Console(stderr=True)
