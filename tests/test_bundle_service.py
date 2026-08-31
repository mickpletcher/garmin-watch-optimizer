import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from garmin_optimizer.exceptions import ArchiveSecurityError, BundleValidationError
from garmin_optimizer.models import DiscoveredSetting, GarminDevice, SnapshotArtifact
from garmin_optimizer.services import bundle_service
from garmin_optimizer.services.bundle_service import ConfigurationBundleService
from garmin_optimizer.services.configuration_service import ConfigurationService
from garmin_optimizer.services.redaction import RedactionService


def service(tmp_path: Path) -> ConfigurationBundleService:
    redactor = RedactionService()
    return ConfigurationBundleService(
        bundles_dir=tmp_path / "bundles",
        imports_dir=tmp_path / "imports",
        exports_dir=tmp_path / "exports",
        configuration=ConfigurationService(redactor),
        redactor=redactor,
    )


def snapshot() -> SnapshotArtifact:
    return SnapshotArtifact(
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
                screen_path=["Device Settings"],
                label="Units",
                current_value="Statute",
                confidence=0.95,
            ),
            DiscoveredSetting(
                id="observed.0123456789abcdef",
                screen_path=["Device Settings"],
                label="Wi-Fi Network",
                current_value="Synthetic Network",
                confidence=0.85,
            ),
        ],
        warnings=["Visible screen only."],
    )


def test_capture_bundle_has_explicit_coverage_and_valid_checksums(tmp_path: Path) -> None:
    bundles = service(tmp_path)
    output = bundles.capture(snapshot(), "Known Good")
    result = bundles.validate(output)
    configuration = bundles.load_configuration(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))

    assert result.valid
    assert set(result.checked_files) == {"config.yaml", "manifest.json", "summary.md"}
    assert configuration.settings["system.units"] == "Statute"
    assert configuration.settings["observed.0123456789abcdef"] == "<redacted-sensitive-value>"
    assert manifest["physical_write_available"] is False
    assert {item["state"] for item in manifest["coverage"]} >= {"captured", "partial", "unavailable"}


def test_tampered_bundle_fails_integrity_validation(tmp_path: Path) -> None:
    bundles = service(tmp_path)
    output = bundles.capture(snapshot(), "Known Good")
    (output / "summary.md").write_text("tampered\n", encoding="utf-8")

    result = bundles.validate(output)

    assert not result.valid
    assert "Checksum or size mismatch: summary.md" in result.errors
    with pytest.raises(BundleValidationError):
        bundles.require_valid(output)


def test_snapshot_and_bundle_structure_fail_closed(tmp_path: Path) -> None:
    bundles = service(tmp_path)
    invalid_snapshot = tmp_path / "snapshot.json"
    invalid_snapshot.write_text("not json", encoding="utf-8")
    with pytest.raises(BundleValidationError, match="Snapshot validation failed"):
        bundles.load_snapshot(invalid_snapshot)
    bundles.MAX_SNAPSHOT_BYTES = 1
    with pytest.raises(BundleValidationError, match="10 MiB"):
        bundles.load_snapshot(invalid_snapshot)
    with pytest.raises(BundleValidationError, match="watch identity"):
        bundles.capture(SnapshotArtifact(host_os="Windows", python_version="3.12"), "Missing")

    empty = tmp_path / "empty"
    empty.mkdir()
    missing = bundles.validate(empty)
    assert not missing.valid
    assert "Missing required files" in missing.errors[0]

    output = bundles.capture(snapshot(), "Known Good")
    extra = output / "raw"
    extra.mkdir()
    unexpected = bundles.validate(output)
    assert not unexpected.valid
    assert any("Unexpected files: raw" in error for error in unexpected.errors)
    assert any("regular file: raw" in error for error in unexpected.errors)


def test_bad_manifest_and_configuration_are_reported(tmp_path: Path) -> None:
    bundles = service(tmp_path)
    output = bundles.capture(snapshot(), "Known Good")
    (output / "manifest.json").write_text("{}", encoding="utf-8")
    result = bundles.validate(output)
    assert not result.valid
    assert any("Manifest validation failed" in error for error in result.errors)

    output = bundles.capture(snapshot(), "Known Good Two")
    (output / "config.yaml").write_text("schema_version: [", encoding="utf-8")
    result = bundles.validate(output)
    assert not result.valid
    assert any("parsing failed" in error for error in result.errors)


def test_capture_persistence_failure_leaves_no_partial_bundle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bundles = service(tmp_path)

    def fail_manifest(*args, **kwargs):
        raise OSError("injected persistence failure")

    monkeypatch.setattr(bundle_service, "atomic_write_json", fail_manifest)

    with pytest.raises(OSError, match="injected persistence failure"):
        bundles.capture(snapshot(), "Injected Failure")
    assert not list((tmp_path / "bundles").iterdir())


def test_archive_export_import_round_trip_is_valid(tmp_path: Path) -> None:
    bundles = service(tmp_path)
    output = bundles.capture(snapshot(), "Known Good")
    archive = bundles.export_archive(output)

    imported = bundles.import_archive(archive)

    assert bundles.validate(imported).valid
    assert imported.is_relative_to(tmp_path / "imports")
    assert bundles.load_configuration(imported).settings["system.units"] == "Statute"


def test_archive_path_traversal_and_compression_bombs_are_blocked(tmp_path: Path) -> None:
    bundles = service(tmp_path)
    traversal = tmp_path / "traversal.zip"
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("config.yaml", "{}")
        archive.writestr("manifest.json", "{}")
        archive.writestr("../summary.md", "blocked")
    with pytest.raises(ArchiveSecurityError):
        bundles.import_archive(traversal)

    compressed = tmp_path / "compressed.zip"
    with zipfile.ZipFile(compressed, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("config.yaml", "{}")
        archive.writestr("manifest.json", "{}")
        archive.writestr("summary.md", "A" * 1_000_000)
    with pytest.raises(ArchiveSecurityError, match="compression ratio"):
        bundles.import_archive(compressed)


def test_archive_size_bad_zip_and_checksum_fail_closed(tmp_path: Path) -> None:
    bundles = service(tmp_path)
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_text("not a zip", encoding="utf-8")
    with pytest.raises(ArchiveSecurityError, match="Unable to read"):
        bundles.import_archive(bad_zip)

    bundles.MAX_ARCHIVE_BYTES = 1
    with pytest.raises(ArchiveSecurityError, match="20 MiB"):
        bundles.import_archive(bad_zip)

    bundles = service(tmp_path)
    output = bundles.capture(snapshot(), "Known Good")
    archive_path = tmp_path / "tampered.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(output / "config.yaml", arcname="config.yaml")
        archive.write(output / "manifest.json", arcname="manifest.json")
        archive.writestr("summary.md", "tampered")
    with pytest.raises(BundleValidationError, match="checksum or size mismatch"):
        bundles.import_archive(archive_path)


def test_import_redacts_summary_and_rebuilds_checksums(tmp_path: Path) -> None:
    bundles = service(tmp_path)
    output = bundles.capture(snapshot(), "Known Good")
    summary_path = output / "summary.md"
    summary_path.write_text("Contact sample.user@example.invalid\n", encoding="utf-8")
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = output / record["path"]
        content = path.read_bytes()
        record["sha256"] = hashlib.sha256(content).hexdigest()
        record["size_bytes"] = len(content)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    archive = bundles.export_archive(output)

    imported = bundles.import_archive(archive)

    assert "example.invalid" not in (imported / "summary.md").read_text(encoding="utf-8")
    assert bundles.validate(imported).valid
