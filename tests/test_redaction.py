from garmin_optimizer.services.redaction import RedactionService


def test_redacts_text_and_nested_sensitive_fields() -> None:
    redactor = RedactionService()
    raw = {
        "serial": "ABCDEF1234567890",
        "nested": {
            "message": "email test.user@example.com token=secret-value phone 615-555-1212",
            "password": "plain-text",
        },
    }
    output = redactor.redact_data(raw)
    rendered = str(output)

    assert "ABCDEF1234567890" not in rendered
    assert "test.user@example.com" not in rendered
    assert "secret-value" not in rendered
    assert "615-555-1212" not in rendered
    assert "plain-text" not in rendered


def test_sensitive_setting_values_are_suppressed() -> None:
    redactor = RedactionService()
    assert redactor.redact_setting_value("Emergency Contact", "Sample Person") == "<redacted-sensitive-value>"
    assert redactor.redact_setting_value("Units", None) is None
    assert redactor.redact_setting_value("Units", "Metric") == "Metric"
    nested = redactor.redact_data({"label": "Emergency Contact", "current_value": "Sample Person"})
    assert nested["current_value"] == "<redacted-sensitive-value>"
