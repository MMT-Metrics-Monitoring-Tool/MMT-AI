from typing import List, Dict

from database.database_connector import DatabaseConnector

import os


db = DatabaseConnector()

sql_path = "./database/sql/"
sql_files = os.listdir(sql_path)
sql_files = [f for f in sql_files if f.endswith(".sql")]

# Maps file names to a file-level description.
file_format_mapping = {
    "project_info.sql": "\nProject and general info:\n{}",
    "project_members_working_hours.sql": "\nTarget and current hours for project members:\n{}",
    "project_metrics.sql": "\nProject metrics for each week:\n{}",
    "project_risks.sql": "\nProject risk information:\n{}",
    "project_working_hours.sql": "\nTarget and current hours for the whole project:\n{}",
}

# Maps risk severity and probability IDs to textual descriptions.
risk_attribute_value_mapping = {
    0: "None",
    1: "Very Low",
    2: "Low",
    3: "Medium",
    4: "High",
    5: "Very High",
}

# Maps risk category IDs to textual descriptions.
risk_category_value_mapping = {
    0: "Uncategorized",
    1: "Political",
    2: "Economic",
    3: "Social",
    4: "Technological",
    5: "Environmental",
    6: "Legal",
}

# Maps risk impact IDs to textual representations.
risk_impact_value_mapping = {
    0: "Budget",
    1: "Time",
    2: "Scope",
    3: "Benefit",
}

# Maps risk status IDs to textual descriptions.
risk_status_value_mapping = {
    0: "Active",
    1: "Mitigated",
    2: "Closed",
}

# Maps the metric 'overallStatus' ID values to textual descriptions.
metrics_overall_status_mapping = {
    1: "All OK",
    2: "Minor Issues",
    3: "Severe Issues",
}


def execute_sql_file(file: str, project_id: int):
    """Opens an SQL file and executes the contained query in the connected MMT database.

    Args:
        file (str): The name of the SQL file to execute.
        project_id (int): ID of the project which to execute the query on.
    
    Returns:
        _type_: A data structure containing the query results.
    """
    f = open(file, "r")
    sql = f.read()
    return db.query(sql, (project_id,))

def map_identifier_values(key: str, value: int) -> str:
    """Maps database ID values into textual descriptions. Handles all possible mappings.

    Args:
        key (str): The name of the column whose value is being mapped.
        value (int): The integer ID value in the database.

    Returns:
        str: The textual description. If no mapping for key is found, returns the given value.
    """
    if key in ["severity", "probability"] and value in risk_attribute_value_mapping:
        value = risk_attribute_value_mapping[value]
    elif key == "category" and value in risk_category_value_mapping:
        value = risk_category_value_mapping[value]
    elif key == "impact" and value in risk_impact_value_mapping:
        value = risk_impact_value_mapping[value]
    elif key == "status" and value in risk_status_value_mapping:
        value = risk_status_value_mapping[value]
    return value

def map_metrics_values(key: str, value: int) -> str:
    """Maps metrics ID values into textual representations. Currently only the metric with description 'overallStatus' requires mapping.

    Args:
        key (str): The description of the metric.
        value (int): The integer ID value for the metrictype.

    Returns:
        str: The textual description. If no mapping for key is found, returns the given value formatted to zero decimal places.
    """
    if key == "overallStatus" and value in metrics_overall_status_mapping:
        value = metrics_overall_status_mapping[value]
    else:
        value = f"{value:.0f}"
    return value

def format_metrics_row(data: List[Dict]) -> str:
    """Formats results from the project metrics query.

    Args:
        data (List[Dict]): Results of the project metrics query.

    Returns:
        str: Formatted data.
    """
    formatted_data = []
    latest_week_num = 0
    for row in data:
        week_num = int(row.get("week"))
        if (week_num > latest_week_num): # Differing formatting for the first row of each week, containing week num, working hours, and meetings.
            formatted_data.append(f"Metrics for week {row.get("week")}, working hours: {row.get("duration"):.1f}, meetings: {row.get("meetings")}")
            latest_week_num = week_num
        mapped_value = map_metrics_values(row.get("description"), row.get("value"))
        formatted_data.append(f"{row.get("description")}: {mapped_value}")
    return "\n".join(formatted_data)

def format_generic_data(file: str, data: List[Dict]) -> str:
    """Formats results from an SQL query. Handles all nested formatting.

    Args:
        file (str): The name of the file. Used to define special formatting for specific queries.
        data (List[Dict]): Results of an SQL select query.

    Returns:
        str: Formatted data ready for writing out.
    """
    if "metrics" in file:
        return format_metrics_row(data)
    formatted_data = []
    for item in data:
        formatted_items = []
        for key, value in item.items():
            # Mapping fields with numerical identifier values into textual representations.
            value = map_identifier_values(key, value)
            formatted_items.append(f"{key}: {value}")
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
    return file_format_mapping.get(file, "Data:\n{}").format(format_generic_data(file, results))

def get_project_data(project_id: int) -> str:
    """Returns formatted project data from all defined queries.

    Args:
        project_id (int): The project on which to execute the queries on.

    Returns:
        str: Formatted project data.
    """
    all_query_results = [(f, result) for (f, result) in ((f, execute_sql_file(sql_path+f, project_id)) for f in sql_files) if result]
    formatted_data = [format_query_results(f, results) for (f, results) in all_query_results]
    return "\n".join(formatted_data)

