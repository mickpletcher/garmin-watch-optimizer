from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import JsonValue

from garmin_optimizer.models import (
    ChangePlan,
    CompatibilityIssue,
    DesiredConfiguration,
    ObservedConfiguration,
    ObservedSettingState,
    PlanClassification,
    PlanOperation,
    RiskLevel,
    SnapshotArtifact,
)
from garmin_optimizer.services.persistence import atomic_write_json, atomic_write_text, utc_file_stamp
from garmin_optimizer.services.redaction import RedactionService


class PlanningService:
    def __init__(self, plans_dir: Path, redactor: RedactionService) -> None:
        self.plans_dir = plans_dir
        self.redactor = redactor

    def observed_from_snapshot(self, snapshot: SnapshotArtifact) -> ObservedConfiguration:
        device = snapshot.garmin_device
        source_model = (device.model_hint or device.display_name) if device else "Unknown Garmin watch"
        settings = {
            item.id: ObservedSettingState(
                id=item.id,
                label=item.label,
                value=item.current_value,
                risk_level=item.risk_level,
                readable=item.current_value is not None,
            )
            for item in snapshot.settings
        }
        return ObservedConfiguration(
            source_model=source_model,
            firmware_version=device.firmware_version if device else None,
            settings=settings,
        )

    def plan(
        self,
        desired: DesiredConfiguration,
        observed: ObservedConfiguration,
    ) -> ChangePlan:
        issues = self._compatibility_issues(desired, observed)
        model_blocked = any(issue.blocking for issue in issues)
        operations: list[PlanOperation] = []

        for setting_id in sorted(desired.settings):
            proposed = desired.settings[setting_id]
            current = observed.settings.get(setting_id)
            if model_blocked:
                operations.append(
                    self._operation(
                        setting_id,
                        current.label if current else setting_id,
                        PlanClassification.BLOCKED,
                        current.value if current else None,
                        proposed,
                        current.risk_level if current else RiskLevel.HIGH,
                        "blocked",
                        "Target model or firmware is incompatible. Nothing can be applied.",
                    )
                )
            elif current is None:
                classification = (
                    PlanClassification.BLOCKED
                    if desired.apply_policy.unsupported == "block"
                    else PlanClassification.UNSUPPORTED
                )
                operations.append(
                    self._operation(
                        setting_id,
                        setting_id,
                        classification,
                        None,
                        proposed,
                        RiskLevel.HIGH,
                        "read_only",
                        "The setting was not observed. Preserve it and collect capability evidence before acting.",
                    )
                )
            elif not current.readable or current.value is None:
                operations.append(
                    self._operation(
                        setting_id,
                        current.label,
                        PlanClassification.UNKNOWN_CURRENT_VALUE,
                        None,
                        proposed,
                        current.risk_level,
                        "read_only",
                        "The current value is unknown. No change can be planned safely.",
                    )
                )
            elif self._normalize(current.value) == self._normalize(proposed):
                operations.append(
                    self._operation(
                        setting_id,
                        current.label,
                        PlanClassification.ALREADY_COMPLIANT,
                        current.value,
                        proposed,
                        current.risk_level,
                        "none",
                        "No action is required.",
                    )
                )
            else:
                operations.append(
                    self._operation(
                        setting_id,
                        current.label,
                        PlanClassification.REQUIRES_USER_ACTION,
                        current.value,
                        proposed,
                        current.risk_level,
                        "guided_on_watch",
                        f"Change {current.label} manually in a Garmin-owned interface, then rerun the audit.",
                    )
                )

        if desired.apply_policy.mode == "strict":
            for setting_id in sorted(observed.settings.keys() - desired.settings.keys()):
                current = observed.settings[setting_id]
                operations.append(
                    self._operation(
                        setting_id,
                        current.label,
                        PlanClassification.BLOCKED,
                        current.value,
                        None,
                        current.risk_level,
                        "blocked",
                        "Strict removal is blocked because the project has no physical write capability.",
                    )
                )

        return ChangePlan(
            source="snapshot",
            source_model=observed.source_model,
            target_model=desired.target.models[0],
            compatibility_issues=issues,
            operations=operations,
        )

    def compare(
        self,
        older: DesiredConfiguration,
        newer: DesiredConfiguration,
    ) -> ChangePlan:
        operations: list[PlanOperation] = []
        keys = sorted(older.settings.keys() | newer.settings.keys())
        for setting_id in keys:
            old_value = older.settings.get(setting_id)
            new_value = newer.settings.get(setting_id)
            if setting_id not in older.settings:
                classification = PlanClassification.WILL_ADD
            elif setting_id not in newer.settings:
                classification = PlanClassification.WILL_REMOVE
            elif self._normalize(old_value) == self._normalize(new_value):
                classification = PlanClassification.ALREADY_COMPLIANT
            else:
                classification = PlanClassification.WILL_CHANGE
            operations.append(
                self._operation(
                    setting_id,
                    setting_id,
                    classification,
                    old_value,
                    new_value,
                    RiskLevel.HIGH,
                    "comparison_only",
                    "Read-only bundle comparison. No apply path is attached.",
                )
            )

        older_models = {item.casefold() for item in older.target.models}
        newer_models = {item.casefold() for item in newer.target.models}
        issues = []
        if not older_models & newer_models:
            issues.append(
                CompatibilityIssue(
                    code="model_specific_difference",
                    message="The bundles target different watch models. Review every difference for portability.",
                    blocking=False,
                )
            )
        return ChangePlan(
            source="bundle_comparison",
            source_model=older.target.models[0],
            target_model=newer.target.models[0],
            compatibility_issues=issues,
            operations=operations,
        )

    def save(self, plan: ChangePlan, prefix: str = "plan") -> tuple[Path, Path]:
        base = self.plans_dir / f"{prefix}_{utc_file_stamp()}_{plan.job_id[:8]}"
        json_path = base.with_suffix(".json")
        markdown_path = base.with_suffix(".md")
        payload = self.redactor.redact_data(plan.model_dump(mode="json"))
        atomic_write_json(json_path, payload)
        atomic_write_text(markdown_path, self._markdown(payload))
        return json_path, markdown_path

    def _compatibility_issues(
        self,
        desired: DesiredConfiguration,
        observed: ObservedConfiguration,
    ) -> list[CompatibilityIssue]:
        issues: list[CompatibilityIssue] = []
        if observed.source_model.casefold() not in {item.casefold() for item in desired.target.models}:
            issues.append(
                CompatibilityIssue(
                    code="model_mismatch",
                    message=(
                        f"Observed model '{observed.source_model}' is not in the target model allowlist."
                    ),
                )
            )
        minimum = desired.target.minimum_firmware
        if minimum and observed.firmware_version:
            observed_version = self._firmware_tuple(observed.firmware_version)
            minimum_version = self._firmware_tuple(minimum)
            if observed_version is None or minimum_version is None:
                issues.append(
                    CompatibilityIssue(
                        code="firmware_unverified",
                        message="Firmware compatibility could not be compared safely.",
                    )
                )
            elif observed_version < minimum_version:
                issues.append(
                    CompatibilityIssue(
                        code="firmware_too_old",
                        message=(
                            f"Observed firmware {observed.firmware_version} is older than required {minimum}."
                        ),
                    )
                )
        elif minimum and not observed.firmware_version:
            issues.append(
                CompatibilityIssue(
                    code="firmware_unknown",
                    message="Target firmware is constrained but the observed firmware is unknown.",
                )
            )
        return issues

    def _operation(
        self,
        setting_id: str,
        label: str,
        classification: PlanClassification,
        old_value: JsonValue,
        proposed_value: JsonValue,
        risk_level: RiskLevel,
        adapter: str,
        guidance: str,
    ) -> PlanOperation:
        selected = classification is PlanClassification.REQUIRES_USER_ACTION
        return PlanOperation(
            setting_id=setting_id,
            label=label,
            classification=classification,
            old_value=old_value,
            proposed_value=proposed_value,
            adapter=adapter,
            risk_level=risk_level,
            selected=selected,
            guidance=guidance,
        )

    def _normalize(self, value: JsonValue) -> JsonValue:
        if isinstance(value, dict):
            return {key: self._normalize(value[key]) for key in sorted(value)}
        if isinstance(value, list):
            return [self._normalize(item) for item in value]
        if isinstance(value, str):
            return value.strip().casefold()
        return value

    def _firmware_tuple(self, value: str) -> tuple[int, ...] | None:
        if not re.fullmatch(r"\d+(?:\.\d+)*", value.strip()):
            return None
        return tuple(int(part) for part in value.split("."))

    def _markdown(self, payload: dict[str, Any]) -> str:
        lines = [
            "# Garmin Watch Optimizer Read-Only Plan",
            "",
            "> This plan cannot apply settings. Every mismatch is guided, unsupported, or blocked.",
            "",
            f"- Job: {payload['job_id']}",
            f"- Source model: {payload['source_model']}",
            f"- Target model: {payload['target_model']}",
            f"- Read only: {payload['read_only']}",
            "",
            "## Compatibility",
        ]
        issues = payload.get("compatibility_issues", [])
        lines.extend([f"- {item['code']}: {item['message']}" for item in issues] or ["- No blocking issue found."])
        lines.extend(["", "## Operations"])
        for item in payload.get("operations", []):
            lines.extend(
                [
                    "",
                    f"### {item['setting_id']}",
                    f"- Classification: {item['classification']}",
                    f"- Risk: {item['risk_level']}",
                    f"- Adapter: {item['adapter']}",
                    f"- Old: {item['old_value']}",
                    f"- Proposed: {item['proposed_value']}",
                    f"- Guidance: {item['guidance']}",
                ]
            )
        return "\n".join(lines) + "\n"
