from neo4j import GraphDatabase

## TODO: Try
def add_missing_mapping_connections(driver):
    errors = []
    
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (db_node)-[:MAPPED_TO]->(concept_node)
                UNWIND labels(db_node) AS single_source_label
                RETURN DISTINCT single_source_label, labels(concept_node) AS target_labels
            """)
            
            for record in result:
                source_label = record["single_source_label"]
                target_labels = record["target_labels"]
                
                if not target_labels:
                    continue
                    
                target_label_str = ":" + ":".join(target_labels)
                
                try:
                    session.run(f"""
                        MATCH (other_db_node:{source_label})
                        WHERE NOT EXISTS {{ (other_db_node)-[:MAPPED_TO]->() }}
                        CALL (other_db_node) {{
                            MERGE (other_db_node)-[:MAPPED_TO]->(other_concept_node{target_label_str} {{__mapped: true, ids: [], names: []}})
                        }} IN TRANSACTIONS OF 10000 ROWS
                    """)
                except Exception as inner_e:
                    errors.append({
                        "source_label": source_label, 
                        "error": str(inner_e)
                    })
                    
    except Exception as e:
        errors.append({"general_error": str(e)})
        return {"status": "error", "errors": errors}
    
    final_status = "success" if len(errors) == 0 else "partial_success"
    return {"status": final_status, "errors": errors}

def main():
    driver = GraphDatabase.driver("bolt://localhost:8083", auth=None)
    try:
        result = add_missing_mapping_connections(driver)
        print(result)
    finally:
        driver.close()

if __name__ == "__main__":
    main()