import os
import shutil
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.s3_propagation.delete_detach_db_nodes import delete_db_nodes
from src.s3_propagation.propagate_db_edges import propagate_edges
from src.s3_propagation.propagate_db_nodes import propagate_db_nodes
from src.utils.migrate_metagraph import migrate_metagraph

def propagation(target_driver):
    with target_driver.session() as session:
        propagate_db_nodes(session)
        propagate_edges(session)
        delete_db_nodes(session)

def clone_propagated_graph_data(propagated_graph_dir, filtered_graph_dir):
    """Copy PROPAGATED_GRAPH_DIR's neo4j data directory into FILTERED_GRAPH_DIR.

    Done as a plain in-process copy rather than via src.utils.clone_kg (which shells
    out to a throwaway `docker run` to perform the copy as uid 7474, matching a stock
    neo4j:latest container's default user) — s3_neo4j runs as this same host user
    instead, so no uid translation is needed, and a container running this step has no
    Docker socket to reach a docker run subprocess through anyway. Mirrors
    s2_mapping.main.clone_mapped_graph_data().
    """
    source_data_dir = os.path.join(propagated_graph_dir, "data")
    target_data_dir = os.path.join(filtered_graph_dir, "data")

    if os.path.exists(target_data_dir):
        shutil.rmtree(target_data_dir)
    shutil.copytree(source_data_dir, target_data_dir)

    for dir_name in ("data", "logs", "conf", "import"):
        os.makedirs(os.path.join(filtered_graph_dir, dir_name), exist_ok=True)

    for root, _, files in os.walk(target_data_dir):
        for filename in files:
            if filename in ("database_lock", "store_lock") or filename.endswith(".tmp") or ".tmp." in filename:
                os.remove(os.path.join(root, filename))

if __name__ == "__main__":
    load_dotenv()
    propagated_graph_uri = os.getenv("PROPAGATED_GRAPH_BOLT_URI")
    #propagated_graph_user = os.getenv("PROPAGATED_GRAPH_USERNAME")
    #propagated_graph_password = os.getenv("PROPAGATED_GRAPH_PASSWORD")
    propagated_graph_dir = os.getenv("PROPAGATED_GRAPH_DIR")
    node_filtered_graph_dir = os.getenv("NODE_FILTERED_GRAPH_DIR")

    #propagated_metagraph_uri = os.getenv("PROPAGATED_METAGRAPH_BOLT_URI")
    #propagated_metagraph_user = os.getenv("PROPAGATED_METAGRAPH_USERNAME")
    #propagated_metagraph_password = os.getenv("PROPAGATED_METAGRAPH_PASSWORD")

    target_driver = GraphDatabase.driver(propagated_graph_uri, auth=None) #auth=(propagated_graph_user, propagated_graph_password)
    propagation(target_driver)

    #metagraph_driver = GraphDatabase.driver(propagated_metagraph_uri, auth=(propagated_metagraph_user, propagated_metagraph_password))
    #migrate_metagraph(target_driver, metagraph_driver)

    print(f"Cloning Propagated Graph to Stage 4 NODE_FILTERED_GRAPH_DIR: {node_filtered_graph_dir}")
    clone_propagated_graph_data(propagated_graph_dir, node_filtered_graph_dir)

