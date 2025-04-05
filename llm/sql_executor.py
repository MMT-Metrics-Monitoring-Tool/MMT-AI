from typing import List, Dict

from database_connector import DatabaseConnector

import os


db = DatabaseConnector()

sql_path = "./sql/"
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


def execute_sql_file(file: str, project_id: int):
    f = open(file, "r")
    sql = f.read()
    return db.query(sql, (project_id,))

def map_identifier_values(key, value):
    if key in ["severity", "probability"] and value in risk_attribute_value_mapping:
        value = risk_attribute_value_mapping[value]
    elif key == "category" and value in risk_category_value_mapping:
        value = risk_category_value_mapping[value]
    elif key == "impact" and value in risk_impact_value_mapping:
        value = risk_impact_value_mapping[value]
    elif key == "status" and value in risk_status_value_mapping:
        value = risk_status_value_mapping[value]
    return value

def format_generic_data(data: List[Dict]) -> str:
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
    return file_format_mapping.get(file, "Data:\n{}").format(format_generic_data(results))

def get_project_data(project_id: int) -> str:
    all_query_results = [(f, result) for (f, result) in ((f, execute_sql_file(sql_path+f, project_id)) for f in sql_files) if result]
    formatted_data = [format_query_results(f, results) for (f, results) in all_query_results]
    return "\n".join(formatted_data)

