# MicrobiomeKG Pipeline Documentation

## Table of Contents
* [Setup and Dependencies](#setup-and-dependencies)
* [Running the Pipeline](#running-the-pipeline)
* [Universal Stage Pattern](#universal-stage-pattern)
* [Stage 1: Raw Graph (`s1_raw_graph`)](#stage-1-raw-graph)
* [Stage 2: Mapping (`s2_mapping`)](#stage-2-mapping)
* [Stage 3: Propagation (`s3_propagation`)](#stage-3-propagation)
* [Stage 4: Node Filtering (`s4_node_filtering`)](#stage-4-node-filtering)
* [Stage 5: Edge Filtering (`s5_edge_filtering`)](#stage-5-edge-filtering)
* [Stage 6: Accessions (`s6_accessions`)](#stage-6-accessions)
* [Reference: Raw Import Notes](#reference-raw-import-notes)

---

## Setup and Dependencies

Create .venv:
```bash
python -m venv .venv
```

Activate .venv:
```bash
source .venv/bin/activate
```

Install requirements:
```bash
pip install -r requirements.txt
```

Curl required .jar files (used to build/run the raw BioDWH2 graph in Stage 1):
```bash
curl -s https://api.github.com/repos/BioDWH2/BioDWH2/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO
curl -s https://api.github.com/repos/BioDWH2/BioDWH2-Neo4j-Server/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO
```

A `.env` file at the repo root is required to run the pipeline (loaded via `env_file: .env` per-service in `pipeline-docker-compose.yml` for stages 1-2, via `python-dotenv` in each `main.py`, and via `source .env` in `run_pipeline.sh` for the not-yet-migrated stages 3-6). It defines, per stage, a `*_DIR` (clone target on disk), `*_DESKTOP_PORT`/`*_BOLT_PORT` (Neo4j HTTP/bolt ports for that stage's graph), `*_USERNAME`/`*_PASSWORD`, plus `PROJEKT_DIR` (repo root, used as the Docker build context) and `GRAPH_CONTAINER_BOLT_PORT` (Neo4j's fixed internal bolt port, `7687` — shared across every stage, distinct from each stage's host-side `*_BOLT_PORT`). `.env` is gitignored — see `info/State_Of_Art.md` for the current full variable list and per-variable notes, and adjust directory paths/ports for your own machine before creating your own copy. `merged.dmp` (NCBI's taxid-merge table, needed by Stage 1) is already committed at `src/s1_raw_graph/merged.dmp`; `bash src/s1_raw_graph/load_ncbi_taxon_merged.sh` only needs to be re-run to refresh it.

Docker + Docker Compose are required to run Stages 1-2 (see below); the `.venv`/`pip install` steps above are for editing/running Python directly, e.g. for the not-yet-migrated stages 3-6.

---

## Running the Pipeline

**Stages 1 and 2 are run together as one Docker Compose stack**, `pipeline-docker-compose.yml` at the repo root. It defines two services per stage — a stock `neo4j:latest` serving that stage's input graph, and a custom-built "runner" that does the stage's actual work against it — sequenced via Compose `depends_on` conditions instead of a shell script polling ports. Before running it, the Stage 1 prerequisites below (BioDWH2 workspace) still need to be done by hand once; after that, one command runs both stages end to end:
```bash
docker compose -f pipeline-docker-compose.yml up --build
```
`--build` is only needed the first time or after changing a `Dockerfile`/a file it `COPY`s — Docker's build cache makes it a fast no-op otherwise, so it's harmless to always include. Add `-d` to run detached, then `docker compose -f pipeline-docker-compose.yml logs -f` to follow logs — but note that only the `up` process itself drives `depends_on` sequencing; switching to `logs -f` (or losing the `up` process any other way, e.g. Ctrl+C) does not stop already-started containers, but does stop later stages from being started automatically once their dependency finishes. Tear down with `docker compose -f pipeline-docker-compose.yml down`.

**Stages 3-6 are not migrated to this model yet.** `run_pipeline.sh` still orchestrates them the old way: for each stage it starts that stage's `docker-compose.yml` (graph) and `meta-docker-compose.yml` (metagraph), waits for both to respond on their desktop (HTTP) port, then runs `PYTHONPATH=. python3 -m src.<stage>.main` from the repo root. To run a single later stage the same way, without editing the script:
```bash
cd src/s3_propagation && docker compose up -d && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s3_propagation.main
```

---

## Universal Stage Pattern

Every stage's runner follows the same internal flow:
1. **Primary Operation** — the stage's specific graph transformation.
2. **Metagraph** — regenerate that stage's schema-only snapshot (`src/utils/migrate_metagraph.py`) from the graph, for inspection/documentation; nothing downstream reads it back. Currently parked (commented out) for both migrated stages (1-2) — no `*_METAGRAPH_*` Compose service exists yet.
3. **Clone** — copy the resulting graph into the next stage's directory. For the migrated stages (1-2), this is a plain in-process `shutil.copytree` (`clone_raw_graph_data()` / `clone_mapped_graph_data()` in each stage's `main.py`), not `src.utils.clone_kg.clone_kg(...)` — that helper shells out to a throwaway `docker run` container to do the copy, which needs the `docker` CLI and a bind-mounted `/var/run/docker.sock` inside the runner, neither of which the containerized runners have. Stages 3-6 still use `clone_kg(...)` as originally written, since they're not containerized yet.

The pipeline is linear: each stage's Clone output is the next stage's input.

---

## Stage 1: Raw Graph

* **Directory:** `src/s1_raw_graph`
* **Primary Operation:** Standardize and repair NCBI taxonomy ids on the already-built raw BioDWH2 graph (see below).
* **Internal Flow:** NCBI Merged Taxonomies Resolution → Clone (Metagraph parked).
* **Routing:** Cloned output is passed to Stage 2 (`MAPPED_GRAPH_DIR`).
* **Compose services:** `s1_neo4j` (stock `neo4j:latest`, serves the BioDWH2 workspace's already-built Neo4j store directly — no BioDWH2 jar/build involved at this point) + `s1_NCBI_taxonomy_service` (builds `src/s1_raw_graph/ncbi-taxonomy.Dockerfile`, runs `src/s1_raw_graph/main.py`).

The BioDWH2 workspace itself still has to be built/updated by hand — `pipeline-docker-compose.yml` only *serves* an already-built workspace, it doesn't build one (`s0_BioDWH2_service`, meant to automate this, is still an unimplemented placeholder):

Create a workspace:
```bash
java -jar BioDWH2-v0.6.8.jar -c ~/git/MicrobiomeKG/src/s1_raw_graph/workspace
```

Update and (re)build the raw database:
```bash
java -jar BioDWH2-v0.6.8.jar -u ~/git/MicrobiomeKG/src/s1_raw_graph/workspace
java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create ~/git/MicrobiomeKG/src/s1_raw_graph/workspace/
```

Point `RAW_GRAPH_DIR` in `.env` at that workspace directory (it must contain a built
`neo4j/neo4j.db/{data,logs}`), then run the stage as part of the pipeline command
above (or scope it to just Stage 1 with `docker compose -f pipeline-docker-compose.yml
up --build s1_NCBI_taxonomy_service`, which pulls in `s1_neo4j` automatically as its
dependency). Unlike the old flow, BioDWH2's own Neo4j-Server jar does **not** need to
be started separately (`--start`) — `s1_neo4j` serves the store directly.

The NCBI resolution step standardizes each raw label's taxid property to `ncbi_taxid`, replaces any obsolete/merged id with its current one (per `merged.dmp`, keeping the original under `ncbi_taxid_old`), and links the node to the corresponding `TAXON` node via `MAPPED_TO`. See `AmbiguityNCBI.py` and `databases.txt` in this directory for the per-label configuration, and the design notes originally written up in `NCBI_Taxon_Ambiguity_Und_Enzyme_Pipeline/NCBI_Merged_Taxonomies_Resolver/README.md` for the full rationale.

---

## Stage 2: Mapping

* **Directory:** `src/s2_mapping`
* **Primary Operation:** Entity resolution — link raw database-specific nodes (e.g. `UniProt_Protein`, `KEGG_...`) to unifying concept nodes (e.g. `PROTEIN`, `ENZYME`, `TERM`) via `MAPPED_TO` edges, filling in mappings the raw import didn't already provide; then a linking pass adding typed edges between existing nodes (e.g. `REFERENCES`, `HAS_ONTOLOGY`).
* **Internal Flow:** Integrations → Linking → Clone (Metagraph parked).
* **Routing:** Cloned output is passed to Stage 3 (`PROPAGATED_GRAPH_DIR`).
* **Compose services:** `s2_neo4j` (stock `neo4j:latest`, serves Stage 1's cloned output) + `s2_mapping` (builds `src/s2_mapping/s2_mapping.Dockerfile`, runs `src/s2_mapping/main.py`).

Runs automatically as part of the pipeline command above once Stage 1 finishes, or on
its own with `docker compose -f pipeline-docker-compose.yml up --build s2_mapping`
(pulls in `s2_neo4j` as its dependency, which in turn waits for
`s1_NCBI_taxonomy_service` to have completed and populated `MAPPED_GRAPH_DIR`).

Each concept type (`PROTEIN_DOMAIN`, `TERM`, `DISEASE`, `TISSUE`, `PTM`, `MODULE`,
`REACTION`, `PATHWAY`, `ENZYME`, ...) is a `BaseMergedEntity` subclass in
`integrations/` declaring which source labels/properties feed it
(`__source_mappings__`) — see `integrations/base_merged.py`,
`integrations/entity_resolver.py`, and `integrations/integrator.py` for the generic
resolve/integrate machinery every blueprint runs through, and e.g.
`integrations/enzyme.py`/`integrations/term.py` for example blueprints.

---

## Stage 3: Propagation

> Stages 3-6 are not yet migrated to the `pipeline-docker-compose.yml` model used by
> Stages 1-2 — they still use the older per-stage `docker-compose.yml` +
> `run_pipeline.sh` pattern below, unverified as part of this round's changes.

* **Directory:** `src/s3_propagation`
* **Primary Operation:** Propagate database-node properties/edges onto their unifying concept nodes, then remove the now-redundant database nodes.
* **Internal Flow:** Propagation & DB node removal → Metagraph → Clone.
* **Routing:** Cloned output is passed to Stage 4 (`NODE_FILTERED_GRAPH_DIR`).

```bash
cd src/s3_propagation && docker compose up -d && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s3_propagation.main
```

---

## Stage 4: Node Filtering

* **Directory:** `src/s4_node_filtering`
* **Primary Operation:** LLM-driven filtering of node properties, keeping only what's relevant to a metaproteomics/metagenomics microbiome KG.
* **Internal Flow:** Node property filtering → Metagraph → Clone.
* **Routing:** Cloned output is passed to Stage 5 (`EDGE_FILTERED_GRAPH_DIR`).

```bash
cd src/s4_node_filtering && docker compose up -d && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s4_node_filtering.main
```

---

## Stage 5: Edge Filtering

* **Directory:** `src/s5_edge_filtering`
* **Primary Operation:** Combine duplicate edges of the same type (merging/deduplicating their properties), then LLM-filter redundant edge properties.
* **Internal Flow:** Edge combination & filtering → Metagraph → Clone.
* **Routing:** Cloned output is passed to Stage 6 (`FINAL_GRAPH_DIR`).

```bash
cd src/s5_edge_filtering && docker compose up -d && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s5_edge_filtering.main
```

---

## Stage 6: Accessions

* **Directory:** `src/s6_accessions`
* **Primary Operation:** LLM-driven identification of primary/secondary accession keys per node label, appended so every node type has a unified accession-based identity.
* **Internal Flow:** Accession appendage → Metagraph → Clone (final output).

```bash
cd src/s6_accessions && docker compose up -d && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s6_accessions.main
```

---

## Reference: Raw Import Notes

Notes from the original raw-graph mapping analysis (labels that came out of the BioDWH2 import without a `MAPPED_TO` connection, and what was decided about each). Kept for historical context; the specific module names mentioned below predate the current `src/` stage layout.

Delete merged nodes:
```cypher
:auto MATCH (n:MergedNode)
CALL {
  WITH n
  DETACH DELETE n
} IN TRANSACTIONS OF 100000 ROWS;
```

Unmapped nodes in biodwh2:
```cypher
MATCH (n) WHERE NOT EXISTS {(n)-[:MAPPED_TO]-()} RETURN DISTINCT labels(n)
```
```
["GeneOntology_Subset"] -> Considered irrelevant since it is only connected to GeneOntology_Header (metadata)
["metadata"] -> considered irrelvant (metadata, can be stoed in sepaarted file next to dump)
["InterPro_DBInfo"] -> considered irrelvant (metadata, can be stoed in sepaarted file next to dump)
["RNAInter_RNA"] -> Partially unmapped by Marcel? (handled by s1_raw_graph.add_missing_mapping_connections)
["DiseaseOntology_Subset"] -> Considered irrelevant since it is only connected to DiseaseOntology_Header (metadata)
["GeneOntology_Typedef"] -> irrelevant since only cnnected itself
["InterPro_ActiveSite"]
["HPRD_Interactor"]
["HPRD_PostTranslationalModification"] -> Mapped to custom concept PTM
["InterPro_Family"]
["DiseaseOntology_SynonymType"] -> irrelevant since its a single node only connected to DiseaseOntology_Header (metadata)
["ENZYME_Enzyme"] -> Property rolluop in s4
["DISEASES_Gene"] -> Partially unmapped by Marcel? (handled by s1_raw_graph.add_missing_mapping_connections)
["HPRD_Motif"]
["DiseaseOntology_Header"] -> irrelevant single node
["InterPro_Classification"]-> Mapped to custom concept TERM
["InterPro_Repeat"]
["UniProt_Reference"] -> handled by edge_roll_up in s4 (shotcut between citation and protein)
["InterPro_BindingSite"]
["DISEASES_Disease"] -> Mapped to custom concept DISEASE (partially unmapped by Marcel)
["GeneOntology_Header"] -> irrelevant single node
["HPRD_Domain"] -> Mapped to custom concept PROTEIN_DOMAIN
["DGIdb_Drug"]-> Partially unmapped by Marcel? (handled by s1_raw_graph.add_missing_mapping_connections)
["DGIdb_Category"] -> Mapped to custom concept TERM
["InterPro_ConservedSite"]
["DiseaseOntology_Typedef"] -> irrelevant (only two nodes without connections)
["RNAInter_HistoneModification"] -> considered irrelvant for now
["GeneOntology_Idspace"] -> considered irrelvant for now
["HPRD_Disease"]-> Mapped to custom concept DISEASE
["HPRD_ProteinComplex"] -> considered irrelvant for now
["InterPro_HomologousSuperfamily"] -> considered irrelvant for now
["InterPro_PTM"] -> Do not know how to map to PRM concept?
["GeneOntology_Term"] -> Mapped to custom concept TERM
["UniProt_Feature"] -> considered irrelvant for now
["GeneOntology_SynonymType"] -> irrelevant single node
["HPRD_Tissue"] -> Mapped to custom concept TISSUE
["DiseaseOntology_Term"] -> Mapped to custom concept TERM
```
