import json
import os
import pandas as pd
import numpy as np
from neo4j import GraphDatabase

SCHEMA_OVERLAPS_PATH = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/schema_overlaps.tsv")
POSSIBLE_CONCEPTS_PATH = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/possible_concept_labels.json")
RELEVANT_CONCEPTS_PATH = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/relevant_additional_concepts.json")

def main():
    driver = GraphDatabase.driver("bolt://localhost:8083", auth=("neo4j", "test"))

    schema_overlaps_df = pd.read_csv(SCHEMA_OVERLAPS_PATH, sep="\t").iloc[:1, :]
    source_labels = schema_overlaps_df["Source Label"]
    source_properties = schema_overlaps_df["Source Property"]
    target_labels = schema_overlaps_df["Target Label"]
    
    print(source_labels.values)
    print(target_labels.values)

    target_properties = schema_overlaps_df["Target Property"]

    with open(POSSIBLE_CONCEPTS_PATH, "r") as f:
        possible_concepts_dict = json.load(f)

    with open(RELEVANT_CONCEPTS_PATH, "r") as f:
        relevant_additional_concepts = json.load(f)
        
    for concept_label in relevant_additional_concepts:
        print(f"Processing relevant concept: {concept_label}")
        new_concept_label = concept_label.upper()
        
        for raw_kg_label in possible_concepts_dict.get(concept_label, []):
            with driver.session() as session:
                source_indices = np.where(source_labels.values == raw_kg_label)[0]
                source_index = source_indices[0] if source_indices.size > 0 else -1
                
                target_indices = np.where(target_labels.values == raw_kg_label)[0]
                target_index = target_indices[0] if target_indices.size > 0 else -1
                
                criteria = ""
                
                if source_index != -1:
                    criteria = f"__id: n.{source_properties.values[source_index]}"
                elif target_index != -1:
                    criteria = f"__id: n.{target_properties.values[target_index]}"
                    new_concept_label = source_labels.values[target_index].split("_")[-1].upper() 
                    print(raw_kg_label, new_concept_label)
                else:
                    criteria = f"__id: n.__id"

                queries = [
                    f"CREATE INDEX IF NOT EXISTS FOR (n:`{new_concept_label}`) ON (n.__id)",
                    f"CREATE INDEX IF NOT EXISTS FOR (n:`{raw_kg_label}`) ON (n.__id)"
                ]

                for q in queries:
                    session.run(q).consume()
                    
                session.run(
                    f"""
                    MATCH (n:`{raw_kg_label}`)
                    CALL {{
                        WITH n
                        MERGE (c:`{new_concept_label}` {{{criteria}}})
                        ON CREATE SET c.__mapped = true, c.ids = [], c.names = []
                        MERGE (n)-[:MAPPED_TO]->(c)
                    }} IN TRANSACTIONS OF 10000 ROWS
                    """
                ).consume()

if __name__ == "__main__":
    main()