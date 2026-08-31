from pathlib import Path

import pytest

from garmin_optimizer.cli import build_parser, run


def test_write_command_was_replaced_by_simulation() -> None:
    parser = build_parser()
    args = parser.parse_args(["simulate-write-test", "--confirm-simulation"])
    assert args.command == "simulate-write-test"
    with pytest.raises(SystemExit):
        parser.parse_args(["write-test"])
    assert parser.parse_args(["adb", "devices", "--show-serial"]).show_serial is True


def test_simulation_cli_uses_only_local_runtime(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("GARMIN_OPT_RUNTIME_DIR", str(tmp_path))
    args = build_parser().parse_args(["simulate-write-test", "--confirm-simulation"])
    assert run(args) == 0
    assert "Device transport used: No" in capsys.readouterr().out
    assert list((tmp_path / "journals").glob("simulation_*.json"))
