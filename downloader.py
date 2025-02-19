"""Downloader module for downloading files from GoFile.

Example usage:
    python3 gofile_downloader.py <album_url>
    python3 gofile_downloader.py <album_url> <password>
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from helpers.config import DOWNLOAD_FOLDER
from helpers.download_utils import save_file_with_progress
from helpers.general_utils import clear_terminal, create_download_directory
from helpers.gofile_utils import (
    check_response_status,
    generate_content_url,
    get_account_token,
    get_content_id,
)
from helpers.managers.live_manager import LiveManager
from helpers.managers.log_manager import LoggerTable
from helpers.managers.progress_manager import ProgressManager

CURRENT_DOWNLOAD_FOLDER = Path.cwd() / DOWNLOAD_FOLDER

SCRIPT_NAME = Path(__file__).name
DEFAULT_USAGE = f"python3 {SCRIPT_NAME} <album_url>"
PASSWORD_USAGE = f"python3 {SCRIPT_NAME} <album_url> <password>"


class Downloader:
    """Class to handle downloading files from a specified URL in parallel.

    It manages the download process, including handling authentication, partial
    downloads, and error checking. This class supports resuming interrupted downloads,
    verifying file integrity, and organizing downloads into appropriate directories.
    """

    def __init__(
        self,
        url: str,
        live_manager: LiveManager,
        password: str | None = None,
        max_workers: int = 3,
    ) -> None:
        """Initialize the downloader with the given parameters."""
        self.url = url
        self.live_manager = live_manager
        self.password = password
        self.max_workers = max_workers
        self.token = get_account_token()

        CURRENT_DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        os.chdir(CURRENT_DOWNLOAD_FOLDER)

    def download_item(self, current_task: int, file_info: tuple) -> None:
        """Download a single file."""
        filename = file_info["filename"]
        final_path = Path(file_info["download_path"]) / filename
        download_link = file_info["download_link"]

        # Skip file if it already exists and is not empty
        if Path(final_path).exists():
            self.live_manager.update_log(
                "Skipped download",
                f"{filename} has already been downloaded.",
            )
            return

        headers = self._prepare_headers(url=download_link)

        # Perform the download and handle possible errors
        with requests.get(
            download_link,
            headers=headers,
            stream=True,
            timeout=(10, 30),
        ) as response:
            if not check_response_status(response, filename):
                return

            task_id = self.live_manager.add_task(current_task=current_task)
            save_file_with_progress(response, final_path, task_id, self.live_manager)

    def run_in_parallel(self, content_directory: str, files_info: tuple) -> None:
        """Execute the file downloads in parallel."""
        os.chdir(content_directory)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for current_task, item_info in enumerate(files_info):
                executor.submit(self.download_item, current_task, item_info)

        os.chdir(CURRENT_DOWNLOAD_FOLDER)

    def _prepare_headers(
        self,
        url: str | None = None,
        *,
        include_auth: bool = False,
    ) -> dict:
        """Prepare the HTTP headers for the request."""
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
            "Cache-Control": "no-cache",
        }

        # If include_auth is True, add the Authorization header
        if include_auth:
            headers["Authorization"] = f"Bearer {self.token}"
        else:
            # Add Referer and Origin headers if URL is provided
            if url:
                adjusted_url = url + ("/" if not url.endswith("/") else "")
                headers["Referer"] = adjusted_url
                headers["Origin"] = url

            # Include the Cookie header for authentication when URL is not
            # needed
            headers["Cookie"] = f"accountToken={self.token}"

        return headers

    def parse_links(
        self,
        identifier: str,
        files_info: tuple,
        password: str | None = None,
    ) -> None:
        """Parse the URL for file links and populates a list with file information."""

        def append_file_info(files_info: tuple, data: dict) -> None:
            files_info.append(
                {
                    "download_path": str(Path.cwd()),
                    "filename": data["name"],
                    "download_link": data["link"],
                },
            )

        def check_password(data: dict) -> bool:
            return "password" in data and data.get("passwordStatus") != "passwordOk"

        content_url = generate_content_url(identifier, password=password)

        headers = self._prepare_headers(include_auth=True)
        response = requests.get(content_url, headers=headers, timeout=10).json()

        if response["status"] != "ok":
            self.live_manager.update_log(
                "Failed request",
                f"Failed to get a link as response from the {content_url}.",
            )
            return

        data = response["data"]

        if check_password(data):
            self.live_manager.update_log(
                "Missing password",
                "Provide the password for the URL.",
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

    def initialize_download(self) -> None:
        """Initialize the download process."""
        content_id = get_content_id(self.url)
        content_directory = CURRENT_DOWNLOAD_FOLDER / content_id
        create_download_directory(content_directory)

        files_info = []
        hashed_password = (
            hashlib.sha256(self.password.encode()).hexdigest()
            if self.password
            else self.password
        )
        self.parse_links(content_id, files_info, hashed_password)

        # Removes the root content directory if there's no file or
        # subdirectory.
        if not os.listdir(content_directory) and not files_info:
            Path(content_directory).rmdir()
            return

        self.live_manager.add_overall_task(
            description=content_id,
            num_tasks=len(files_info),
        )
        self.run_in_parallel(content_directory, files_info)


def handle_download_process(
    url: str,
    live_manager: LiveManager,
    password: str | None = None,
) -> None:
    """Handle the process of downloading content from a specified URL."""
    if url is None:
        usage = f"Default usage: {DEFAULT_USAGE}\nPassword usage: {PASSWORD_USAGE}\n"
        logging.error(usage)
        sys.exit(1)

    downloader = Downloader(url=url, live_manager=live_manager, password=password)
    downloader.initialize_download()


def initialize_managers() -> LiveManager:
    """Initialize and returns the managers for progress tracking and logging."""
    progress_manager = ProgressManager(task_name="Album", item_description="File")
    logger_table = LoggerTable()
    return LiveManager(progress_manager, logger_table)


def setup_parser() -> ArgumentParser:
    """Set up and returns an argument parser."""
    parser = argparse.ArgumentParser(
        description="Download content from a specified URL.",
    )
    parser.add_argument("url", nargs="?", type=str, help="The URL to download from.")
    parser.add_argument(
        "password",
        nargs="?",
        type=str,
        help="The password for the download.",
    )
    return parser


def main() -> None:
    """Process command-line arguments to download an album from a specified URL.

    It expects at least one argument (the URL) and optionally a second argument
    (a password).
    """
    clear_terminal()
    parser = setup_parser()
    args = parser.parse_args()
    live_manager = initialize_managers()

    try:
        with live_manager.live:
            handle_download_process(args.url, live_manager, password=args.password)
            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
