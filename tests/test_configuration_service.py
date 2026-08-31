import json
from pathlib import Path

import pytest

from garmin_optimizer.exceptions import ConfigurationError, ConfigurationSecurityError
from garmin_optimizer.models import ConfigurationOverlay
from garmin_optimizer.services.configuration_service import ConfigurationService
from garmin_optimizer.services.redaction import RedactionService


def service() -> ConfigurationService:
    return ConfigurationService(RedactionService())


def test_example_matches_generated_schema_and_round_trips(tmp_path: Path) -> None:
    configuration = service().load(Path("examples/enduro2.example.yaml"))
    output = tmp_path / "saved.yaml"
    service().save(configuration, output)

    assert service().load(output) == configuration
    committed = json.loads(Path("schemas/config.schema.json").read_text(encoding="utf-8"))
    generated = configuration.__class__.model_json_schema()
    generated["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    generated["$id"] = committed["$id"]
    assert committed == generated


def test_json_loading_dumping_and_overlay_validation(tmp_path: Path) -> None:
    configuration = service().load(Path("examples/enduro2.example.yaml"))
    json_path = tmp_path / "config.json"
    json_path.write_text(configuration.model_dump_json(), encoding="utf-8")

    assert service().load(json_path) == configuration
    assert "schema_version: '1.0'" in service().dump_text(configuration)

    invalid_overlay = tmp_path / "invalid.overlay.yaml"
    invalid_overlay.write_text("schema_version: '1.0'\nname: Bad\nsettings: {Bad.Id: value}\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        service().load_overlay(invalid_overlay)


@pytest.mark.parametrize(
    "payload",
    [
        "schema_version: '1.0'\nprofile: {name: Test}\ntarget: {models: [Enduro 2]}\nextra: true\n",
        (
            "schema_version: '1.0'\nprofile: {name: Test}\ntarget: {models: [Enduro 2]}\n"
            "settings: {System.Units: Metric}\n"
        ),
        "schema_version: '2.0'\nprofile: {name: Test}\ntarget: {models: [Enduro 2]}\n",
    ],
)
def test_invalid_configuration_fails_closed(payload: str) -> None:
    with pytest.raises(ConfigurationError):
        service().load_text(payload)


@pytest.mark.parametrize(
    "payload",
    [
        (
            "schema_version: '1.0'\nprofile: {name: Test}\ntarget: {models: [Enduro 2]}\n"
            "settings: {account.token: value}\n"
        ),
        "schema_version: '1.0'\nprofile: {name: sample.user@example.invalid}\ntarget: {models: [Enduro 2]}\n",
        "schema_version: '1.0'\nprofile: &p {name: Test}\ntarget: {models: [Enduro 2]}\ncopy: *p\n",
        "!!python/object/apply:os.system ['echo blocked']\n",
    ],
)
def test_sensitive_or_complex_yaml_is_blocked(payload: str) -> None:
    with pytest.raises(ConfigurationSecurityError):
        service().load_text(payload)


def test_configuration_size_limit_is_enforced() -> None:
    with pytest.raises(ConfigurationSecurityError):
        service().load_text("x" * (ConfigurationService.MAX_CONFIG_BYTES + 1))


def test_file_and_root_validation_errors_are_actionable(tmp_path: Path) -> None:
    unsupported = tmp_path / "config.txt"
    unsupported.write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must use"):
        service().load(unsupported)
    with pytest.raises(ConfigurationError, match="Unable to inspect"):
        service().load(tmp_path / "missing.yaml")
    with pytest.raises(ConfigurationError, match="root must be an object"):
        service().load_text("- one\n- two\n")
    with pytest.raises(ConfigurationError, match="parsing failed"):
        service().load_text("schema_version: [")

    oversized = tmp_path / "large.yaml"
    oversized.write_text("xx", encoding="utf-8")
    loader = service()
    loader.MAX_CONFIG_BYTES = 1
    with pytest.raises(ConfigurationSecurityError, match="1 MiB"):
        loader.load(oversized)


def test_overlays_are_ordered_report_conflicts_and_do_not_mutate_base() -> None:
    base = service().load(Path("examples/enduro2.example.yaml"))
    first = ConfigurationOverlay(
        name="Daily",
        settings={"system.units": "Statute", "power.battery_saver": "auto"},
    )
    second = ConfigurationOverlay(
        name="Race",
        settings={"system.units": "Statute UK", "system.time_format": "24_hour"},
    )

    result = service().resolve_overlays(base, [first, second])

    assert result.applied_overlays == ["Daily", "Race"]
    assert result.configuration.settings["system.units"] == "Statute UK"
    assert result.conflicts[0].setting_id == "system.units"
    assert base.settings["system.units"] == "Metric"
