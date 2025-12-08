""" Utility module for tap-formkeep."""

import re
from typing import Any


def sanitize_field_name(field_name: str) -> str:
    """
    Sanitize field names to be compatible with DB columns and JSON schema.
    Replaces spaces and special characters with underscores.
    """
    # Replace spaces and special characters with underscores
    new_key = re.sub(r'[^A-Za-z0-9_]', '_', field_name)  # replace special chars
    new_key = re.sub(r'_+', '_', new_key)                # collapse underscores
    new_key = new_key.strip('_')                         # trim underscores

    return new_key


def sanitize_record_keys(obj: Any) -> Any:
    """
    Recursively replace spaces and other special characters in dictionary keys with underscores.
    Works for nested dictionaries and lists of dictionaries.
    """
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            new_key = sanitize_field_name(k)
            new_obj[new_key] = sanitize_record_keys(v)
        return new_obj
    elif isinstance(obj, list):
        return [sanitize_record_keys(item) for item in obj]
    else:
        return obj
