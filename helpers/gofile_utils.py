"""
This module provides utility functions for interacting with the GoFile API.
"""

import sys
from urllib.parse import urlencode

import requests

from .config import (
    GOFILE_API,
    GOFILE_API_ACCOUNTS
)

def get_content_id(url):
    """
    Extracts and returns the content ID from a GoFile URL.

    Args:
        url (str): The GoFile URL from which to extract the content ID.

    Returns:
        str or None: The content ID if the URL is valid, or None if the URL is
                     invalid or the ID cannot be found.
    """
    try:
        if url.split('/')[-2] != 'd':
            print(f"Missing ID for URL: {url}")
            return None

        return url.split('/')[-1]

    except IndexError:
        print(f"{url} is not a valid GoFile URL.")
        return None

def generate_content_url(content_id, password=None):
    """
    Builds a URL for accessing content, optionally including a password as a
    query parameter.

    Args:
        content_id (str): The unique identifier of the content to be accessed.
        password (str, optional): The password required to access the content,
                                  if any. Default is None.

    Returns:
        str: The generated URL for accessing the content, with or without the
             password query parameter.
    """
    base_url = f"{GOFILE_API}/contents/{content_id}?wt=4fd6sg89d7s6&cache=true"

    # Only add the password if it's provided
    query_params = {}
    if password:
        query_params['password'] = password

    # If there are additional query parameters, append them
    if query_params:
        return f"{base_url}&{urlencode(query_params)}"

    return base_url

def check_response_status(response, filename):
    """
    Checks if the server response is valid based on status codes.

    Args:
        response (requests.Response): The HTTP response object to be validated.
        filename (str): The name of the file being downloaded, used for
                        logging.

    Returns:
        bool: True if the response is valid, False otherwise.
    """
    is_invalid_status_code = (
        response.status_code in (403, 404, 405, 500)
        or response.status_code != 200
    )

    if is_invalid_status_code:
        print(
            f"Invalid response for {filename}. "
            f"Status code: {response.status_code}"
        )
        return False

    return True

def get_account_token():
    """
    Retrieves the access token for the created account.

    Returns:
        str: The access token of the created account.

    Raises:
        SystemExit: If the account creation fails, the function prints an error
                    message and exits the program.
    """
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }

    account_response = requests.post(
        GOFILE_API_ACCOUNTS,
        headers=headers,
        timeout=10
    ).json()

    if account_response["status"] != "ok":
        print("Account creation failed.")
        sys.exit(1)

    return account_response["data"]["token"]
