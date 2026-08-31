from pathlib import Path

import pytest

from garmin_optimizer.exceptions import NavigationMismatchError
from garmin_optimizer.models import AuthenticationState, RiskLevel
from garmin_optimizer.services.redaction import RedactionService
from garmin_optimizer.services.ui_discovery import UiDiscoveryService


def service(tmp_path: Path, enabled: bool = False) -> UiDiscoveryService:
    return UiDiscoveryService(tmp_path, RedactionService(), enabled)


def test_parser_extracts_only_structured_setting_rows(tmp_path: Path) -> None:
    fixture = Path("tests/fixtures/settings_screen.xml").read_text(encoding="utf-8")
    rows = service(tmp_path).parse_page_source(fixture, ["Device", "System"])
    labels = {row.label: row for row in rows}

    assert set(labels) == {"Units", "Language", "Battery Saver"}
    assert labels["Units"].current_value == "Statute"
    assert labels["Units"].risk_level is RiskLevel.LOW
    assert labels["Battery Saver"].risk_level is RiskLevel.MEDIUM
    assert all(not row.writable_candidate for row in rows)


def test_login_screen_is_not_parsed_as_settings_and_auth_is_detected(tmp_path: Path) -> None:
    sign_in = Path("tests/fixtures/unexpected_screen.xml").read_text(encoding="utf-8")
    home = Path("tests/fixtures/authenticated_home.xml").read_text(encoding="utf-8")
    discovery = service(tmp_path)

    assert discovery.parse_page_source(sign_in, ["Unknown"]) == []
    assert discovery.detect_authentication_state(sign_in) is AuthenticationState.SIGN_IN_REQUIRED
    assert discovery.detect_authentication_state(home) is AuthenticationState.AUTHENTICATED
    assert discovery.detect_authentication_state("<hierarchy />") is AuthenticationState.UNKNOWN


def test_diagnostic_dump_is_always_sanitized(tmp_path: Path) -> None:
    discovery = service(tmp_path)
    assert discovery.dump_sanitized_xml("<hierarchy />", "disabled") is None
    output = discovery.dump_sanitized_xml(
        '<hierarchy text="Sample Person test.user@example.com token=secret-value ABCDEF1234567890" />',
        "manual/dump",
        force=True,
    )
    assert output is not None
    content = output.read_text(encoding="utf-8")
    assert "test.user@example.com" not in content
    assert "secret-value" not in content
    assert "ABCDEF1234567890" not in content
    assert "Sample Person" not in content


def test_malformed_hierarchy_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(NavigationMismatchError):
        service(tmp_path).visible_texts("<hierarchy>")
