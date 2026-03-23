import argparse
from neo4j import GraphDatabase
import json

def filter_properties(t_session, removed_properties):
    for label in removed_properties:
        removed_props = removed_properties[label]
        print(f"Removing properties from label '{label}': {removed_props}")
            
        props_to_remove = ", ".join([f"n.{prop}" for prop in removed_props])
        batch_query = f"""
        CALL apoc.periodic.iterate(
            "MATCH (n:{label}) RETURN n",
            "REMOVE {props_to_remove}",
            {{batchSize: 10000, parallel: false}}
        )
        """
        print(batch_query)
        t_session.run(batch_query).consume()


def remove_items(main_list, items_to_remove):
    remove_set = set(items_to_remove)
    return [item for item in main_list if item not in remove_set]

def run_migration(args):
    target_driver = GraphDatabase.driver(args.turi, auth=(args.tuser, args.tpass))
    with open("step_5_1_conceptfiltered_knowledge_graph/removed_concept_properties.json", "r") as f:
        removed_properties = json.load(f)

    with target_driver.session() as t_session:
        filter_properties(t_session, removed_properties)

        target_driver.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate and filter Neo4j graph")
    parser.add_argument("--turi", default="bolt://localhost:7691", help="Target Bolt URI")
    parser.add_argument("--tuser", default="neo4j", help="Target username")
    parser.add_argument("--tpass", default="", help="Target password")
    
    args = parser.parse_args()
    run_migration(args)