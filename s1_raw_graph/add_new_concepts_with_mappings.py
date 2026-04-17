import json
import re
from neo4j import GraphDatabase

def setup_concept_indexes(driver):
    with driver.session() as session:
        result = session.run("CALL db.labels() YIELD label RETURN label")
        all_labels = [record["label"] for record in result]

    concept_labels = [label for label in all_labels if re.fullmatch(r'^[A-Z_]+$', label)]

    for label in concept_labels:
        print(f"Setting up index and backfilling data for label: {label}")
        
        with driver.session() as session:
            index_name = f"idx_{label.lower()}_search_names"
            
            session.run(
                f"CREATE INDEX {index_name} IF NOT EXISTS FOR (c:`{label}`) ON (c.search_names)"
            ).consume()
            
            session.run(
                f"""
                CALL {{
                    MATCH (c:`{label}`)
                    WHERE c.search_names IS NULL 
                      AND (c.names IS NOT NULL OR c.ids IS NOT NULL)
                    WITH c, [name IN coalesce(c.names, []) | toLower(name)] + [id IN coalesce(c.ids, []) | toLower(id)] AS combined
                    UNWIND CASE WHEN size(combined) = 0 THEN [null] ELSE combined END AS term
                    WITH c, collect(DISTINCT term) AS unique_search_names
                    SET c.search_names = [x IN unique_search_names WHERE x IS NOT NULL]
                }} IN TRANSACTIONS OF 5000 ROWS
                """
            ).consume()

driver = GraphDatabase.driver("bolt://localhost:8083", auth=None)

setup_concept_indexes(driver)

with open("config/s1_raw_graph/database_mapping_identifiers.json", "r") as f:
    concept_to_databases_with_mappings = json.load(f)

for concept, mapping_info in concept_to_databases_with_mappings.items():
    if concept in ["UNCLASSIFIED", "METADATA", "GENOMIC_REPEAT", "SEQUENCE_FEATURE"]:
        print(f"Skipping concept '{concept}' as it is not a valid concept for mapping in my honest opinion.")
        continue
    
    for db, db_config in mapping_info.items():
        print(f"Processing concept '{concept}' with database '{db}'...")
        with driver.session() as session:
            
            preprocessing = db_config.get("preprocessing")
            if preprocessing and "cypher_query" in preprocessing:
                cypher_query = preprocessing["cypher_query"]
                session.run(cypher_query).consume()
            
            final_prop_name = db_config['final_property_name']
            
            session.run(f"""
            MATCH (db_node:{db})
WHERE db_node.`{final_prop_name}` IS NOT NULL AND NOT EXISTS((db_node)-[:MAPPED_TO]->())
CALL {{
    WITH db_node
    CREATE (new_c:{concept} {{
        names: [db_node.`{final_prop_name}`], 
        ids: [], 
        search_names: [toLower(db_node.`{final_prop_name}`)], 
        search_ids: []
    }})
    CREATE (db_node)-[:MAPPED_TO]->(new_c)
}} IN TRANSACTIONS OF 5000 ROWS
            """).consume()

            # session.run(
            #     f"""
            #     MATCH (db_node:{db})
            #     WHERE db_node.`{final_prop_name}` IS NOT NULL AND NOT EXISTS((db_node)-[:MAPPED_TO]->())
            #     WITH db_node.`{final_prop_name}` AS raw_val, collect(db_node) AS db_nodes
            #     CALL {{
            #         WITH raw_val, db_nodes
            #         WITH raw_val, db_nodes, toLower(raw_val) AS search_val
            #         OPTIONAL MATCH (c:{concept})
            #         WHERE search_val IN c.search_names OR search_val IN c.search_ids
            #         WITH raw_val, search_val, db_nodes, collect(c) AS matched_concepts
            #         FOREACH (existing_c IN matched_concepts |
            #             SET existing_c.names = CASE WHEN NOT raw_val IN coalesce(existing_c.names, []) THEN coalesce(existing_c.names, []) + [raw_val] ELSE coalesce(existing_c.names, []) END,
            #                 existing_c.search_names = CASE WHEN NOT search_val IN coalesce(existing_c.search_names, []) THEN coalesce(existing_c.search_names, []) + [search_val] ELSE coalesce(existing_c.search_names, []) END
            #             FOREACH (node IN db_nodes | MERGE (node)-[:MAPPED_TO]->(existing_c))
            #         )
            #         FOREACH (_ IN CASE WHEN size(matched_concepts) = 0 THEN [1] ELSE [] END |
            #             CREATE (new_c:{concept} {{
            #                 names: [raw_val], 
            #                 ids: [], 
            #                 search_names: [search_val], 
            #                 search_ids: []
            #             }})
            #             FOREACH (node IN db_nodes | MERGE (node)-[:MAPPED_TO]->(new_c))
            #         )
            #     }} IN TRANSACTIONS OF 5000 ROWS
            #     """
            # ).consume()