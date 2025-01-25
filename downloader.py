"""
This script is a downloader utility for downloading files from GoFile.io, 
with support for multithreading and handling password-protected albums.

Example usage:
    python3 gofile_downloader.py <album_url>
    python3 gofile_downloader.py <album_url> <password>
"""

import os
import sys
import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor

import requests

from helpers.managers.live_manager import LiveManager
from helpers.managers.log_manager import LoggerTable
from helpers.managers.progress_manager import ProgressManager

from helpers.download_utils import save_file_with_progress
from helpers.general_utils import (
    create_download_directory,
    clear_terminal
)
from helpers.gofile_utils import (
    get_content_id,
    get_account_token,
    generate_content_url,
    check_response_status
)

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "Downloads")

SCRIPT_NAME = os.path.basename(__file__)
DEFAULT_USAGE = f"python3 {SCRIPT_NAME} <album_url>"
PASSWORD_USAGE = f"python3 {SCRIPT_NAME} <album_url> <password>"

class Downloader:
    """
    The Downloader class handles downloading files from a specified URL in
    parallel. It manages the download process, including handling
    authentication, partial downloads, and error checking. This class supports
    resuming interrupted downloads, verifying file integrity, and organizing
    downloads into appropriate directories.

    Attributes:
        url (str): The URL to download content from.
        live_manager (LiveManager): An instance of the LiveManager class for
                                    managing download status and progress.
        password (str, optional): The password required for content access,
                                  if any.
        max_workers (int): The maximum number of concurrent download tasks.
        token (str): The account token used for authentication.
    """
    def __init__(self, url, live_manager, password=None, max_workers=3):
        self.url = url
        self.live_manager = live_manager
        self.password = password
        self.max_workers = max_workers
        self.token = get_account_token()

        os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
        os.chdir(DOWNLOAD_FOLDER)

    def download_item(self, current_task, file_info):
        """Downloads a single file."""
        filename = file_info["filename"]
        final_path = os.path.join(file_info["download_path"], filename)
        download_link = file_info["download_link"]

        # Skip file if it already exists and is not empty
        if os.path.exists(final_path):
            self.live_manager.update_log(
                "Skipped download",
                f"{filename} has already been downloaded."
            )
            return

        headers = self._prepare_headers(url=download_link)

        # Perform the download and handle possible errors
        with requests.get(
            download_link, headers=headers, stream=True, timeout=(10, 30)
        ) as response:
            if not check_response_status(response, filename):
                return

            task_id = self.live_manager.add_task(current_task=current_task)
            save_file_with_progress(
                response, final_path, task_id, self.live_manager
            )

    def run_in_parallel(self, content_directory, files_info):
        """Executes the file downloads in parallel."""
        os.chdir(content_directory)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for current_task, item_info in enumerate(files_info):
                executor.submit(self.download_item, current_task, item_info)

        os.chdir(DOWNLOAD_FOLDER)

    def _prepare_headers(self, url=None, include_auth=False):
        """
        Prepares the HTTP headers for the request.
        """
        # Base headers common for all requests
        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
        }

        # If include_auth is True, add the Authorization header
        if include_auth:
            headers["Authorization"] = f"Bearer {self.token}"
        else:
            # Add Referer and Origin headers if URL is provided
            if url:
                adjusted_url = url + ('/' if not url.endswith('/') else '')
                headers["Referer"] = adjusted_url
                headers["Origin"] = url

            # Include the Cookie header for authentication when URL is not
            # needed
            headers["Cookie"] = f"accountToken={self.token}"

        return headers

    def parse_links(self, identifier, files_info, password=None):
        """
        Parses the content URL for file links and populates a list with file
        information.
        """
        def append_file_info(files_info, data):
            files_info.append({
                "download_path": os.getcwd(),
                "filename": data["name"],
                "download_link": data["link"]
            })

        def check_password(data):
            return (
                "password" in data
                and data.get("passwordStatus") != "passwordOk"
            )

        content_url = generate_content_url(identifier, password=password)

        headers = self._prepare_headers(include_auth=True)
        response = requests.get(
            content_url, headers=headers, timeout=10
        ).json()

        if response["status"] != "ok":
            self.live_manager.update_log(
                "Failed request",
                f"Failed to get a link as response from the {content_url}."
            )
            return

        data = response["data"]

        if check_password(data):
            self.live_manager.update_log(
                "Missing password",
                "Provide the password for the URL."
            )
            return

        # Handle folder
        if data["type"] == "folder":
            create_download_directory(data["name"])
            os.chdir(data["name"])

            for child_id in data["children"]:
                child = data["children"][child_id]

                if child["type"] == "folder":
                    self.parse_links(child["id"], files_info, password)
                else:
                    append_file_info(files_info, child)

            os.chdir(os.path.pardir)

        # Handle file
        else:
            append_file_info(files_info, data)

    def initialize_download(self):
        """
        Initiates the download process by requesting the content and starting
        the download.
        """
        content_id = get_content_id(self.url)
        content_directory = os.path.join(DOWNLOAD_FOLDER, content_id)
        create_download_directory(content_directory)

        files_info = []
        hashed_password = (
            hashlib.sha256(self.password.encode()).hexdigest() if self.password
            else self.password
        )
        self.parse_links(content_id, files_info, hashed_password)

        # Removes the root content directory if there's no file or
        # subdirectory.
        if not os.listdir(content_directory) and not files_info:
            os.rmdir(content_directory)
            return

        self.live_manager.add_overall_task(
            description=content_id, num_tasks=len(files_info)
        )
        self.run_in_parallel(content_directory, files_info)

def handle_download_process(url, live_manager, password=None):
    """
    Handles the process of downloading content from a specified URL.

    Args:
        url (str): The URL from which to download content. This is a required
                   parameter.
        password (str, optional): An optional password for the download.
                                  Default is `None`.

    
    Raises:
        SystemExit: If the URL is `None`, the function terminate the program,
                    showing usage.
    """
    if url is None:
        print(
            f"Default usage: {DEFAULT_USAGE}\n"
            f"Password usage: {PASSWORD_USAGE}\n"
        )
        sys.exit(1)

    downloader = Downloader(
        url=url,
        live_manager=live_manager,
        password=password
    )
    downloader.initialize_download()

def initialize_managers():
    """
    Initializes and returns the managers for progress tracking and logging.

    Returns:
        LiveManager: Handles the live display of progress and logs.
    """
    progress_manager = ProgressManager(
        task_name="Album",
        item_description="File"
    )
    logger_table = LoggerTable()
    return LiveManager(progress_manager, logger_table)

def setup_parser():
    """
    Sets up and returns an argument parser for downloading content from a
    specified URL.

    Returns:
        argparse.ArgumentParser: The configured argument parser with the
                                 defined arguments.
    """
    parser = argparse.ArgumentParser(
        description="Download content from a specified URL."
    )
    parser.add_argument(
        "url", nargs="?", type=str, help="The URL to download from."
    )
    parser.add_argument(
        "password", nargs="?", type=str, help="The password for the download."
    )
    return parser

def main():
    """
    This function processes command-line arguments to download an album from a
    specified URL. It expects at least one argument (the URL) and optionally a
    second argument (a password).

    Raises:
        SystemExit: Exits the program if not enough arguments are provided or
                    if interrupted by the user.
    """
    clear_terminal()
    parser = setup_parser()
    args = parser.parse_args()
    live_manager = initialize_managers()

    try:
        with live_manager.live:
            handle_download_process(
                args.url,
                live_manager,
                password=args.password
            )
            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == '__main__':
    main()
