from datetime import date

from chatbot.deadlines import extract_dated_items, format_upcoming


SCHEDULE = """# Schedule

## Course schedule Autumn 2026

- Moodle submissions deadlines:
  - Sprint retrospective memo will be delivered to Moodle before each sprint review meeting. Deadlines (Sprint 0 review DL = 25.09.2026, Sprint 1 review DL = 09.10.2026, Sprint 2 review DL = 23.10.2026).
  - Project plan 18.09.2026.
  - Test plan 30.10.2026.
- Peer feedback (link can be found from the Moodle).
  - Project status and peer feedback 1 latest by 09.10.2026.
  - ~~Project status and peer feedback 4 latest by 19.12.2026.~~

| Meeting | Participants | Review deadline |
| --- | --- | --- |
| Sprint 3 (19.10.-30.10.) review, weeks 43-44 | Team+coach | 06.11.2026 |
"""


def test_list_items_are_labelled_with_their_parent():
    labels = {(item.date, item.label) for item in extract_dated_items(SCHEDULE)}
    assert (date(2026, 10, 30), "Moodle submissions deadlines: Test plan") in labels
    assert (date(2026, 10, 9), "Peer feedback: Project status and peer feedback 1") in labels


def test_lines_with_many_dates_are_split_per_date():
    labels = {(item.date, item.label) for item in extract_dated_items(SCHEDULE)}
    assert (date(2026, 9, 25), "Moodle submissions deadlines: Sprint 0 review DL") in labels
    assert (date(2026, 10, 23), "Moodle submissions deadlines: Sprint 2 review DL") in labels


def test_table_cells_use_row_and_column_labels():
    labels = {(item.date, item.label) for item in extract_dated_items(SCHEDULE)}
    assert (date(2026, 11, 6), "Sprint 3 (19.10.-30.10.) review, weeks 43-44 - Review deadline") in labels


def test_struck_through_items_are_ignored():
    assert all(item.date != date(2026, 12, 19) for item in extract_dated_items(SCHEDULE))


def test_upcoming_is_sorted_from_today_with_relative_times():
    upcoming = format_upcoming(extract_dated_items(SCHEDULE), today=date(2026, 10, 8)).splitlines()
    assert upcoming[0].startswith("- Fri 09.10.2026 (tomorrow):")
    assert not any("18.09.2026" in line for line in upcoming)
    assert upcoming[-1].startswith("- Fri 06.11.2026 (in 4 weeks):")


def test_upcoming_without_dates():
    assert format_upcoming([], today=date(2026, 10, 8)) == "No upcoming dates found in the course material."
