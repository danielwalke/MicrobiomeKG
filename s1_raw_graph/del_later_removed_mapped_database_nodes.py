import json
from neo4j import GraphDatabase

## I can delete this sinc ein the future i will add these missing MAPPED_TO Conncetions in a previous scrupt
def get_node_database_labels_without_mappings(session):
    query = "MATCH (n) WHERE NOT (n)-[:MAPPED_TO]->() AND NOT all(l IN labels(n) WHERE l =~ '^[A-Z]+$') UNWIND labels(n) AS label RETURN DISTINCT label"
    result = session.run(query)
    return [record["label"] for record in result]


def filter_db_to_concept_mapping(db_to_concept, valid_labels):
    filtered_mapping = {}
    for db_label, mapping_info in db_to_concept.items():
        if db_label in valid_labels:
            filtered_mapping[db_label] = mapping_info
        else:
            print(f"Excluding '{db_label}' from mapping - not found in database labels without mappings.")
    return filtered_mapping

driver = GraphDatabase.driver("bolt://localhost:8083", auth=("neo4j", "password"))
with driver.session() as session:
     database_labels = get_node_database_labels_without_mappings(session)


with open("config/s1_raw_graph/database_to_concept_mapping.json", "r") as f:
    db_to_concept = json.load(f)

filtered_mapping = filter_db_to_concept_mapping(db_to_concept, database_labels)
with open("config/s1_raw_graph/database_to_concept_mapping.json", "w") as f:
    json.dump(filtered_mapping, f, indent=4)