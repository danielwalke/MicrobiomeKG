from neo4j import GraphDatabase
import json

def get_unique_labels(session):
    query = "CALL db.labels() YIELD label RETURN label"
    result = session.run(query)
    return [record["label"] for record in result]

def filter_unmapped_database_labels(session, unique_labels):
    query = "MATCH (n) WHERE any(label IN labels(n) WHERE label IN $labels) AND NOT (n)-[:MAPPED_TO]->() RETURN DISTINCT labels(n) AS possible_concept_labels"
    result = session.run(query, labels=unique_labels)
    
    unique_flattened_labels = {label for record in result for label in record["possible_concept_labels"]}
    return list(unique_flattened_labels)

driver = GraphDatabase.driver("bolt://localhost:8083", auth=("neo4j", "test"))

with driver.session() as session:
    unique_labels = get_unique_labels(session)
    concept_node_json_file = "step_1_1_concept_expansion/concept_labels.json"
    possible_concept_node_json_file = "step_1_1_concept_expansion/possible_concept_labels.json"
    concept_labels = list(filter(lambda x: x.isupper(), unique_labels))
    database_labels = list(filter(lambda x: not x.isupper(), unique_labels))
    database_labels = filter_unmapped_database_labels(session, database_labels)
    
    possible_concept_dict = {}
    for db_label in database_labels:
        key = db_label.split("_")[-1]
        if key not in possible_concept_dict:
            possible_concept_dict[key] = []
        possible_concept_dict[key].append(db_label)
        
    with open(concept_node_json_file, "w", encoding="utf-8") as f:
        json.dump(concept_labels, f, indent=4)
    with open(possible_concept_node_json_file, "w", encoding="utf-8") as f:
        json.dump(possible_concept_dict, f, indent=4)