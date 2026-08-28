import os
import re

from dotenv import load_dotenv
from neo4j import GraphDatabase

from AmbiguityNCBI import NcbiMergedTaxonomy

DATABASES_FILE = os.path.join(os.path.dirname(__file__), "databases.txt")

STANDARD_PROPERTY = "ncbi_taxid"
OLD_ID_PROPERTY = "ncbi_taxid_old"
TAXON_LABEL = "TAXON"
NCBI_CURIE_PREFIX = "NCBITaxon:"
MAPPED_TO_REL = "MAPPED_TO"

TAXID_PATTERN = re.compile(r"(\d+)$")


def load_databases(path: str = DATABASES_FILE) -> dict:
    """Read databases.txt into {label: {"property": ..., "is_list": ...}}."""
    databases = {}
    with open(path, "r") as databases_file:
        for line in databases_file:
            line = line.strip()
            if not line:
                continue
            header, _, example = line.partition("\t")
            label, prop, _ = [part.strip() for part in header.split(";")]
            databases[label] = {"property": prop, "is_list": example.startswith("[")}
    return databases


def extract_taxid(raw_value) -> int:
    match = TAXID_PATTERN.search(str(raw_value))
    return int(match.group(1)) if match else None


def format_like(raw_value, new_taxid: int):
    """Render new_taxid in the same shape (plain int, plain str, or NCBITaxon: CURIE) as raw_value."""
    if isinstance(raw_value, str) and raw_value.startswith(NCBI_CURIE_PREFIX):
        return f"{NCBI_CURIE_PREFIX}{new_taxid}"
    if isinstance(raw_value, str):
        return str(new_taxid)
    return new_taxid


def run_query_to_standarize_ncbi_property_name(driver, label: str, old_property: str, is_list: bool):
    with driver.session() as session:
        if is_list:
            session.run(
                f"""
                MATCH (n:`{label}`)
                WHERE n.`{old_property}` IS NOT NULL AND n.{STANDARD_PROPERTY} IS NULL
                WITH n, [x IN n.`{old_property}` WHERE x STARTS WITH $prefix] AS ncbi_ids
                WHERE size(ncbi_ids) > 0
                SET n.{STANDARD_PROPERTY} = ncbi_ids
                """,
                prefix=NCBI_CURIE_PREFIX,
            )
        elif old_property != STANDARD_PROPERTY:
            session.run(
                f"""
                MATCH (n:`{label}`)
                WHERE n.`{old_property}` IS NOT NULL AND n.{STANDARD_PROPERTY} IS NULL
                SET n.{STANDARD_PROPERTY} = n.`{old_property}`
                REMOVE n.`{old_property}`
                """
            )


def run_query_to_generate_dict_with_ids_based_on_new_standarized_ids(driver, label: str, merged_map: dict) -> dict:
    """Build {ncbi_merged_id: [node_id, ncbi_id]} for nodes whose current taxid is a merged/obsolete one."""
    merged_nodes = {}
    with driver.session() as session:
        result = session.run(
            f"""
            MATCH (n:`{label}`)
            WHERE n.{STANDARD_PROPERTY} IS NOT NULL
            RETURN id(n) AS node_id, n.{STANDARD_PROPERTY} AS ncbi_taxid
            """
        )
        for record in result:
            node_id = record["node_id"]
            values = record["ncbi_taxid"]
            values = values if isinstance(values, list) else [values]
            for ncbi_id in values:
                ncbi_merged_id = extract_taxid(ncbi_id)
                if ncbi_merged_id is not None and ncbi_merged_id in merged_map:
                    merged_nodes[ncbi_merged_id] = [node_id, ncbi_id]
    return merged_nodes


def update_ncbi_id_based_on_node_id(driver, label: str, is_list: bool, node_id, old_value, new_taxid: int):
    new_value = format_like(old_value, new_taxid)
    with driver.session() as session:
        if is_list:
            session.run(
                f"""
                MATCH (n:`{label}`) WHERE id(n) = $node_id
                SET n.{OLD_ID_PROPERTY} = coalesce(n.{OLD_ID_PROPERTY}, []) + $old_value
                SET n.{STANDARD_PROPERTY} = [x IN n.{STANDARD_PROPERTY} WHERE x <> $old_value] + $new_value
                """,
                node_id=node_id, old_value=old_value, new_value=new_value,
            )
        else:
            session.run(
                f"""
                MATCH (n:`{label}`) WHERE id(n) = $node_id
                SET n.{OLD_ID_PROPERTY} = $old_value, n.{STANDARD_PROPERTY} = $new_value
                """,
                node_id=node_id, old_value=old_value, new_value=new_value,
            )

        if label != TAXON_LABEL:
            new_curie = f"{NCBI_CURIE_PREFIX}{new_taxid}"
            session.run(
                f"""
                MATCH (n:`{label}`) WHERE id(n) = $node_id
                MATCH (t:{TAXON_LABEL}) WHERE $new_curie IN t.{STANDARD_PROPERTY}
                MERGE (n)-[:{MAPPED_TO_REL}]->(t)
                """,
                node_id=node_id, new_curie=new_curie,
            )


def main():
    load_dotenv()
    uri = os.getenv("RAW_GRAPH_BOLT_URI")
    user = os.getenv("RAW_GRAPH_USERNAME")
    password = os.getenv("RAW_GRAPH_PASSWORD")
    merged_dmp_path = os.getenv("NCBI_MERGED_DMP_PATH", os.path.join(os.path.dirname(__file__), "merged.dmp"))

    databases = load_databases()
    merged_map = NcbiMergedTaxonomy.load_merged_dmp(merged_dmp_path)
    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        for label, config in databases.items():
            print(f"[{label}] standardizing {STANDARD_PROPERTY} property...")
            run_query_to_standarize_ncbi_property_name(driver, label, config["property"], config["is_list"])

            merged_nodes = run_query_to_generate_dict_with_ids_based_on_new_standarized_ids(driver, label, merged_map)
            print(f"[{label}] found {len(merged_nodes)} node(s) with a merged NCBI taxid")

            for ncbi_merged_id, (node_id, ncbi_id) in merged_nodes.items():
                new_taxid = merged_map[ncbi_merged_id]
                update_ncbi_id_based_on_node_id(driver, label, config["is_list"], node_id, ncbi_id, new_taxid)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
