import json
from neo4j import GraphDatabase
import pandas as pd
import numpy as np


## Assumption: The relevant target concept only has one identifier property that can be used across different matchings e.g., in Interpro_Classification we only use n.id for matchings
## -> I should check in schema_overlaps.tsv if this assumption holds for all relevant concepts. If not, I need to adjust the code to also include other properties in the criteria for creating the new concept node.
## This is not allways the case but for now lets assume it is because any list matching is far too expensive

driver = GraphDatabase.driver("bolt://localhost:8083", auth=("neo4j", "test"))

schema_overlaps_df = pd.read_csv("schema_overlaps.tsv", sep="\t").iloc[:1, :] ## Only for small graph, remove .iloc[:1, :] for full processing
source_labels = schema_overlaps_df["Source Label"]
source_properties = schema_overlaps_df["Source Property"]
target_labels = schema_overlaps_df["Target Label"]
print(source_labels.values)
print(target_labels.values)

target_properties = schema_overlaps_df["Target Property"]

with open("step_1_1_concept_expansion/possible_concept_labels.json", "r") as f:
    possible_concepts_dict = json.load(f)



with open("step_1_1_concept_expansion/relevant_additional_concepts.json", "r") as f:
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
                    f"CREATE INDEX IF NOT EXISTS FOR (n:{new_concept_label}) ON (n.__id)",
                    f"CREATE INDEX IF NOT EXISTS FOR (n:{raw_kg_label}) ON (n.__id)"
                ]

                for q in queries:
                    session.run(q).consume()
                session.run(
                f"""
                MATCH (n:{raw_kg_label})
                MERGE (c:{new_concept_label} {{{criteria}}})
                ON CREATE SET c.__mapped = true, c.ids = [], c.names = []
                MERGE (n)-[:MAPPED_TO]->(c)
                """
                ).consume()

