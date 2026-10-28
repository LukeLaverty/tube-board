"""
Which lines a board shows, and in what order.
"""

import pytest

from tube_board.config import Config, Status
from tube_board.models import LineStatus
from tube_board.selection import (
    configured_lines,
    day_index,
    lines_for,
    parse_days,
    rows_for,
    selection_for,
    validate,
)

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


def status(line_id: str) -> LineStatus:
    return LineStatus(line_id, line_id.title(), "tube", 10, "Good Service")


class TestParseDays:
    def test_single_day(self):
        assert parse_days("mon") == {MON}

    def test_is_case_and_space_insensitive(self):
        assert parse_days("  MoN , tue ") == {MON, TUE}

    def test_full_names_abbreviate(self):
        assert parse_days("monday,thursday") == {MON, THU}

    def test_groups(self):
        assert parse_days("weekdays") == {MON, TUE, WED, THU, FRI}
        assert parse_days("weekend") == {SAT, SUN}
        assert parse_days("all") == set(range(7))

    def test_range(self):
        assert parse_days("mon-thu") == {MON, TUE, WED, THU}

    def test_backwards_range_wraps_through_the_weekend(self):
        assert parse_days("fri-mon") == {FRI, SAT, SUN, MON}

    def test_mixed_parts(self):
        assert parse_days("sat,sun") == {SAT, SUN}
        assert parse_days("weekend,mon") == {MON, SAT, SUN}

    def test_rejects_an_unknown_day(self):
        with pytest.raises(ValueError, match="Unknown day"):
            parse_days("caturday")

    def test_rejects_an_empty_spec(self):
        with pytest.raises(ValueError, match="No days given"):
            parse_days("  ")


def test_day_index_rejects_nonsense():
    assert day_index("Fri") == FRI
    with pytest.raises(ValueError):
        day_index("someday")


def test_validate_surfaces_a_typo_at_startup():
    with pytest.raises(ValueError):
        validate([{"days": "mon"}, {"days": "tuseday"}])


class TestLinesFor:
    SCHEDULE = [
        {"days": "mon-thu", "lines": ["metropolitan", "jubilee"]},
        {"days": "fri", "lines": ["elizabeth"]},
        {"days": "sat,sun", "lines": []},
    ]

    def test_first_matching_rule_wins(self):
        assert lines_for(self.SCHEDULE, ["district"], weekday=TUE) == [
            "metropolitan",
            "jubilee",
        ]
        assert lines_for(self.SCHEDULE, ["district"], weekday=FRI) == [
            "elizabeth"
        ]

    def test_an_empty_rule_means_every_line(self):
        assert lines_for(self.SCHEDULE, ["district"], weekday=SAT) == []

    def test_falls_back_when_no_rule_matches(self):
        assert lines_for([], ["district"], weekday=WED) == ["district"]

    def test_normalises_the_names_it_returns(self):
        schedule = [{"days": "all", "lines": [" Metropolitan ", "", "DLR"]}]
        assert lines_for(schedule, [], weekday=MON) == ["metropolitan", "dlr"]


class TestSelectionFor:
    CONFIG = Config(
        status=Status(
            lines=["circle", "district"],
            schedule=[{"days": "mon", "lines": ["jubilee"]}],
        )
    )

    def test_override_beats_everything(self):
        assert selection_for(self.CONFIG, ["dlr"], weekday=MON) == ["dlr"]

    def test_an_empty_override_is_still_an_override(self):
        assert selection_for(self.CONFIG, [], weekday=MON) == []

    def test_schedule_beats_the_configured_list(self):
        assert selection_for(self.CONFIG, None, weekday=MON) == ["jubilee"]

    def test_falls_back_to_the_configured_list(self):
        assert selection_for(self.CONFIG, None, weekday=TUE) == [
            "circle",
            "district",
        ]


def test_configured_lines_covers_every_day_once():
    config = Config(
        status=Status(
            lines=["circle", "district"],
            schedule=[
                {"days": "mon", "lines": ["jubilee", "circle"]},
                {"days": "fri", "lines": ["elizabeth"]},
            ],
        )
    )
    # Every line named anywhere, de-duplicated, so one fetch covers any day.
    assert configured_lines(config) == [
        "circle",
        "district",
        "jubilee",
        "elizabeth",
    ]


class TestRowsFor:
    def test_a_selection_sets_the_running_order(self):
        statuses = [status("circle"), status("dlr"), status("jubilee")]
        rows = rows_for(statuses, ["jubilee", "circle"])
        assert [r.line_id for r in rows] == ["jubilee", "circle"]

    def test_a_selection_drops_what_it_does_not_name(self):
        statuses = [status("circle"), status("dlr")]
        assert [r.line_id for r in rows_for(statuses, ["circle"])] == ["circle"]

    def test_no_selection_falls_back_to_tube_map_order(self):
        statuses = [status("victoria"), status("bakerloo"), status("central")]
        rows = rows_for(statuses, None)
        assert [r.line_id for r in rows] == ["bakerloo", "central", "victoria"]

    def test_unknown_lines_sort_last(self):
        statuses = [status("mystery"), status("bakerloo")]
        rows = rows_for(statuses, None)
        assert [r.line_id for r in rows] == ["bakerloo", "mystery"]
