import json
import os

selected_db_file_path = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/selectedDatabases.json")
config_file_path = os.path.expanduser("~/git/MicrobiomeKG/s1_raw_graph/workspace/config.json")

with open(selected_db_file_path, "r") as f:
    selected_databases = json.load(f)

with open(config_file_path, "r") as f:
    workspace = json.load(f)

workspace["dataSourceIds"] = selected_databases["selected_databases"]

with open(config_file_path, "w") as f:
    json.dump(workspace, f, indent=4)