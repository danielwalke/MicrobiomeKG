
from utils.extract_properties_markdown import extract_schema_with_samples_md
from utils.extract_properties_json import extract_json
from utils.identify_relevant_properties import extract_relevant_properties_as_json



if __name__ == "__main__":
    port = 8083
    user = "neo4j"
    password = "test"       
    schema_dict_md = extract_schema_with_samples_md(port, user, password, only_concept_nodes = False)
    json_schema = extract_json(port, user, password) ## TODO: Might cache if speed will increase in relevance 
    print(json_schema)
    extract_relevant_properties_as_json(schema_dict_md, json_schema)