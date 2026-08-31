from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from pydantic import ValidationError

from garmin_optimizer import __version__
from garmin_optimizer.exceptions import ArchiveSecurityError, BundleValidationError, ConfigurationError
from garmin_optimizer.models import (
    ApplyPolicy,
    BackupManifest,
    BundleCoverage,
    BundleFile,
    BundleValidationResult,
    ConfigurationTarget,
    CoverageState,
    DesiredConfiguration,
    ProfileMetadata,
    SnapshotArtifact,
)
from garmin_optimizer.services.configuration_service import ConfigurationService
from garmin_optimizer.services.persistence import atomic_write_json, atomic_write_text, utc_file_stamp
from garmin_optimizer.services.redaction import RedactionService


class ConfigurationBundleService:
    REQUIRED_FILES = {"config.yaml", "manifest.json", "summary.md"}
    CHECKSUM_FILES = {"config.yaml", "summary.md"}
    KNOWN_GROUPS = ("activities", "controls", "glances", "hot_keys", "power", "system", "watch_face")
    MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024
    MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
    MAX_MEMBER_BYTES = 5 * 1024 * 1024
    MAX_TOTAL_UNCOMPRESSED_BYTES = 10 * 1024 * 1024
    MAX_COMPRESSION_RATIO = 100

    def __init__(
        self,
        bundles_dir: Path,
        imports_dir: Path,
        exports_dir: Path,
        configuration: ConfigurationService,
        redactor: RedactionService,
    ) -> None:
        self.bundles_dir = bundles_dir
        self.imports_dir = imports_dir
        self.exports_dir = exports_dir
        self.configuration = configuration
        self.redactor = redactor

    def load_snapshot(self, path: Path) -> SnapshotArtifact:
        if path.is_symlink():
            raise BundleValidationError("Symbolic-link snapshots are blocked.")
        try:
            if path.stat().st_size > self.MAX_SNAPSHOT_BYTES:
                raise BundleValidationError("Snapshot exceeds the 10 MiB safety limit.")
            payload = json.loads(path.read_text(encoding="utf-8"))
            return SnapshotArtifact.model_validate(payload)
        except BundleValidationError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            raise BundleValidationError(f"Snapshot validation failed: {exc}") from exc

    def capture(
        self,
        snapshot: SnapshotArtifact,
        name: str,
        description: str = "",
    ) -> Path:
        device = snapshot.garmin_device
        if device is None:
            raise BundleValidationError("A captured Garmin watch identity is required to create a bundle.")
        source_model = device.model_hint or device.display_name
        slug = self._slug(name)
        bundle_dir = self.bundles_dir / f"{slug}_{utc_file_stamp()}"
        temporary = self.bundles_dir / f".{slug}.{uuid4().hex}.tmp"
        temporary.mkdir(parents=True, exist_ok=False)
        try:
            settings = {
                item.id: self.redactor.redact_setting_value(item.label, item.current_value)
                for item in snapshot.settings
                if item.current_value is not None
            }
            desired = DesiredConfiguration(
                profile=ProfileMetadata(
                    name=self.redactor.redact_text(name),
                    description=self.redactor.redact_text(description),
                ),
                target=ConfigurationTarget(
                    models=[source_model],
                    minimum_firmware=device.firmware_version,
                ),
                apply_policy=ApplyPolicy(),
                settings={key: settings[key] for key in sorted(settings)},
            )
            config_path = self.configuration.save(desired, temporary / "config.yaml")
            coverage = self._coverage(snapshot)
            summary_path = temporary / "summary.md"
            atomic_write_text(summary_path, self._summary(snapshot, desired, coverage))
            manifest = BackupManifest(
                application_version=__version__,
                source_model=source_model,
                firmware_version=device.firmware_version,
                files=[self._file_record(config_path), self._file_record(summary_path)],
                coverage=coverage,
            )
            atomic_write_json(
                temporary / "manifest.json",
                self.redactor.redact_data(manifest.model_dump(mode="json")),
            )
            self.require_valid(temporary)
            os.replace(temporary, bundle_dir)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return bundle_dir

    def validate(self, bundle_path: Path) -> BundleValidationResult:
        errors: list[str] = []
        checked: list[str] = []
        if bundle_path.is_symlink() or not bundle_path.is_dir():
            return BundleValidationResult(
                valid=False,
                bundle_path=str(bundle_path),
                errors=["Bundle must be a real directory, not a symbolic link."],
            )
        entries = list(bundle_path.iterdir())
        present = {item.name for item in entries}
        missing = self.REQUIRED_FILES - present
        unexpected = present - self.REQUIRED_FILES
        if missing:
            errors.append(f"Missing required files: {', '.join(sorted(missing))}")
        if unexpected:
            errors.append(f"Unexpected files: {', '.join(sorted(unexpected))}")
        for item in entries:
            if item.is_symlink():
                errors.append(f"Symbolic-link bundle member is blocked: {item.name}")
            elif not item.is_file():
                errors.append(f"Bundle member must be a regular file: {item.name}")
        if errors:
            return BundleValidationResult(
                valid=False,
                bundle_path=str(bundle_path),
                errors=errors,
            )

        try:
            manifest_payload = json.loads((bundle_path / "manifest.json").read_text(encoding="utf-8"))
            manifest = BackupManifest.model_validate(manifest_payload)
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            errors.append(f"Manifest validation failed: {exc}")
            manifest = None

        try:
            self.configuration.load(bundle_path / "config.yaml")
            checked.append("config.yaml")
        except ConfigurationError as exc:
            errors.append(str(exc))

        if manifest:
            records = {item.path: item for item in manifest.files}
            if set(records) != self.CHECKSUM_FILES:
                errors.append("Manifest checksum records must contain exactly config.yaml and summary.md.")
            for relative_path in sorted(self.CHECKSUM_FILES & records.keys()):
                path = bundle_path / relative_path
                if path.is_symlink():
                    errors.append(f"Symbolic-link bundle member is blocked: {relative_path}")
                    continue
                try:
                    record = self._file_record(path)
                except OSError as exc:
                    errors.append(f"Unable to inspect {relative_path}: {exc}")
                    continue
                expected = records[relative_path]
                if record.sha256 != expected.sha256 or record.size_bytes != expected.size_bytes:
                    errors.append(f"Checksum or size mismatch: {relative_path}")
                else:
                    checked.append(relative_path)
            checked.append("manifest.json")

        return BundleValidationResult(
            valid=not errors,
            bundle_path=str(bundle_path),
            checked_files=sorted(set(checked)),
            errors=errors,
        )

    def require_valid(self, bundle_path: Path) -> BundleValidationResult:
        result = self.validate(bundle_path)
        if not result.valid:
            raise BundleValidationError("Bundle validation failed: " + "; ".join(result.errors))
        return result

    def load_configuration(self, path: Path) -> DesiredConfiguration:
        if path.is_dir():
            self.require_valid(path)
            return self.configuration.load(path / "config.yaml")
        return self.configuration.load(path)

    def export_archive(self, bundle_path: Path) -> Path:
        self.require_valid(bundle_path)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        output = self.exports_dir / f"{self._slug(bundle_path.name)}_{utc_file_stamp()}.zip"
        temporary = output.with_name(f".{output.name}.{uuid4().hex}.tmp")
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name in sorted(self.REQUIRED_FILES):
                    archive.write(bundle_path / name, arcname=name)
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
        return output

    def import_archive(self, archive_path: Path) -> Path:
        if archive_path.is_symlink():
            raise ArchiveSecurityError("Symbolic-link archives are blocked.")
        try:
            if archive_path.stat().st_size > self.MAX_ARCHIVE_BYTES:
                raise ArchiveSecurityError("Archive exceeds the 20 MiB safety limit.")
        except OSError as exc:
            raise ArchiveSecurityError(f"Unable to inspect archive: {exc}") from exc

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                members = archive.infolist()
                self._validate_archive_members(members)
                payloads = {item.filename: archive.read(item) for item in members}
        except ArchiveSecurityError:
            raise
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise ArchiveSecurityError(f"Unable to read bundle archive: {exc}") from exc

        try:
            manifest = BackupManifest.model_validate(json.loads(payloads["manifest.json"].decode("utf-8")))
            config_text = payloads["config.yaml"].decode("utf-8")
            summary_text = payloads["summary.md"].decode("utf-8")
        except (KeyError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            raise BundleValidationError(f"Archive content validation failed: {exc}") from exc

        records = {item.path: item for item in manifest.files}
        if set(records) != self.CHECKSUM_FILES:
            raise BundleValidationError("Archive manifest checksum records are incomplete.")
        for name in self.CHECKSUM_FILES:
            content = payloads[name]
            if hashlib.sha256(content).hexdigest() != records[name].sha256 or len(content) != records[name].size_bytes:
                raise BundleValidationError(f"Archive checksum or size mismatch: {name}")

        desired = self.configuration.load_text(config_text, ".yaml")
        slug = self._slug(archive_path.stem)
        destination = self.imports_dir / f"{slug}_{utc_file_stamp()}"
        temporary = self.imports_dir / f".{slug}.{uuid4().hex}.tmp"
        temporary.mkdir(parents=True, exist_ok=False)
        try:
            config_path = self.configuration.save(desired, temporary / "config.yaml")
            summary_path = temporary / "summary.md"
            atomic_write_text(summary_path, self.redactor.redact_text(summary_text))
            sanitized_manifest = manifest.model_copy(
                update={"files": [self._file_record(config_path), self._file_record(summary_path)]}
            )
            atomic_write_json(
                temporary / "manifest.json",
                self.redactor.redact_data(sanitized_manifest.model_dump(mode="json")),
            )
            self.require_valid(temporary)
            os.replace(temporary, destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return destination

    def _validate_archive_members(self, members: list[zipfile.ZipInfo]) -> None:
        names = {item.filename for item in members}
        if names != self.REQUIRED_FILES or len(members) != len(self.REQUIRED_FILES):
            raise ArchiveSecurityError("Archive must contain exactly config.yaml, manifest.json, and summary.md.")
        total_size = 0
        for item in members:
            pure = PurePosixPath(item.filename)
            if pure.is_absolute() or len(pure.parts) != 1 or ".." in pure.parts:
                raise ArchiveSecurityError(f"Unsafe archive path: {item.filename}")
            mode = (item.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ArchiveSecurityError(f"Symbolic-link archive member is blocked: {item.filename}")
            if item.file_size > self.MAX_MEMBER_BYTES:
                raise ArchiveSecurityError(f"Archive member exceeds 5 MiB: {item.filename}")
            total_size += item.file_size
            if item.compress_size and item.file_size / item.compress_size > self.MAX_COMPRESSION_RATIO:
                raise ArchiveSecurityError(f"Suspicious compression ratio: {item.filename}")
        if total_size > self.MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ArchiveSecurityError("Archive exceeds the 10 MiB uncompressed safety limit.")

    def _coverage(self, snapshot: SnapshotArtifact) -> list[BundleCoverage]:
        groups: dict[str, list] = {}
        for setting in snapshot.settings:
            groups.setdefault(setting.id.split(".", 1)[0], []).append(setting)
        result: list[BundleCoverage] = []
        for group in self.KNOWN_GROUPS:
            items = groups.get(group, [])
            if not items:
                result.append(
                    BundleCoverage(
                        group=group,
                        state=CoverageState.UNAVAILABLE,
                        setting_count=0,
                        note="Not observed on the captured settings screen.",
                    )
                )
                continue
            readable = [item for item in items if item.current_value is not None]
            state = CoverageState.CAPTURED if len(readable) == len(items) else CoverageState.PARTIAL
            result.append(
                BundleCoverage(
                    group=group,
                    state=state,
                    setting_count=len(readable),
                    note="Visible read-only settings only.",
                )
            )
        observed_items = groups.get("observed", [])
        if observed_items:
            result.append(
                BundleCoverage(
                    group="unmapped_visible_settings",
                    state=CoverageState.PARTIAL,
                    setting_count=len(observed_items),
                    note="Captured with stable hashes because no semantic identifier is proven.",
                )
            )
        return result

    def _summary(
        self,
        snapshot: SnapshotArtifact,
        desired: DesiredConfiguration,
        coverage: list[BundleCoverage],
    ) -> str:
        lines = [
            "# Garmin Watch Optimizer Capture Bundle",
            "",
            "> Read-only research capture. This is not a native Garmin backup and cannot write to a watch.",
            "",
            f"- Profile: {desired.profile.name}",
            f"- Model: {desired.target.models[0]}",
            f"- Minimum firmware: {desired.target.minimum_firmware or 'unknown'}",
            f"- Captured settings: {len(desired.settings)}",
            "- Physical write capability: blocked",
            "",
            "## Coverage",
        ]
        lines.extend(
            f"- {item.group}: {item.state.value} ({item.setting_count}) {item.note}" for item in coverage
        )
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {self.redactor.redact_text(item)}" for item in snapshot.warnings)
        return self.redactor.redact_text("\n".join(lines) + "\n")

    def _file_record(self, path: Path) -> BundleFile:
        content = path.read_bytes()
        return BundleFile(
            path=path.name,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
        )

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
        return slug[:80] or "bundle"
