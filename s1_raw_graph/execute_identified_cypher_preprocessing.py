import json
from neo4j import GraphDatabase

def execute_preprocessing_queries(json_filepath, uri="bolt://localhost:8083"):
    with open(json_filepath, "r") as file:
        data = json.load(file)

    driver = GraphDatabase.driver(uri, auth=None)

    try:
        with driver.session() as session:
            for label, properties in data.items():
                for prop, details in properties.items():
                    cypher_query = details.get("cypher")
                    if cypher_query:
                        print(f"Executing update for {label}.{prop}")
                        session.run(cypher_query)
        print("All queries executed successfully.")
    except Exception as e:
        print(f"Error executing queries: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    execute_preprocessing_queries("generated_queries.json")