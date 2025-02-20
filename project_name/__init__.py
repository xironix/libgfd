# This file marks the directory as a Python package and exposes key parts of your library.

__version__ = "0.1.0"

# Import functionality from the core module
from .core import hello_world

from .module1 import some_function

__all__ = ['some_function']  # Explicitly declare public API 