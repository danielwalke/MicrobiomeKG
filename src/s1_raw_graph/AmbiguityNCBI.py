
import os
import re

#structure to match the merged_id in the dmp file of NCBI
class NcbiMergedTaxonomy:
    def __init__(self, old_tax_id: int, new_tax_id: int):
        self.old_tax_id = old_tax_id
        self.new_tax_id = new_tax_id

    @classmethod
    def load_merged_dmp(cls, path: str) -> dict:
        """Parse NCBI's merged.dmp into {old_tax_id: new_tax_id}."""
        merged_map = {}
        with open(path, "r") as merged_dmp:
            for line in merged_dmp:
                fields = [field.strip() for field in line.split("|")]
                if len(fields) < 2 or not fields[0]:
                    continue
                record = cls(old_tax_id=int(fields[0]), new_tax_id=int(fields[1]))
                merged_map[record.old_tax_id] = record.new_tax_id
        return merged_map

#required in the main to resolve ambiguity of the NCBI taxonomies
DATABASES_FILE = os.path.join(os.path.dirname(__file__), "databases.txt")

STANDARD_PROPERTY = "ncbi_taxid"  # the property name we want to standardize to for all nodes with an NCBI taxid
OLD_ID_PROPERTY = "ncbi_taxid_old"
TAXON_LABEL = "TAXON"
NCBI_CURIE_PREFIX = "NCBITaxon:"
MAPPED_TO_REL = "MAPPED_TO"

TAXID_PATTERN = re.compile(r"(\d+)$")

DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")


def debug_print(message: str):
    if DEBUG:
        print(f"[debug] {message}")


#parse taxonomy merged.dmp
def load_databases(path: str = DATABASES_FILE) -> dict:
    """Read databases.txt into {label: {"property": ..., "is_list": ..., "curie_prefix": ...}}.

    Each line is `Label; property_name; example_value` (semicolon-delimited throughout —
    there is no literal tab before the example; an earlier version relied on
    `line.partition("\t")` to split off the example, which silently produced an empty
    example for every line since the file never actually contained a tab character,
    forcing `is_list` to always be False even for TAXON/UniProt_Organism's list-valued
    properties).
    `curie_prefix` is whatever non-digit prefix appears before the trailing number in
    the example (e.g. "NCBITaxon:" or "NCBI Taxonomy:"), or "" for a plain int/str
    example — used both to pick out matching entries from a mixed-authority list and
    to preserve that exact prefix when writing a corrected value back.
    """
    databases = {}
    with open(path, "r") as databases_file:
        for line in databases_file:
            line = line.strip()
            if not line:
                continue
            label, prop, example = [part.strip() for part in line.split(";", 2)]
            is_list = example.startswith("[")
            inner = example.strip("[]")
            curie_prefix = TAXID_PATTERN.sub("", inner)
            databases[label] = {"property": prop, "is_list": is_list, "curie_prefix": curie_prefix}
    return databases


def extract_taxid(raw_value) -> int:
    match = TAXID_PATTERN.search(str(raw_value))
    return int(match.group(1)) if match else None


def format_like(raw_value, new_taxid: int, curie_prefix: str = NCBI_CURIE_PREFIX):
    """Render new_taxid in the same shape (plain int, plain str, or <curie_prefix> CURIE) as raw_value."""
    if isinstance(raw_value, str) and curie_prefix and raw_value.startswith(curie_prefix):
        return f"{curie_prefix}{new_taxid}"
    if isinstance(raw_value, str):
        return str(new_taxid)
    return new_taxid


def run_query_to_standarize_ncbi_property_name(driver, label: str, old_property: str, is_list: bool, curie_prefix: str):
    with driver.session() as session:

        #is_list for TAXON concept node where:       TAXON; ids; [NCBITaxon:1785091]
        if is_list:
            session.run(
                f"""
                MATCH (n:`{label}`)
                WHERE n.`{old_property}` IS NOT NULL AND n.{STANDARD_PROPERTY} IS NULL
                WITH n, [x IN n.`{old_property}` WHERE x STARTS WITH $prefix] AS ncbi_ids
                WHERE size(ncbi_ids) > 0
                SET n.{STANDARD_PROPERTY} = ncbi_ids
                """,
                prefix=curie_prefix,
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

#mapps again dict of merged.dmpf generated with AmbiguityNCBI objects for every node
def run_query_to_generate_dict_with_ids_based_on_new_standarized_ids(driver, label: str, merged_map: dict) -> dict:
    """Build {ncbi_merged_id: [[node_id, ncbi_id], ...]} for nodes whose current taxid is a merged/obsolete one.

    Multiple nodes of the same label can share the same obsolete taxid (e.g. several
    GTDB_Genome assemblies of one species), so each merged id maps to a *list* of
    (node_id, ncbi_id) entries rather than a single one — otherwise all but the last
    node seen for a given merged id would be silently dropped.
    """
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
                #convert value to integer
                ncbi_merged_id = extract_taxid(ncbi_id)
                if ncbi_merged_id is not None and ncbi_merged_id in merged_map:
                    debug_print(f"[{label}] merged taxid match: node_id={node_id} old={ncbi_id!r} merged_id={ncbi_merged_id}")
                    merged_nodes.setdefault(ncbi_merged_id, []).append([node_id, ncbi_id])
    return merged_nodes


def update_ncbi_id_based_on_node_id(driver, label: str, is_list: bool, node_id, old_value, new_taxid: int, curie_prefix: str):
    new_value = format_like(old_value, new_taxid, curie_prefix)
    debug_print(f"[{label}] node_id={node_id}: {old_value!r} -> {new_value!r}")
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
            debug_print(f"[{label}] node_id={node_id}: linking MAPPED_TO -> TAXON with {new_curie!r}")
            session.run(
                f"""
                MATCH (n:`{label}`) WHERE id(n) = $node_id
                MATCH (t:{TAXON_LABEL}) WHERE $new_curie IN t.{STANDARD_PROPERTY}
                MERGE (n)-[:{MAPPED_TO_REL}]->(t)
                """,
                node_id=node_id, new_curie=new_curie,
            )