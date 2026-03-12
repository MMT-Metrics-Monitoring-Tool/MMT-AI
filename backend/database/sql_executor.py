from typing import Any, List, Dict, TypedDict, cast

from database.database_connector import DatabaseConnector

import os


db = DatabaseConnector()

sql_path = "./database/sql/"
sql_files = os.listdir(sql_path)
sql_files = [f for f in sql_files if f.endswith(".sql")]

# Maps file names to a file-level description.
file_format_mapping: dict[str, str] = {
    "project_info.sql": "\nProject and general info:\n{}",
    "project_members_working_hours.sql": "\nTarget and current hours for project members:\n{}",
    "project_metrics.sql": "\nProject metrics for each week:\n{}",
    "project_risks.sql": "\nProject risk information:\n{}",
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
    week: int
    duration: float
    meetings: int
    description: str
    value: float | int | str


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

    result = db.query(sql, (project_id,))

    if result is None:
        return []

    if isinstance(result, list):
        return cast(list[dict[str, Any]], result)
    return []


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
    """Formats results from the project metrics query.

    Args:
        data (List[Dict]): Results of the project metrics query.

    Returns:
        str: Formatted data.
    """
    formatted_data: list[str] = []
    latest_week_num = 0

    for row in data:
        week_num = row["week"]

        if week_num is None: 
            continue

        # Differing formatting for the first row of each week, containing week num, working hours, and meetings.
        if (week_num > latest_week_num):
            duration = row.get("duration") or 0.0  # Default to 0.0 if NULL
            meetings = row.get("meetings") or 0    # Default to 0 if NULL
            formatted_data.append(
                f"Metrics for week {week_num}, "
                f"working hours: {duration:.1f}, "
                f"meetings: {meetings}"
            )
            latest_week_num = week_num

        mapped_value = map_metrics_values(row["description"], row["value"])
        formatted_data.append(f"{row['description']}: {mapped_value}")

    return "\n".join(formatted_data)


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


def get_project_data(project_id: int) -> str:
    """Returns formatted project data from all defined queries.

    Args:
        project_id (int): The project on which to execute the queries on.

    Returns:
        str: Formatted project data.
    """
    formatted_sections: list[str] = []

    for f in sql_files:
        results = execute_sql_file(os.path.join(sql_path, f), project_id)
        if results:
            formatted_sections.append(format_query_results(f, results))

    return "\n".join(formatted_sections)

