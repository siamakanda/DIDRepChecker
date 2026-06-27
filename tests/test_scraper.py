import pytest
from did_intel.scraper import parse_robokiller_html


SAMPLE_POSITIVE_HTML = """
<html>
<body>
  <div id="userReputation" class="green">
    <h3>Positive</h3>
  </div>
  <div id="roboStatus" class="green">
    <h3>Allowed</h3>
  </div>
  <div id="userReports">
    <h3>1,234 reports</h3>
  </div>
  <div id="totalCall">
    <h3>5,678 calls</h3>
  </div>
  <div id="lastCall">
    <h3>January 15, 2024</h3>
  </div>
</body>
</html>
"""

SAMPLE_NEGATIVE_HTML = """
<html>
<body>
  <div id="userReputation" class="red">
    <h3>Negative</h3>
  </div>
  <div id="roboStatus" class="red">
    <h3>Blocked</h3>
  </div>
  <div id="userReports">
    <h3>42 reports</h3>
  </div>
  <div id="totalCall">
    <h3>99 calls</h3>
  </div>
  <div id="lastCall">
    <h3>December 31, 2023</h3>
  </div>
</body>
</html>
"""

NOT_FOUND_HTML = """
<html>
<body>
  <p>Phone number not found</p>
</body>
</html>
"""

INVALID_HTML = """
<html>
<body>
  <p>Short page</p>
</body>
</html>
"""


def test_parse_positive():
    result = parse_robokiller_html(SAMPLE_POSITIVE_HTML, "2125551234")
    assert result["phone_number"] == "2125551234"
    assert result["reputation"] == "Positive"
    assert result["robokiller_status"] == "Allowed"
    assert result["user_reports"] == "1234"
    assert result["total_calls"] == "5678"
    assert result["last_call"] == "January 15, 2024"
    assert result["scraped_at"]  # ISO timestamp


def test_parse_negative():
    result = parse_robokiller_html(SAMPLE_NEGATIVE_HTML, "2125559999")
    assert result["reputation"] == "Negative"
    assert result["robokiller_status"] == "Blocked"
    assert result["user_reports"] == "42"
    assert result["total_calls"] == "99"
    assert result["last_call"] == "December 31, 2023"


def test_parse_not_found():
    result = parse_robokiller_html(NOT_FOUND_HTML, "2125550000")
    assert result["reputation"] == "Not Found"
    assert result["robokiller_status"] == "N/A"


def test_parse_short_page():
    result = parse_robokiller_html(INVALID_HTML, "2125550000")
    assert result["reputation"] == "Invalid Page"


def test_parse_empty_html():
    result = parse_robokiller_html("", "2125550000")
    assert result["reputation"] in ("Parse Error",)


def test_parse_malformed_html():
    result = parse_robokiller_html("not even html", "2125550000")
    assert result["reputation"] == "Invalid Page"


def test_parse_no_data_available():
    long_html = "<html>" + ("x" * 5001) + "</html>"
    result = parse_robokiller_html(long_html, "2125550000")
    assert result["reputation"] == "No Data Available"
