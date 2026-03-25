
from utils.extract_properties_json import extract_json
from utils.extract_properties_markdown import extract_schema_with_samples_md
from utils.identify_relevant_properties import extract_relevant_properties_as_json
import os

if __name__ == "__main__":
    port = 7690
    user = "neo4j"
    password = "test"       
    schema_dict_md = extract_schema_with_samples_md(port, user, password, only_concept_nodes = True)
    json_schema = extract_json(port, user, password) 
    output_file_path = os.path.expanduser("~/git/MicrobiomeKG/config/s6_postfiltered_metagraph/interesting_concept_properties.json")
    output_removed_file_path = os.path.expanduser("~/git/MicrobiomeKG/config/s6_postfiltered_metagraph/removed_concept_properties.json")
    extract_relevant_properties_as_json(schema_dict_md, json_schema, output_file=output_file_path, output_removed_file=output_removed_file_path)
    