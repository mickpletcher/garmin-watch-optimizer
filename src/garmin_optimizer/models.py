from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator


def validate_stable_identifier(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)+", value):
        raise ValueError(f"Invalid stable setting identifier: {value}")
    return value


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"


class AuthenticationState(StrEnum):
    AUTHENTICATED = "authenticated"
    SIGN_IN_REQUIRED = "sign_in_required"
    UNKNOWN = "unknown"


class ReadSupport(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"
    UNKNOWN = "unknown"


class WriteSupport(StrEnum):
    AUTOMATIC = "automatic"
    GUIDED = "guided"
    READ_ONLY = "read-only"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class SimulationOutcome(StrEnum):
    RUNNING = "running"
    RESTORED = "restored"
    FAILED_RESTORED = "failed_restored"
    AMBIGUOUS_RESTORED = "ambiguous_restored"
    RESTORE_FAILED = "restore_failed"


class PlanClassification(StrEnum):
    ALREADY_COMPLIANT = "already_compliant"
    WILL_CHANGE = "will_change"
    WILL_ADD = "will_add"
    WILL_REMOVE = "will_remove"
    REQUIRES_USER_ACTION = "requires_user_action"
    UNSUPPORTED = "unsupported"
    UNKNOWN_CURRENT_VALUE = "unknown_current_value"
    BLOCKED = "blocked"


class CoverageState(StrEnum):
    CAPTURED = "captured"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    EXCLUDED = "excluded"


class AndroidDevice(BaseModel):
    serial: str
    state: str
    manufacturer: str | None = None
    model: str | None = None
    android_version: str | None = None


class GarminApp(BaseModel):
    package_name: str
    activity_name: str | None = None
    app_version: str | None = None
    confidence: float = 0.0


class GarminDevice(BaseModel):
    display_name: str
    model_hint: str | None = None
    firmware_version: str | None = None
    connected_state: str | None = None
    identity_source: str = "garmin_connect_ui"


class DiscoveredSetting(BaseModel):
    id: str
    screen_path: list[str]
    label: str
    current_value: str | None
    selectable_values: list[str] = Field(default_factory=list)
    resource_id: str | None = None
    content_description: str | None = None
    confidence: float
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    writable_candidate: bool = False
    notes: str = ""

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_stable_identifier(value)


class Capability(BaseModel):
    id: str
    title: str
    description: str
    read_support: ReadSupport
    write_support: WriteSupport
    adapter: str
    transport: str
    supported_values: list[JsonValue] = Field(default_factory=list)
    validation_rules: dict[str, JsonValue] = Field(default_factory=dict)
    requires_restart: bool = False
    requires_sync: bool = False
    requires_phone_action: bool = False
    requires_watch_confirmation: bool = False
    supported_models: list[str] = Field(default_factory=list)
    firmware_constraints: list[str] = Field(default_factory=list)
    rollback_supported: bool = False
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    evidence: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_stable_identifier(value)


class CapabilityManifest(BaseModel):
    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    transport: str = "android_ui_research"
    research_only: bool = True
    app_package: str
    app_version: str | None = None
    device_model: str | None = None
    firmware_version: str | None = None
    capabilities: list[Capability] = Field(default_factory=list)


class JournalEvent(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event: str
    status: str
    detail: str = ""


class WriteSimulationTransaction(BaseModel):
    transaction_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    setting_id: str
    label: str
    risk_level: RiskLevel
    original_value: str
    temporary_value: str
    user_confirmed: bool
    outcome: SimulationOutcome = SimulationOutcome.RUNNING
    change_verified: bool = False
    ambiguous_write: bool = False
    restore_attempted: bool = False
    restore_verified: bool = False
    errors: list[str] = Field(default_factory=list)
    events: list[JournalEvent] = Field(default_factory=list)


class SnapshotArtifact(BaseModel):
    schema_version: str = "1.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    host_os: str
    python_version: str
    adb_version: str | None = None
    appium_status: str | None = None
    authentication_state: AuthenticationState = AuthenticationState.UNKNOWN
    device: AndroidDevice | None = None
    garmin_app: GarminApp | None = None
    garmin_device: GarminDevice | None = None
    capability_manifest: CapabilityManifest | None = None
    screens_reached: list[str] = Field(default_factory=list)
    settings: list[DiscoveredSetting] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PocStatus(BaseModel):
    level: int
    summary: str
    warnings: list[str] = Field(default_factory=list)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileMetadata(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class ConfigurationTarget(StrictModel):
    manufacturer: Literal["Garmin"] = "Garmin"
    models: list[str] = Field(min_length=1)
    minimum_firmware: str | None = None

    @field_validator("models")
    @classmethod
    def validate_models(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("Target model names cannot be empty.")
        if len({item.casefold() for item in normalized}) != len(normalized):
            raise ValueError("Target model names must be unique.")
        return normalized


class ApplyPolicy(StrictModel):
    mode: Literal["merge", "strict"] = "merge"
    backup_before_apply: Literal[True] = True
    verify_after_apply: Literal[True] = True
    unsupported: Literal["report", "block"] = "report"
    require_confirmation_for_high_risk: Literal[True] = True


class DesiredConfiguration(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    profile: ProfileMetadata
    target: ConfigurationTarget
    apply_policy: ApplyPolicy = Field(default_factory=ApplyPolicy)
    settings: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("settings")
    @classmethod
    def validate_setting_ids(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        for identifier in value:
            if identifier != identifier.strip():
                raise ValueError("Setting identifiers cannot be empty or padded with whitespace.")
            validate_stable_identifier(identifier)
        return value


class ConfigurationOverlay(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(min_length=1, max_length=100)
    settings: dict[str, JsonValue] = Field(default_factory=dict)


class OverlayConflict(StrictModel):
    setting_id: str
    previous_overlay: str
    replacing_overlay: str


class OverlayResolution(StrictModel):
    configuration: DesiredConfiguration
    applied_overlays: list[str] = Field(default_factory=list)
    conflicts: list[OverlayConflict] = Field(default_factory=list)


class ObservedSettingState(StrictModel):
    id: str
    label: str
    value: JsonValue
    risk_level: RiskLevel = RiskLevel.HIGH
    readable: bool = True
    write_available: Literal[False] = False

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_stable_identifier(value)


class ObservedConfiguration(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    source_model: str
    firmware_version: str | None = None
    settings: dict[str, ObservedSettingState] = Field(default_factory=dict)


class CompatibilityIssue(StrictModel):
    code: str
    message: str
    blocking: bool = True


class PlanOperation(StrictModel):
    operation_id: str = Field(default_factory=lambda: uuid4().hex)
    setting_id: str
    label: str
    classification: PlanClassification
    old_value: JsonValue = None
    proposed_value: JsonValue = None
    adapter: str
    risk_level: RiskLevel
    dependencies: list[str] = Field(default_factory=list)
    requires_sync: bool = False
    requires_restart: bool = False
    rollback_supported: Literal[False] = False
    automatic: Literal[False] = False
    selected: bool = True
    guidance: str = ""

    @field_validator("setting_id")
    @classmethod
    def validate_setting_id(cls, value: str) -> str:
        return validate_stable_identifier(value)


class ChangePlan(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    job_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: Literal["snapshot", "bundle_comparison"]
    source_model: str
    target_model: str
    read_only: Literal[True] = True
    compatibility_issues: list[CompatibilityIssue] = Field(default_factory=list)
    operations: list[PlanOperation] = Field(default_factory=list)


class BundleFile(StrictModel):
    path: str
    sha256: str
    size_bytes: int = Field(ge=0)


class BundleCoverage(StrictModel):
    group: str
    state: CoverageState
    setting_count: int = Field(ge=0)
    note: str = ""


class BackupManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    application_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_model: str
    firmware_version: str | None = None
    research_only: Literal[True] = True
    physical_write_available: Literal[False] = False
    files: list[BundleFile] = Field(default_factory=list)
    coverage: list[BundleCoverage] = Field(default_factory=list)


class BundleValidationResult(StrictModel):
    valid: bool
    bundle_path: str
    checked_files: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
