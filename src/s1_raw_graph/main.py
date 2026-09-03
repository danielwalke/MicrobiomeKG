import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from src.utils.migrate_metagraph import migrate_metagraph
from src.utils.clone_kg import clone_kg

from src.s1_raw_graph.AmbiguityNCBI import (
    NcbiMergedTaxonomy,
    STANDARD_PROPERTY,
    load_databases,
    run_query_to_standarize_ncbi_property_name,
    run_query_to_generate_dict_with_ids_based_on_new_standarized_ids,
    update_ncbi_id_based_on_node_id,
)


def resolve_ncbi_merged_taxonomies(driver):
    merged_dmp_path = os.getenv("NCBI_MERGED_DMP_PATH", os.path.join(os.path.dirname(__file__), "merged.dmp"))

    databases = load_databases()
    merged_map = NcbiMergedTaxonomy.load_merged_dmp(merged_dmp_path)

    for label, config in databases.items():
        print(f"[{label}] standardizing {STANDARD_PROPERTY} property...")
        run_query_to_standarize_ncbi_property_name(driver, label, config["property"], config["is_list"], config["curie_prefix"])

        merged_nodes = run_query_to_generate_dict_with_ids_based_on_new_standarized_ids(driver, label, merged_map)
        total_matches = sum(len(entries) for entries in merged_nodes.values())
        print(f"[{label}] found {total_matches} node(s) with a merged NCBI taxid")

        for ncbi_merged_id, entries in merged_nodes.items():
            new_taxid = merged_map[ncbi_merged_id]
            for node_id, ncbi_id in entries:
                update_ncbi_id_based_on_node_id(driver, label, config["is_list"], node_id, ncbi_id, new_taxid, config["curie_prefix"])


def main():
    load_dotenv()

    # 1. Primary Operation: For s1, the raw graph is already started by Java application.
    raw_graph_uri = os.getenv("RAW_GRAPH_BOLT_URI")
    raw_graph_user = os.getenv("RAW_GRAPH_USERNAME")
    raw_graph_password = os.getenv("RAW_GRAPH_PASSWORD")
    raw_graph_dir = os.getenv("RAW_GRAPH_DIR")

    mapped_graph_dir = os.getenv("MAPPED_GRAPH_DIR")

    raw_metagraph_uri = os.getenv("RAW_METAGRAPH_BOLT_URI")
    raw_metagraph_user = os.getenv("RAW_METAGRAPH_USERNAME")
    raw_metagraph_password = os.getenv("RAW_METAGRAPH_PASSWORD")

    print(f"Connecting to Raw Graph at {raw_graph_uri}...")
    # notifications_min_severity="OFF" silences Neo4j's id() deprecation notice —
    # the NCBI resolution step below still relies on id(n) for node identity.
    source_driver = GraphDatabase.driver(
        raw_graph_uri, auth=(raw_graph_user, raw_graph_password), notifications_min_severity="OFF"
    )

    # 2. NCBI Merged Taxonomies Resolution — runs against the raw graph itself, before
    # the metagraph/clone below, so Stage 2 receives the corrected ncbi_taxid values
    # rather than a snapshot taken before the correction.
    print("Running Primary Operation: NCBI Merged Taxonomies Resolution")
    resolve_ncbi_merged_taxonomies(source_driver)

    print(f"Connecting to Raw Metagraph at {raw_metagraph_uri}...")
    # NOTE: Assuming the neo4j-raw-metagraph container is already running.
    # We use auth=None because docker-compose specifies NEO4J_AUTH=none.
    metagraph_driver = GraphDatabase.driver(raw_metagraph_uri, auth=None)

    # 3. Metagraph Generation
    print("Generating metagraph...")
    migrate_metagraph(source_driver, metagraph_driver)

    # 4. Clone
    print(f"Cloning Raw Graph to Stage 2 MAPPED_GRAPH_DIR: {mapped_graph_dir}")
    clone_kg(raw_graph_dir, mapped_graph_dir)
    print("Stage 1 complete.")

if __name__ == "__main__":
    main()
