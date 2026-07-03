import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.s3_propagation.delete_detach_db_nodes import delete_db_nodes
from src.s3_propagation.propagate_db_edges import propagate_edges
from src.s3_propagation.propagate_db_nodes import propagate_db_nodes
from src.utils.migrate_metagraph import migrate_metagraph
from src.utils.clone_kg import clone_kg

def propagation(target_driver):
    with target_driver.session() as session:
        propagate_db_nodes(session)
        propagate_edges(session)
        delete_db_nodes(session)

if __name__ == "__main__":
    load_dotenv()
    propagated_graph_uri = os.getenv("PROPAGATED_GRAPH_BOLT_URI")
    propagated_graph_user = os.getenv("PROPAGATED_GRAPH_USERNAME")
    propagated_graph_password = os.getenv("PROPAGATED_GRAPH_PASSWORD")
    propagated_graph_dir = os.getenv("PROPAGATED_GRAPH_DIR")
    filtered_graph_dir = os.getenv("NODE_FILTERED_GRAPH_DIR")

    propagated_metagraph_uri = os.getenv("PROPAGATED_METAGRAPH_BOLT_URI")
    propagated_metagraph_user = os.getenv("PROPAGATED_METAGRAPH_USERNAME")
    propagated_metagraph_password = os.getenv("PROPAGATED_METAGRAPH_PASSWORD")

    target_driver = GraphDatabase.driver(propagated_graph_uri, auth=(propagated_graph_user, propagated_graph_password))
    propagation(target_driver)

    metagraph_driver = GraphDatabase.driver(propagated_metagraph_uri, auth=(propagated_metagraph_user, propagated_metagraph_password))
    migrate_metagraph(target_driver, metagraph_driver)

    clone_kg(propagated_graph_dir, filtered_graph_dir)

