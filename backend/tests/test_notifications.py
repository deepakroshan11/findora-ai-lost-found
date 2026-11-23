import notifications
from notifications import _build_text, is_valid_email, parse_contact, send_email


def test_parse_contact_email_and_phone():
    assert parse_contact("a@b.com | +91 98450 12367") == ("a@b.com", "+91 98450 12367")


def test_parse_contact_email_only():
    assert parse_contact("a@b.com") == ("a@b.com", None)


def test_parse_contact_trailing_separator_has_no_phone():
    assert parse_contact("a@b.com |") == ("a@b.com", None)


def test_is_valid_email():
    assert is_valid_email("deepak@example.com")
    assert is_valid_email("  deepak@example.com ")
    assert not is_valid_email("deepak@")
    assert not is_valid_email("deepak example.com")
    assert not is_valid_email("")


LOST = {"title": "Black leather wallet", "description": "tan stitching", "location": "Bus stand"}
FOUND = {
    "title": "Wallet found",
    "description": "black, silver plate",
    "location": "Gandhipuram",
    "contact_info": "finder@example.com | +91 90000 00000",
}


def test_text_email_tells_owner_how_to_reach_finder():
    text = _build_text("lost", LOST, FOUND, 0.9)
    assert "90.0%" in text
    assert "Black leather wallet" in text
    assert "finder@example.com" in text
    assert "+91 90000 00000" in text


def test_text_email_omits_mobile_when_not_given():
    found = {**FOUND, "contact_info": "finder@example.com"}
    assert "Mobile" not in _build_text("lost", LOST, found, 0.85)


def test_send_email_does_nothing_without_api_key(monkeypatch):
    monkeypatch.setattr(notifications, "ENABLED", False)
    assert send_email("a@b.com", "lost", LOST, FOUND, 0.9) is False


def test_send_email_rejects_invalid_address(monkeypatch):
    monkeypatch.setattr(notifications, "ENABLED", True)
    assert send_email("not-an-email", "lost", LOST, FOUND, 0.9) is False
