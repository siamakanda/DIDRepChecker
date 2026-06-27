import pytest
from did_intel.utils import clean_number


@pytest.mark.parametrize("input_val, expected", [
    ("2125551234", "2125551234"),
    ("(212) 555-1234", "2125551234"),
    ("+1 (212) 555-1234", "2125551234"),
    ("12125551234", "2125551234"),
        ("212-555-1234", "2125551234"),
        ("DID: 2125551234", "2125551234"),
    ("+44 20 7946 0958", ""),              # international, not 10-digit US
    ("5551234", ""),                       # too short
    ("121255512345", ""),                  # 12 digits — too long
    ("", ""),
    (2125551234, "2125551234"),            # int input
    (None, ""),
    ("1234567890", "1234567890"),
])
def test_clean_number(input_val, expected):
    assert clean_number(input_val) == expected


def test_clean_number_deduplication():
    numbers = ["2125551234", "212-555-1234", "(212) 555-1234", "12125551234"]
    cleaned = [clean_number(n) for n in numbers]
    assert cleaned == ["2125551234"] * 4
    assert len(set(cleaned)) == 1
