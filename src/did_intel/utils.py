"""
Shared utility functions used across the did_intel package.
"""


def clean_number(number) -> str:
    """Extract 10-digit phone number from any input string or int.

    Strips non-digit characters.  If the result starts with '1' and has
    11 digits the leading country code is removed.  Returns the 10-digit
    string or an empty string when the input is unusable.
    """
    if not number or not isinstance(number, (str, int)):
        return ""
    cleaned = "".join(filter(str.isdigit, str(number)))
    if cleaned.startswith("1") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    return cleaned if len(cleaned) == 10 else ""
