from step_4_filtered_metaconcept_graph.identify_relevant_properties import extract_schema_with_samples_md, extract_relevant_properties_as_json
from step_4_filtered_metaconcept_graph.extract_properties_json import extract_json

if __name__ == "__main__":
    port = 7691
    user = "neo4j"
    password = "test"       
    schema_dict_md = extract_schema_with_samples_md(port, user, password, only_concept_nodes = True)
    json_schema = extract_json(port, user, password) ## TODO: Might cache if speed will increase in relevance 
    extract_relevant_properties_as_json(schema_dict_md, json_schema, output_file="step_5_1_conceptfiltered_knowledge_graph/interesting_concept_properties.json", output_removed_file="step_5_1_conceptfiltered_knowledge_graph/removed_concept_properties.json")
    