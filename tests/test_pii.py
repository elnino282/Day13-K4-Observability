from app.pii import scrub_text, scrub_value


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_recursive_scrub_covers_nested_sensitive_values() -> None:
    value = {
        "contact": [
            "student@vinuni.edu.vn",
            {"card": "4111 1111 1111 1111", "passport": "B1234567"},
        ]
    }

    scrubbed = scrub_value(value)

    rendered = str(scrubbed)
    assert "student@" not in rendered
    assert "4111 1111" not in rendered
    assert "B1234567" not in rendered
    assert "REDACTED_EMAIL" in rendered
    assert "REDACTED_CREDIT_CARD" in rendered
    assert "REDACTED_PASSPORT" in rendered
