import os
import shutil
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.utils.migrate_metagraph import migrate_metagraph
from src.s2_mapping.integrations.main import run_integrations
from src.s2_mapping.linking.main import main as run_linking


def clone_mapped_graph_data(mapped_graph_dir, propagated_graph_dir):
    """Copy MAPPED_GRAPH_DIR's neo4j data directory into PROPAGATED_GRAPH_DIR.

    Done as a plain in-process copy rather than via src.utils.clone_kg (which shells
    out to a throwaway `docker run` to perform the copy as uid 7474, matching a stock
    neo4j:latest container's default user) — s2_neo4j runs as this same host user
    instead, so no uid translation is needed, and a container running this step has no
    Docker socket to reach a docker run subprocess through anyway. Mirrors
    s1_raw_graph.main.clone_raw_graph_data(), except the source is already in the flat
    MAPPED_GRAPH_DIR/data layout (produced by that same function), not BioDWH2's nested
    neo4j/neo4j.db/data layout.
    """
    source_data_dir = os.path.join(mapped_graph_dir, "data")
    target_data_dir = os.path.join(propagated_graph_dir, "data")

    if os.path.exists(target_data_dir):
        shutil.rmtree(target_data_dir)
    shutil.copytree(source_data_dir, target_data_dir)

    for dir_name in ("data", "logs", "conf", "import"):
        os.makedirs(os.path.join(propagated_graph_dir, dir_name), exist_ok=True)

    for root, _, files in os.walk(target_data_dir):
        for filename in files:
            if filename in ("database_lock", "store_lock") or filename.endswith(".tmp") or ".tmp." in filename:
                os.remove(os.path.join(root, filename))


def main():
    load_dotenv()

    print("Running Primary Operation: Integrations")
    run_integrations()

    print("Running Primary Operation: Linking")
    run_linking()

    # TODO: Implement missing concept ID finder via LLM.
    print("TODO: Address missing concept mappings.")

    # Metagraph generation is parked until Stage 3's own neo4j service exists, same as
    # s1_raw_graph/main.py's own metagraph section — no MAPPED_METAGRAPH_* service is
    # wired up in pipeline-docker-compose.yml yet. The clone below is active, since
    # PROPAGATED_GRAPH_DIR is now defined in .env.
    # mapped_graph_uri = os.getenv("MAPPED_GRAPH_BOLT_URI", "bolt://localhost:8085")
    # mapped_graph_user = os.getenv("MAPPED_GRAPH_USERNAME", "neo4j")
    # mapped_graph_password = os.getenv("MAPPED_GRAPH_PASSWORD", "")
    mapped_graph_dir = os.getenv("MAPPED_GRAPH_DIR")
    propagated_graph_dir = os.getenv("PROPAGATED_GRAPH_DIR")
    # mapped_metagraph_uri = os.getenv("MAPPED_METAGRAPH_BOLT_URI", "bolt://localhost:8086")
    # print(f"Connecting to Mapped Graph at {mapped_graph_uri}...")
    # source_driver = GraphDatabase.driver(mapped_graph_uri, auth=(mapped_graph_user, mapped_graph_password))
    # print(f"Connecting to Mapped Metagraph at {mapped_metagraph_uri}...")
    # metagraph_driver = GraphDatabase.driver(mapped_metagraph_uri, auth=None)
    # print("Generating metagraph...")
    # migrate_metagraph(source_driver, metagraph_driver)
    print(f"Cloning Mapped Graph to Stage 3 PROPAGATED_GRAPH_DIR: {propagated_graph_dir}")
    clone_mapped_graph_data(mapped_graph_dir, propagated_graph_dir)

    print("Stage 2 complete.")

if __name__ == "__main__":
    main()
