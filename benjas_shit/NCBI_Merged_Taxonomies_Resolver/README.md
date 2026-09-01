# NCBI Merged Taxonomies Resolver

## Purpose

Several raw-graph node labels store an NCBI taxonomy id under different property
names and formats. Over time NCBI "merges" some taxids into others (tracked in
their `merged.dmp` taxdump file); a node created before a merge still carries the
old, now-obsolete taxid. This pipeline:

1. Standardizes every db-specific taxid property to a single property name,
   `ncbi_taxid`.
2. Finds nodes whose `ncbi_taxid` is an old/merged id (per `merged.dmp`).
3. Replaces it with the current id (keeping the original value under
   `ncbi_taxid_old`), and links the node to the corresponding native `TAXON`
   node via a `MAPPED_TO` edge.

This runs against the **raw graph** (the graph populated by BioDWH2 in
`src/s1_raw_graph`), before `src/s2_mapping` does its own entity-resolution
pass — it is a data-correction step, not the general concept-node mapping
framework used elsewhere in `src/s2_mapping/integrations/`.

## Files

- `databases.txt` — the actual runtime config (not just documentation). One
  line per label: `Label; property_name;<TAB>example_value`. Parsed by
  `load_databases()` in `NCBI_Merged_Taxonomies_Ambiguity.py`, which infers
  `is_list` from whether the example value starts with `[`. To add/remove a
  database from the pipeline, edit this file — no code changes needed.
- `AmbiguityNCBI.py` — `NcbiMergedTaxonomy`, a small record class plus
  `load_merged_dmp(path)`, which parses NCBI's raw `merged.dmp` (`|`-delimited
  taxdump format) into `{old_tax_id: new_tax_id}`.
- `NCBI_Merged_Taxonomies_Ambiguity.py` — the pipeline itself (entry point:
  `main()`).

## Per-label config (parsed from `databases.txt`)

| Label              | Original property | Type            |
|--------------------|--------------------|-----------------|
| CAZY_CazyOrganism  | ncbi_taxid         | scalar int      |
| GTDB_Genome        | ncbi_taxid         | scalar int      |
| INSTANCE_TAXON     | taxonomy_id        | scalar int      |
| KEGG_Organism      | ncbi_taxid         | scalar `NCBITaxon:<id>` string |
| TAXON              | ids                | list of mixed-authority CURIEs (native NCBI taxonomy node) |
| TrEMBL_Organism    | taxonomy_id        | scalar int      |

`TAXON` is the raw NCBI taxonomy node itself; its `ids` list can hold CURIEs
from multiple identifier authorities, not just NCBI, so it is handled
differently (see below) and is never rewritten/removed.

## Pipeline logic

For each label (in the order it appears in `databases.txt`):

1. **`run_query_to_standarize_ncbi_property_name`**
   - Scalar labels: idempotently renames `<old_property>` → `ncbi_taxid`
     (`SET ... REMOVE ...`, guarded by `WHERE old prop IS NOT NULL AND
     ncbi_taxid IS NULL`, so re-running the pipeline is safe). If the label's
     property is already named `ncbi_taxid`, this is a no-op.
   - `TAXON`: does **not** touch `ids`. Instead it extracts every entry
     starting with `NCBITaxon:` out of `ids` into a new `ncbi_taxid` **list**
     property (always a list, even for a single match, so downstream matching
     can uniformly use `IN`).

2. **`run_query_to_generate_dict_with_ids_based_on_new_standarized_ids`**
   - Reads back `(id(n), n.ncbi_taxid)` for every node in the label.
   - For each value (unwrapping list-valued `ncbi_taxid` on `TAXON`), strips
     any `NCBITaxon:` prefix and checks the resulting int against the
     `merged.dmp`-derived map.
   - Only nodes whose id **is** a merged/obsolete id go into the result dict,
     keyed by that merged id so the later id-replacement lookup is O(1):
     `{ncbi_merged_id: [[node_id, ncbi_id], ...]}` — a *list* of entries per
     merged id, since multiple nodes of the same label can share one obsolete
     taxid (e.g. several `GTDB_Genome` assemblies of the same species). An
     earlier version keyed this as a single `[node_id, ncbi_id]` value, which
     silently dropped every node but the last one seen for a given merged id.
     `ncbi_id` is the original raw property value (kept to preserve its exact
     formatting — plain int, plain str, or CURIE — when writing the fix).

3. **`update_ncbi_id_based_on_node_id`**, called once per entry in that dict:
   - Computes the replacement value in the *same shape* as the original
     (`format_like`): CURIE stays a CURIE, plain int stays a plain int, etc.
   - Scalar labels: `ncbi_taxid_old` is set to the single old value;
     `ncbi_taxid` is overwritten with the new value.
   - `TAXON`: `ncbi_taxid_old` accumulates old values in a list (a `TAXON`
     node's `ncbi_taxid` can have more than one entry over time); the fixed
     CURIE replaces the stale one inside the `ncbi_taxid` list.
   - For every label **except `TAXON`**: also `MERGE`s a `MAPPED_TO` edge from
     the node to the `TAXON` node whose `ncbi_taxid` list now contains the
     corrected CURIE. `TAXON` nodes never get a self-edge.

## Design decisions confirmed with the user (2026-08-28)

- Property rename is idempotent (safe to re-run).
- `TAXON.ids` entries are matched by the literal substring pattern
  `"NCBITaxon"`, since the list may contain non-NCBI identifiers too.
- CURIE prefixes are stripped only for comparison against `merged.dmp`; the
  original format is always preserved when writing values back.
- The obsolete id is preserved under `ncbi_taxid_old`.
- `merged.dmp` is consumed in its raw NCBI taxdump format (`|`-delimited),
  not a pre-cleaned CSV.
- New edges to the resolved `TAXON` node use relationship type `MAPPED_TO`
  (matching the convention used by `src/s2_mapping/integrations/integrator.py`
  elsewhere in the repo).
- `TAXON` nodes are excluded from edge-building (id correction only) — a
  `TAXON` node should not get a `MAPPED_TO` edge to itself/another `TAXON`.

## Configuration (env vars, via `.env` / `python-dotenv`)

- `RAW_GRAPH_BOLT_URI`, `RAW_GRAPH_USERNAME`, `RAW_GRAPH_PASSWORD` — same
  names as `src/s1_raw_graph/main.py`, since these raw labels live in that
  graph. No default is hard-coded (matching that stage's convention) — these
  **must** be set in `.env` before running.
- `NCBI_MERGED_DMP_PATH` — path to NCBI's `merged.dmp`. Defaults to
  `merged.dmp` next to this script if unset.

## Not yet done / for the next agent

- **`merged.dmp` has not been supplied yet** — the user will provide it
  (deliberately not auto-downloaded from NCBI's public FTP). Nothing has been
  run against a live database. The code has only been syntax-checked and the
  pure-Python helpers (`load_databases`, `extract_taxid`, `format_like`)
  unit-exercised manually; the Cypher-touching functions are untested
  end-to-end. Once `merged.dmp` exists, smoke-test by pointing
  `NCBI_MERGED_DMP_PATH` at it, running against a raw graph that actually has
  a handful of known-merged taxids, and checking: (1) the property rename
  happened on all six labels, (2) `ncbi_taxid_old` got set only on the nodes
  that had a merged id, (3) `MAPPED_TO` edges appeared from the corrected
  non-`TAXON` nodes to the right `TAXON` node.
- `docker-compose.yml` and `Dockerfile` in this folder are intentionally left
  as empty skeletons — the user will fill in the actual Neo4j service config
  (image, ports, volumes, `NEO4J_AUTH`, etc.) themselves. Do not flesh these
  out unless explicitly asked again.
- **Pipeline wiring (undecided, needs a decision + implementation):** this
  script is standalone today — it is not invoked by `run_pipeline.sh` or any
  stage's `main()`. It must run against the **raw graph**, before
  `src/s2_mapping`'s entity resolution (since that stage relies on
  `ncbi_taxid` already being standardized/correct to cluster nodes). Concrete
  options to weigh with the user before implementing:
  - Add an explicit call at the end of `src/s1_raw_graph/main.py` (or a new
    step invoked right after it, sharing `RAW_GRAPH_BOLT_URI`/etc.), since
    `run_pipeline.sh` currently starts at `s2_mapping` and s1 is run
    separately/manually (via the BioDWH2 Java tool). This keeps "raw graph
    correction" logically inside stage 1.
  - Or introduce it as a distinct step invoked between s1 and s2 in
    `run_pipeline.sh`, so it's explicit in the pipeline's stage list rather
    than folded into an existing stage's `main()`.
  - Either way: move this folder's script out of `benjas_shit/` into `src/`
    (e.g. `src/s1_raw_graph/` or a new `src/s1b_ncbi_taxonomy_resolver/`)
    following the repo's existing per-stage `.env`-driven `main()` pattern,
    and decide where `merged.dmp` should live on disk (an env var like
    `RAW_GRAPH_DIR`-relative path, matching how other stages reference their
    data directories).
- **No-match logging (needs implementation):** in
  `update_ncbi_id_based_on_node_id`, the `MERGE (t:TAXON) WHERE $new_curie IN
  t.ncbi_taxid` query currently matches zero rows and silently creates no edge
  when no `TAXON` node carries the resolved id. Before wiring this into the
  pipeline, add visibility into that case, e.g.:
  ```python
  result = session.run(
      f"""
      MATCH (n:`{label}`) WHERE id(n) = $node_id
      OPTIONAL MATCH (t:{TAXON_LABEL}) WHERE $new_curie IN t.{STANDARD_PROPERTY}
      FOREACH (_ IN CASE WHEN t IS NOT NULL THEN [1] ELSE [] END |
          MERGE (n)-[:{MAPPED_TO_REL}]->(t)
      )
      RETURN t IS NOT NULL AS matched
      """,
      node_id=node_id, new_curie=new_curie,
  ).single()
  if not result["matched"]:
      print(f"[{label}] WARNING: no TAXON node found for {new_curie} (node id(n)={node_id})")
  ```
  This also makes the edge-creation atomic with the match check in one query
  instead of two. Consider accumulating these warnings and printing a summary
  count per label at the end of `main()` rather than one line per node, if
  the number of misses could be large.
