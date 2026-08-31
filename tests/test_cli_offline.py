from pathlib import Path

from garmin_optimizer import cli
from garmin_optimizer.models import DiscoveredSetting, GarminDevice, SnapshotArtifact


def fail_transport(*args, **kwargs):
    raise AssertionError("Offline commands must not construct device transports.")


def write_snapshot(path: Path) -> None:
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
                screen_path=["Device Settings"],
                label="Units",
                current_value="Statute",
                confidence=0.95,
            )
        ],
    )
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")


def test_offline_cli_commands_never_construct_adb_or_appium(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv("GARMIN_OPT_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(cli, "AdbService", fail_transport)
    monkeypatch.setattr(cli, "AppiumService", fail_transport)
    snapshot_path = tmp_path / "snapshot.json"
    write_snapshot(snapshot_path)

    validate_args = cli.build_parser().parse_args(["validate", "examples/enduro2.example.yaml"])
    assert cli.run(validate_args) == 0

    capture_args = cli.build_parser().parse_args(
        ["capture", "--snapshot", str(snapshot_path), "--name", "Test Capture", "--export-zip"]
    )
    assert cli.run(capture_args) == 0

    plan_args = cli.build_parser().parse_args(
        [
            "plan",
            "examples/enduro2.example.yaml",
            "--snapshot",
            str(snapshot_path),
            "--overlay",
            "examples/race.overlay.yaml",
        ]
    )
    assert cli.run(plan_args) == 0

    output = capsys.readouterr().out
    assert "Automatic operations: 0" in output
    assert output.count("Device transport used: No") == 2
    assert list((tmp_path / "runtime" / "bundles").glob("test-capture_*"))
    assert list((tmp_path / "runtime" / "plans").glob("plan_*.json"))
