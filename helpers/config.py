"""Centralized configuration module for managing constants used across the project.

These configurations aim to improve modularity and readability by consolidating settings
into a single location.
"""

GOFILE_API = "https://api.gofile.io"            # The base URL for the GoFile API.
GOFILE_API_ACCOUNTS = f"{GOFILE_API}/accounts"  # The endpoint for GoFile account
                                                # related operations.
DOWNLOAD_FOLDER = "Downloads"                   # The folder where downloaded files
                                                # will be stored.
URLS_FILE = "URLs.txt"                          # The name of the file containing the
                                                # list of URLs to process.
SESSION_LOG = "session_log.txt"                 # The file used to log session errors.

# Constants for file sizes, expressed in bytes.
KB = 1024
MB = 1024 * KB

# HTTP status codes.
HTTP_STATUS_OK = 200
