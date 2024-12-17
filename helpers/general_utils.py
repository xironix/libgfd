"""
This module includes functions to handle common tasks such as sending HTTP
requests, parsing HTML, creating download directories, and clearing the
terminal, making it reusable across projects.
"""

import os

def create_download_directory(directory_name):
    """
    Creates a directory for saving files if it does not already exist, and
    changes the current working directory to the newly created directory.

    Args:
        directory_name (str): The name of the directory to create.
    """
    filepath = os.path.join(os.getcwd(), directory_name)
    os.makedirs(filepath, exist_ok=True)

def clear_terminal():
    """
    Clears the terminal screen based on the operating system.
    """
    commands = {
        'nt': 'cls',      # Windows
        'posix': 'clear'  # macOS and Linux
    }

    command = commands.get(os.name)
    if command:
        os.system(command)
