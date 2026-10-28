"""
Config errors the CLI catches before a board starts.
"""

import pytest

from tube_board import cli
from tube_board.cli import main


@pytest.fixture
def bad_schedule(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[[status.schedule]]\ndays = "wkdays"\nlines = ["victoria"]\n'
    )
    return path


@pytest.mark.parametrize("command", ["departures", "status"])
def test_a_bad_schedule_stops_either_board(bad_schedule, command):
    with pytest.raises(SystemExit, match="Config error: Unknown day 'wkdays'"):
        main(["--config", str(bad_schedule), "--mock"], command)


def test_a_missing_config_file_stops_the_board(tmp_path):
    missing = tmp_path / "nope.toml"
    with pytest.raises(SystemExit, match="Config error: No config file at"):
        main(["--config", str(missing), "--mock"], "status")


def test_an_unknown_setting_stops_the_board(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[display]\nfsp = 30\n")
    with pytest.raises(SystemExit, match="Config error: .*'fsp'"):
        main(["--config", str(path), "--mock"], "departures")


def test_the_old_departures_search_flag_still_searches(monkeypatch):
    searched = []
    monkeypatch.setattr(
        cli, "run_search", lambda query: searched.append(query) or 0
    )
    assert main(["--search", "canary wharf"], "departures") == 0
    assert searched == ["canary wharf"]
