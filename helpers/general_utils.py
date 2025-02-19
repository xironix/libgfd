"""Module to handle common tasks.

This module includes functions to handle common tasks such as sending HTTP
requests, parsing HTML, creating download directories, and clearing the
terminal, making it reusable across projects.
"""

import os
from pathlib import Path


def create_download_directory(directory_name: str) -> None:
    """Create a directory for saving files if it does not already exist."""
    filepath = Path.cwd() / Path(directory_name)
    filepath.mkdir(parents=True, exist_ok=True)


def clear_terminal() -> None:
    """Clear the terminal screen based on the operating system."""
    commands = {
        "nt": "cls",       # Windows
        "posix": "clear",  # macOS and Linux
    }

    command = commands.get(os.name)
    if command:
        os.system(command)  # noqa: S605
