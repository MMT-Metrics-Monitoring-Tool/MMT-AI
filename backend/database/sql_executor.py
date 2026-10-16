from datetime import date, timedelta
from typing import Any, List, Dict, TypedDict, cast

from database import db

import os


sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql")
sql_files = sorted(os.listdir(sql_path))
sql_files = [f for f in sql_files if f.endswith(".sql")]

# Maps file names to a file-level description.
file_format_mapping: dict[str, str] = {
    "project_info.sql": "\nProject and general info:\n{}",
    "project_members_working_hours.sql": "\nTarget and current hours for project members:\n{}",
    "project_metrics.sql": "\nProject metrics for each week:\n{}",
    "project_risks.sql": "\nProject risk information:\n{}",
    "project_weekly_logged_hours.sql": "\nLogged working hours per week (from the team's working hour entries):\n{}",
    "project_working_hours.sql": "\nTarget and current hours for the whole project:\n{}",
}

# Maps risk severity and probability IDs to textual descriptions.
risk_attribute_value_mapping: dict[int, str] = {
    0: "None",
    1: "Very Low",
    2: "Low",
    3: "Medium",
    4: "High",
    5: "Very High",
}

# Maps risk category IDs to textual descriptions.
risk_category_value_mapping: dict[int, str] = {
    0: "Uncategorized",
    1: "Political",
    2: "Economic",
    3: "Social",
    4: "Technological",
    5: "Environmental",
    6: "Legal",
}

# Maps risk impact IDs to textual representations.
risk_impact_value_mapping: dict[int, str] = {
    0: "Budget",
    1: "Time",
    2: "Scope",
    3: "Benefit",
}

# Maps risk status IDs to textual descriptions.
risk_status_value_mapping: dict[int, str] = {
    0: "Active",
    1: "Mitigated",
    2: "Closed",
}

# Maps the metric 'overallStatus' ID values to textual descriptions.
metrics_overall_status_mapping: dict[int, str] = {
    1: "All OK",
    2: "Minor Issues",
    3: "Severe Issues",
}

# Generic row from db.query(..., dictionary=True)
class Row(TypedDict, total=False):
    pass

class MetricsRow(TypedDict):
    year: int
    week: int
    reported_hours: float | None
    meetings: str
    description: str
    value: float | int | str


WEEKLY_HOURS_FILE = "project_weekly_logged_hours.sql"


def execute_sql_file(file: str, project_id: int) -> list[dict[str, Any]]:
    """Opens an SQL file and executes the contained query in the connected MMT database.

    Args:
        file (str): The name of the SQL file to execute.
        project_id (int): ID of the project which to execute the query on.
    
    Returns:
        list[dict[str, Any]]: A data structure containing the query results.
    """
    with open(file, "r", encoding="utf-8") as f:
        sql = f.read()

    return db.fetch_all(sql, (project_id,))


def _to_int(value: Any) -> int | None:
    """
    Best-effort conversion to int for identifier values.
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None


def map_identifier_values(key: str, value: Any) -> str:
    """Maps database ID values into textual descriptions. Handles all possible mappings.

    Args:
        key (str): The name of the column whose value is being mapped.
        value (int): The integer ID value in the database.

    Returns:
        str: The textual description. If no mapping for key is found, returns the given value.
    """
    if key not in ("severity", "probability", "category", "impact", "status"):
        return "" if value is None else str(value)
    int_value = _to_int(value)
    if int_value is None:
        return "" if value is None else str(value)

    if key in ("severity", "probability") and int_value in risk_attribute_value_mapping:
        return risk_attribute_value_mapping[int_value]
    elif key == "category" and int_value in risk_category_value_mapping:
        return risk_category_value_mapping[int_value]
    elif key == "impact" and int_value in risk_impact_value_mapping:
        return risk_impact_value_mapping[int_value]
    elif key == "status" and int_value in risk_status_value_mapping:
        return risk_status_value_mapping[int_value]

    return str(int_value)


def map_metrics_values(key: str, value: float | int | str) -> str:
    """Maps metrics ID values into textual representations. Currently only the metric with description 'overallStatus' requires mapping.

    Args:
        key (str): The description of the metric.
        value (int): The integer ID value for the metrictype.

    Returns:
        str: The textual description. If no mapping for key is found, returns the given value formatted to zero decimal places.
    """
    if key == "overallStatus":
        int_value = _to_int(value)
        if int_value is not None and int_value in metrics_overall_status_mapping:
            return metrics_overall_status_mapping[int_value]

    # Format numerics to 0 decimals when possible.
    if isinstance(value, (int, float)):
        return f"{value:.0f}"
    # If string, attempt parsing.
    if isinstance(value, str):
        try:
            num = float(value)
            return f"{num:.0f}"
        except ValueError:
            return value


def format_metrics_row(data: List[MetricsRow]) -> str:
    """Formats results from the project metrics query, which are sorted by year and week.

    Args:
        data (List[Dict]): Results of the project metrics query.

    Returns:
        str: Formatted data.
    """
    formatted_data: list[str] = []
    current_report = None

    for row in data:
        if row["week"] is None:
            continue

        # Each weekly report starts with a header line containing the week, the hours reported in it and the meetings.
        # Reports without reported hours say "none" rather than 0, so missing data is not presented as zero hours.
        report = (row.get("year"), row["week"])
        if report != current_report:
            week = f"{row['week']}/{row['year']}" if row.get("year") else str(row["week"])
            reported = row.get("reported_hours")
            reported_text = f"{float(reported):.1f}" if reported is not None else "none"
            formatted_data.append(
                f"Weekly report for week {week}, hours reported: {reported_text}, meetings: {row.get('meetings') or 'none'}"
            )
            current_report = report

        mapped_value = map_metrics_values(row["description"], row["value"])
        formatted_data.append(f"{row['description']}: {mapped_value}")

    return "\n".join(formatted_data)


def _week_label(iso_year: int, iso_week: int) -> str:
    monday = date.fromisocalendar(iso_year, iso_week, 1)
    return f"week {iso_week}/{iso_year} ({monday:%d.%m.}-{monday + timedelta(days=6):%d.%m.})"


def format_weekly_hours(rows: list[dict[str, Any]], today: date) -> str:
    """Formats the logged hours per ISO week, from the first week with hours up to the current week.
    Weeks without any entries are listed with 0.0 h, so the model does not have to infer them.
    """
    hours = {(int(row["iso_year"]), int(row["iso_week"])): float(row["hours"] or 0) for row in rows}
    if not hours:
        return "None recorded."
    week = date.fromisocalendar(*min(hours), 1)
    last = max(date.fromisocalendar(*max(hours), 1), today - timedelta(days=today.weekday()))
    lines = []
    while week <= last:
        iso_year, iso_week, _ = week.isocalendar()
        lines.append(f"{_week_label(iso_year, iso_week)}: {hours.get((iso_year, iso_week), 0.0):.1f} h")
        week += timedelta(weeks=1)
    return "\n".join(lines)


def _week_summary(rows: list[dict[str, Any]], day: date, label: str) -> str:
    iso_year, iso_week, _ = day.isocalendar()
    logged = sum(float(row["hours"] or 0) for row in rows
                 if (int(row["iso_year"]), int(row["iso_week"])) == (iso_year, iso_week))
    return f"{label}, {_week_label(iso_year, iso_week)}: {logged:.1f} h logged"


def format_generic_data(file: str, data: list[dict[str, Any]]) -> str:
    """Formats results from an SQL query. Handles all nested formatting.

    Args:
        file (str): The name of the file. Used to define special formatting for specific queries.
        data (List[Dict]): Results of an SQL select query.

    Returns:
        str: Formatted data ready for writing out.
    """
    if "metrics" in file:
        return format_metrics_row(cast(list[MetricsRow], data))

    formatted_data: list[str] = []

    for item in data:
        formatted_items: list[str] = []
        for key, value in item.items():
            # Mapping fields with numerical identifier values into textual representations.
            formatted_items.append(f"{key}: {map_identifier_values(key, value)}")
        formatted_data.append(", ".join(formatted_items))

    return "\n".join(formatted_data)


def format_query_results(file: str, results: List[Dict]) -> str:
    """Formats the file-level description for a specific SQL query. Handles all nested formatting.

    Args:
        file (str): Name of the SQL file.
        results (List[Dict]): The result data from executing the query.

    Returns:
        str: The formatted query data.
    """
    template = file_format_mapping.get(file, "Data:\n{}")
    return template.format(format_generic_data(file, results))


def _hours_summary(row: dict[str, Any], label: str) -> str:
    target = float(row.get("target_hours") or 0)
    current = float(row.get("current_hours") or 0)
    if target:
        return f"{label}: {current:.1f} h logged of {target:.0f} h target ({current / target:.0%})"
    return f"{label}: {current:.1f} h logged, no target set"


def get_project_snapshot(project_id: int, today: date | None = None) -> str:
    """Returns the project data for the chatbot prompt: computed summary figures first, then all sections.
    Empty sections are stated explicitly, so the model does not have to infer that data is missing.

    Args:
        today: Overrides today's date for the weekly hours. Used by the tests.
    """
    today = today or date.today()
    results = {f: execute_sql_file(os.path.join(sql_path, f), project_id) for f in sql_files}

    summary: list[str] = []
    for row in results.get("project_working_hours.sql", []):
        if row.get("target_hours") is not None or row.get("current_hours") is not None:
            summary.append(_hours_summary(row, "Team hours"))
    weekly_hours = results.get(WEEKLY_HOURS_FILE, [])
    summary.append(_week_summary(weekly_hours, today, "Team hours this week"))
    summary.append(_week_summary(weekly_hours, today - timedelta(weeks=1), "Team hours last week"))
    for row in results.get("project_members_working_hours.sql", []):
        summary.append(_hours_summary(row, f"Member {row.get('user_id')} hours"))
    risks = results.get("project_risks.sql", [])
    statuses = [map_identifier_values("status", risk.get("status")) for risk in risks]
    summary.append(
        f"Risks: {len(risks)} recorded ({statuses.count('Active')} active, "
        f"{statuses.count('Mitigated')} mitigated, {statuses.count('Closed')} closed)"
    )
    reports = sorted({(row.get("year") or 0, row["week"]) for row in results.get("project_metrics.sql", [])
                      if row.get("week") is not None})
    summary.append(f"Weekly reports: {len(reports)}" + (f", latest week {reports[-1][1]}" if reports else ""))

    sections = ["Summary:\n" + "\n".join(summary)]
    for f in sql_files:
        template = file_format_mapping.get(f, "Data:\n{}")
        if f == WEEKLY_HOURS_FILE:
            sections.append(template.format(format_weekly_hours(results[f], today)))
        elif results[f]:
            sections.append(format_query_results(f, results[f]))
        else:
            sections.append(template.format("None recorded."))
    return "\n".join(sections)
