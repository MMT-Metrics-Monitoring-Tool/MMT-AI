from datetime import date

import pytest

from database import sql_executor


ROWS = {
    "project_info.sql": [{"project_name": "Lunch Planner", "created_on": "2026-09-01", "finished_date": "2026-12-18",
                          "current_date": "2026-10-16"}],
    "project_members_working_hours.sql": [{"user_id": 22, "target_hours": 130, "current_hours": 120}],
    # Deliberately not in week order: the formatter must not depend on the order of different reports.
    "project_metrics.sql": [
        {"year": 2026, "week": 40, "meetings": "Team sync", "reported_hours": 96.0, "description": "reqNew", "value": 4},
        {"year": 2026, "week": 40, "meetings": "Team sync", "reported_hours": 96.0, "description": "overallStatus",
         "value": 2},
        {"year": 2026, "week": 41, "meetings": None, "reported_hours": None, "description": "reqNew", "value": 3},
    ],
    "project_risks.sql": [],
    "project_weekly_logged_hours.sql": [
        {"iso_year": 2026, "iso_week": 39, "hours": 30.0},
        {"iso_year": 2026, "iso_week": 41, "hours": 42.5},
        {"iso_year": 2026, "iso_week": 42, "hours": 10.0},
    ],
    "project_working_hours.sql": [{"target_hours": 650, "current_hours": 82.5}],
}


@pytest.fixture
def snapshot(monkeypatch):
    monkeypatch.setattr(sql_executor, "execute_sql_file", lambda path, project_id: ROWS[path.rsplit("/", 1)[-1]])
    return sql_executor.get_project_snapshot(1, today=date(2026, 10, 16))


def test_summary_has_this_and_last_weeks_logged_hours(snapshot):
    assert "Team hours this week, week 42/2026 (12.10.-18.10.): 10.0 h logged" in snapshot
    assert "Team hours last week, week 41/2026 (05.10.-11.10.): 42.5 h logged" in snapshot


def test_weekly_hours_list_every_week_including_empty_ones(snapshot):
    assert "week 39/2026 (21.09.-27.09.): 30.0 h" in snapshot
    assert "week 40/2026 (28.09.-04.10.): 0.0 h" in snapshot
    assert "week 42/2026 (12.10.-18.10.): 10.0 h" in snapshot


def test_weekly_hours_continue_to_the_current_week(monkeypatch):
    rows = dict(ROWS, **{"project_weekly_logged_hours.sql": [{"iso_year": 2026, "iso_week": 39, "hours": 5.0}]})
    monkeypatch.setattr(sql_executor, "execute_sql_file", lambda path, project_id: rows[path.rsplit("/", 1)[-1]])
    snapshot = sql_executor.get_project_snapshot(1, today=date(2026, 10, 16))
    assert "week 42/2026 (12.10.-18.10.): 0.0 h" in snapshot
    assert "Team hours this week, week 42/2026 (12.10.-18.10.): 0.0 h logged" in snapshot


def test_weekly_hours_across_the_year_boundary():
    rows = [{"iso_year": 2026, "iso_week": 53, "hours": 4.0}, {"iso_year": 2027, "iso_week": 1, "hours": 6.0}]
    text = sql_executor.format_weekly_hours(rows, today=date(2027, 1, 5))
    assert text.splitlines() == ["week 53/2026 (28.12.-03.01.): 4.0 h", "week 1/2027 (04.01.-10.01.): 6.0 h"]


def test_weekly_reports_have_one_header_each_with_reported_hours(snapshot):
    assert "Weekly report for week 40/2026, hours reported: 96.0, meetings: Team sync" in snapshot
    # A report without weekly hours says "none", so missing hours are not presented as zero.
    assert "Weekly report for week 41/2026, hours reported: none, meetings: none" in snapshot
    assert snapshot.count("Weekly report for week 40/2026") == 1
    assert "overallStatus: Minor Issues" in snapshot
    assert "Weekly reports: 2, latest week 41" in snapshot


def test_no_working_hours_recorded(monkeypatch):
    rows = dict(ROWS, **{"project_weekly_logged_hours.sql": []})
    monkeypatch.setattr(sql_executor, "execute_sql_file", lambda path, project_id: rows[path.rsplit("/", 1)[-1]])
    snapshot = sql_executor.get_project_snapshot(1, today=date(2026, 10, 16))
    assert "Team hours this week, week 42/2026 (12.10.-18.10.): 0.0 h logged" in snapshot
    assert "Logged working hours per week (from the team's working hour entries):\nNone recorded." in snapshot


def test_hours_keep_their_decimals():
    assert sql_executor.map_identifier_values("current_hours", 98.5) == "98.5"
    assert sql_executor.map_identifier_values("status", 2) == "Closed"
