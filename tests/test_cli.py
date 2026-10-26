"""
Config errors the CLI catches before a board starts.
"""

import pytest

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
