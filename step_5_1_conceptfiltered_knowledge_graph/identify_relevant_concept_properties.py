from step_4_filtered_metaconcept_graph.identify_relevant_properties import extract_schema_with_samples, extract_relevant_properties_as_json

if __name__ == "__main__":
    port = 7691
    user = "neo4j"
    password = "test"       
    schema_dict, all_props = extract_schema_with_samples(port, user, password, only_concept_nodes = False)
    extract_relevant_properties_as_json(schema_dict, all_props, output_file="interesting_concept_properties.json")