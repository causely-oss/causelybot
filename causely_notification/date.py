from __future__ import annotations

from datetime import datetime


def parse_iso_date(iso_date_str):
    """
    Parse an ISO 8601 date string and return a human-readable format.

    Args:
        iso_date_str (str): The ISO 8601 date string.

    Returns:
        str: A human-readable date string.
    """
    try:
        # Parse the ISO 8601 date string
        parsed_date = datetime.strptime(iso_date_str[:19], "%Y-%m-%dT%H:%M:%S")
        # Convert to human-readable format
        readable_date = parsed_date.strftime("%B %d, %Y at %I:%M:%S %p")
        return readable_date
    except ValueError:
        return iso_date_str
