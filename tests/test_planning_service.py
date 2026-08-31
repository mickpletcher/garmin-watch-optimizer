import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from garmin_optimizer.models import (
    ApplyPolicy,
    ConfigurationTarget,
    DesiredConfiguration,
    DiscoveredSetting,
    GarminDevice,
    ObservedConfiguration,
    ObservedSettingState,
    PlanClassification,
    ProfileMetadata,
    RiskLevel,
    SnapshotArtifact,
)
from garmin_optimizer.services.planning_service import PlanningService
from garmin_optimizer.services.redaction import RedactionService


def desired(settings, *, model: str = "Enduro 2", mode: str = "merge") -> DesiredConfiguration:
    return DesiredConfiguration(
        profile=ProfileMetadata(name="Test"),
        target=ConfigurationTarget(models=[model]),
        apply_policy=ApplyPolicy(mode=mode),
        settings=settings,
    )


def observed(settings, *, model: str = "Enduro 2") -> ObservedConfiguration:
    return ObservedConfiguration(
        source_model=model,
        firmware_version="18.16",
        settings={
            identifier: ObservedSettingState(
                id=identifier,
                label=identifier,
                value=value,
                risk_level=RiskLevel.LOW,
                readable=value is not None,
            )
            for identifier, value in settings.items()
        },
    )


def planner(tmp_path: Path) -> PlanningService:
    return PlanningService(tmp_path, RedactionService())


def test_plan_classifies_without_automatic_operations(tmp_path: Path) -> None:
    current = observed(
        {
            "system.units": "Statute",
            "system.language": "English",
            "power.battery_saver": None,
        }
    )
    target = desired(
        {
            "system.units": "Metric",
            "system.language": "English",
            "power.battery_saver": "Auto",
            "activities.favorites": ["trail_run"],
        }
    )

    result = planner(tmp_path).plan(target, current)
    classifications = {item.setting_id: item.classification for item in result.operations}

    assert classifications == {
        "activities.favorites": PlanClassification.UNSUPPORTED,
        "power.battery_saver": PlanClassification.UNKNOWN_CURRENT_VALUE,
        "system.language": PlanClassification.ALREADY_COMPLIANT,
        "system.units": PlanClassification.REQUIRES_USER_ACTION,
    }
    assert all(not item.automatic and not item.rollback_supported for item in result.operations)
    assert [item.setting_id for item in result.operations if item.selected] == ["system.units"]


def test_model_mismatch_and_strict_removal_are_blocked(tmp_path: Path) -> None:
    mismatch = planner(tmp_path).plan(
        desired({"system.units": "Metric"}, model="Enduro 3"),
        observed({"system.units": "Statute"}),
    )
    strict = planner(tmp_path).plan(
        desired({}, mode="strict"),
        observed({"system.units": "Statute"}),
    )

    assert mismatch.compatibility_issues[0].code == "model_mismatch"
    assert mismatch.operations[0].classification is PlanClassification.BLOCKED
    assert strict.operations[0].classification is PlanClassification.BLOCKED
    assert "no physical write capability" in strict.operations[0].guidance


def test_firmware_gates_and_unsupported_block_policy(tmp_path: Path) -> None:
    target = desired({"system.units": "Metric"})
    target.target.minimum_firmware = "19.0"
    old_firmware = observed({"system.units": "Statute"})
    old_firmware.firmware_version = "18.16"
    unknown_firmware = observed({"system.units": "Statute"})
    unknown_firmware.firmware_version = None
    invalid_firmware = observed({"system.units": "Statute"})
    invalid_firmware.firmware_version = "beta"

    assert planner(tmp_path).plan(target, old_firmware).compatibility_issues[0].code == "firmware_too_old"
    assert planner(tmp_path).plan(target, unknown_firmware).compatibility_issues[0].code == "firmware_unknown"
    assert planner(tmp_path).plan(target, invalid_firmware).compatibility_issues[0].code == "firmware_unverified"

    block_target = desired({"activities.favorites": ["trail_run"]})
    block_target.apply_policy.unsupported = "block"
    operation = planner(tmp_path).plan(block_target, observed({})).operations[0]
    assert operation.classification is PlanClassification.BLOCKED


def test_snapshot_conversion_preserves_read_only_observations(tmp_path: Path) -> None:
    snapshot = SnapshotArtifact(
        host_os="Windows",
        python_version="3.12",
        garmin_device=GarminDevice(
            display_name="Enduro 2",
            model_hint="Enduro 2",
            firmware_version="18.16",
        ),
        settings=[
            DiscoveredSetting(
                id="system.units",
                screen_path=["System"],
                label="Units",
                current_value="Statute",
                confidence=0.9,
                risk_level=RiskLevel.LOW,
            )
        ],
    )

    result = planner(tmp_path).observed_from_snapshot(snapshot)

    assert result.source_model == "Enduro 2"
    assert result.firmware_version == "18.16"
    assert result.settings["system.units"].write_available is False


def test_bundle_comparison_covers_all_diff_categories(tmp_path: Path) -> None:
    older = desired({"setting.same": "A", "setting.changed": "A", "setting.removed": True})
    newer = desired(
        {"setting.same": "A", "setting.changed": "B", "setting.added": False},
        model="fenix 8",
    )

    result = planner(tmp_path).compare(older, newer)
    classifications = {item.setting_id: item.classification for item in result.operations}

    assert classifications == {
        "setting.added": PlanClassification.WILL_ADD,
        "setting.changed": PlanClassification.WILL_CHANGE,
        "setting.removed": PlanClassification.WILL_REMOVE,
        "setting.same": PlanClassification.ALREADY_COMPLIANT,
    }
    assert result.compatibility_issues[0].code == "model_specific_difference"


def test_saved_plan_is_sanitized_json_and_markdown(tmp_path: Path) -> None:
    current = observed({"system.units": "sample.user@example.invalid"})
    result = planner(tmp_path).plan(desired({"system.units": "Metric"}), current)

    json_path, markdown_path = planner(tmp_path).save(result)

    assert "example.invalid" not in json_path.read_text(encoding="utf-8")
    assert "example.invalid" not in markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["read_only"] is True
    assert payload["job_id"] == result.job_id
    assert payload["operations"][0]["setting_id"] == "system.units"


@given(
    st.dictionaries(
        keys=st.sampled_from(["system.units", "system.language", "power.battery_saver"]),
        values=st.one_of(st.booleans(), st.integers(), st.text(max_size=20)),
        min_size=1,
    )
)
def test_equal_state_is_idempotent(settings) -> None:
    service = PlanningService(Path("runtime/test-plans"), RedactionService())
    result = service.plan(desired(settings), observed(settings))

    assert result.operations
    assert all(item.classification is PlanClassification.ALREADY_COMPLIANT for item in result.operations)
    assert all(not item.selected for item in result.operations)
