"""
This module provides functionality for reading URLs from a file, processing
them to download anime content, and clearing the file after the process is
complete.

Usage:
    Ensure that a file named 'URLs.txt' is present in the same directory as
    this script. The file should contain a list of URLs, one per line. When
    executed, the script will:
        1. Read the URLs from 'URLs.txt'.
        2. Process each URL for downloading anime content.
        3. Clear the contents of 'URLs.txt' after all URLs have been processed.
"""

import os
import sys

from helpers.general_utils import clear_terminal
from helpers.file_utils import (
    read_file,
    write_file
)

from downloader import (
    handle_download_process,
    initialize_managers
)

FILE = os.path.join(os.getcwd(), "URLs.txt")

def process_urls(urls):
    """
    Validates and downloads items for a list of URLs.

    Args:
        urls (list): A list of URLs to process.
    """
    live_manager = initialize_managers()

    try:
        with live_manager.live:
            for url in urls:
                handle_download_process(url, live_manager)
            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)

def main():
    """
    Main function to execute the script.

    Reads URLs from a file, processes the downloads for each URL, and clears
    the file after the processing is complete.
    """
    clear_terminal()
    urls = read_file(FILE)
    process_urls(urls)
    write_file(FILE)

if __name__ == '__main__':
    main()
