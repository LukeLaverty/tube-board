"""
Finding, reading and checking config files.
"""

import pytest

from tube_board import config as config_module
from tube_board.config import load_app_key, load_config


@pytest.fixture
def places(tmp_path, monkeypatch):
    """
    Point every place on the search path somewhere empty, so the checkout's
    own config.toml doesn't leak in.
    """
    cwd = tmp_path / "cwd"
    checkout = tmp_path / "checkout"
    xdg = tmp_path / "xdg"
    for directory in (cwd, checkout, xdg / "tube-board"):
        directory.mkdir(parents=True)
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(config_module, "CHECKOUT", checkout)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("TFL_APP_KEY", raising=False)
    return {"cwd": cwd, "checkout": checkout, "user": xdg / "tube-board"}


def write(directory, text, name="config.toml"):
    path = directory / name
    path.write_text(text)
    return path


class TestSearchPath:
    def test_runs_on_the_defaults_when_nothing_is_found(self, places):
        assert load_config().station.id == "940GZZLUKSX"

    def test_finds_the_checkout_from_another_directory(self, places):
        # As a cron job does, running from $HOME.
        write(places["checkout"], '[station]\nid = "checkout"\n')
        write(places["user"], '[station]\nid = "user"\n')
        assert load_config().station.id == "checkout"

    def test_the_working_directory_comes_first(self, places):
        write(places["cwd"], '[station]\nid = "cwd"\n')
        write(places["checkout"], '[station]\nid = "checkout"\n')
        assert load_config().station.id == "cwd"

    def test_falls_back_to_the_user_config(self, places):
        write(places["user"], '[station]\nid = "user"\n')
        assert load_config().station.id == "user"

    def test_reads_the_app_key_from_the_checkout(self, places):
        write(places["checkout"], "TFL_APP_KEY = abc123\n", name=".env")
        assert load_app_key() == "abc123"


class TestLoading:
    def test_a_missing_explicit_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nope.toml")

    def test_overlays_the_defaults(self, tmp_path):
        config = load_config(write(tmp_path, "[display]\nfps = 10\n"))
        assert config.display.fps == 10
        assert config.display.width == 256

    def test_whole_numbers_stand_in_for_floats(self, tmp_path):
        path = write(tmp_path, "[refresh]\nstatus_seconds = 30\n")
        refresh = load_config(path).refresh
        assert refresh.status_seconds == 30.0
        assert isinstance(refresh.status_seconds, float)

    def test_accepts_a_comma_separated_list(self, tmp_path):
        path = write(tmp_path, '[station]\nlines = "circle,,district"\n')
        assert load_config(path).station.lines == ["circle", "district"]

    def test_accepts_the_older_single_value_keys(self, tmp_path):
        path = write(tmp_path, '[station]\nline = "victoria"\n')
        assert load_config(path).station.lines == ["victoria"]

    def test_normalises_show_line_names(self, tmp_path):
        path = write(tmp_path, '[station]\nshow_line_names = " Never "\n')
        assert load_config(path).station.show_line_names == "never"


class TestErrors:
    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("[stations]\n", r"Unknown section \[stations\]"),
            ("[display]\nfsp = 30\n", r"\[display\] has no setting 'fsp'"),
            (
                '[display]\nfps = "thirty"\n',
                r"\[display\] fps should be a whole number",
            ),
            ("[display]\nwidth = 25.6\n", r"width should be a whole number"),
            ("[display]\nscale = true\n", r"scale should be a whole number"),
            (
                "[display]\nstatus_follows_schedule = 1\n",
                r"status_follows_schedule should be true or false",
            ),
            ("[station]\nlines = [1, 2]\n", r"lines should be a list"),
            ("[display]\nfps = 0\n", r"fps should be above 0"),
            ("[display]\nstatus_every = -1\n", r"status_every should be 0"),
            (
                '[station]\nshow_line_names = "sometimes"\n',
                r"show_line_names should be one of",
            ),
            (
                '[[status.schedule]]\ndays = "wkdays"\n',
                r"Unknown day 'wkdays'",
            ),
            ("station = 3\n", r"\[station\] should be a table"),
        ],
    )
    def test_reports_what_is_wrong_and_where(self, tmp_path, text, message):
        with pytest.raises(ValueError, match=message):
            load_config(write(tmp_path, text))
