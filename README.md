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

A `.env` file at the repo root is required by every stage (loaded via `python-dotenv` in each `main.py`, and via `source .env` in `run_pipeline.sh`). It defines, per stage, a `*_DIR` (clone target on disk), `*_DESKTOP_PORT`/`*_BOLT_PORT` (Neo4j HTTP/bolt ports for that stage's graph and its metagraph), and `*_USERNAME`/`*_PASSWORD`. `.env` is gitignored — see `refactor_prompt.txt` for the full variable list this pipeline was designed against, and adjust directory paths/ports for your own machine before creating your own copy.

---

## Running the Pipeline

`run_pipeline.sh` orchestrates stages 2 through 6 automatically: for each stage it starts that stage's `docker-compose.yml` (graph) and `meta-docker-compose.yml` (metagraph), waits for both to respond on their desktop (HTTP) port, then runs `PYTHONPATH=. python3 -m src.<stage>.main` from the repo root.

**Stage 1 is not run this way.** It has no `docker-compose.yml` of its own — the raw graph is a BioDWH2 Neo4j server started by hand (see Stage 1 below), not a container this repo manages. Only its metagraph has a compose file. Run Stage 1 manually before invoking `run_pipeline.sh` for the rest:
```bash
bash src/s1_raw_graph/load_ncbi_taxon_merged.sh          # fetch merged.dmp if not already present
cd src/s1_raw_graph && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s1_raw_graph.main
```

To run a single later stage the same way `run_pipeline.sh` would, without editing the script:
```bash
cd src/s2_mapping && docker compose up -d && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s2_mapping.main
```

---

## Universal Stage Pattern

Every stage after Stage 1 follows the same internal flow:
1. **Primary Operation** — the stage's specific graph transformation.
2. **Metagraph** — regenerate that stage's schema-only snapshot (`src/utils/migrate_metagraph.py`) from the graph, for inspection/documentation; nothing downstream reads it back.
3. **Clone** — copy the resulting graph (`src/utils/clone_kg.py`) into the next stage's directory.

The pipeline is linear: each stage's Clone output is the next stage's input.

---

## Stage 1: Raw Graph

* **Directory:** `src/s1_raw_graph`
* **Primary Operation:** Build/start the raw BioDWH2 graph, then standardize and repair NCBI taxonomy ids on it (see below).
* **Internal Flow:** Raw graph → NCBI Merged Taxonomies Resolution → Metagraph → Clone.
* **Routing:** Cloned output is passed to Stage 2 (`MAPPED_GRAPH_DIR`).

Create a workspace:
```bash
java -jar BioDWH2-v0.6.8.jar -c ~/git/MicrobiomeKG/src/s1_raw_graph/workspace
```

Update and (re)build the raw database:
```bash
java -jar BioDWH2-v0.6.8.jar -u ~/git/MicrobiomeKG/src/s1_raw_graph/workspace
java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create ~/git/MicrobiomeKG/src/s1_raw_graph/workspace/
```

Start the raw database (kept running for `main.py` to connect to):
```bash
java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start ~/git/MicrobiomeKG/src/s1_raw_graph/workspace/
```

Fetch `merged.dmp` (NCBI's taxid-merge table, needed by the resolution step below):
```bash
bash src/s1_raw_graph/load_ncbi_taxon_merged.sh
```

Run the stage (NCBI Merged Taxonomies Resolution, metagraph generation, clone to Stage 2):
```bash
cd src/s1_raw_graph && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s1_raw_graph.main
```

The NCBI resolution step standardizes each raw label's taxid property to `ncbi_taxid`, replaces any obsolete/merged id with its current one (per `merged.dmp`, keeping the original under `ncbi_taxid_old`), and links the node to the corresponding `TAXON` node via `MAPPED_TO`. See `AmbiguityNCBI.py` and `databases.txt` in this directory for the per-label configuration, and the design notes originally written up in `benjas_shit/NCBI_Merged_Taxonomies_Resolver/README.md` for the full rationale.

---

## Stage 2: Mapping

* **Directory:** `src/s2_mapping`
* **Primary Operation:** Entity resolution — link raw database-specific nodes (e.g. `UniProt_Protein`, `KEGG_...`) to unifying concept nodes (e.g. `PROTEIN`) via `MAPPED_TO` edges, filling in mappings the raw import didn't already provide.
* **Internal Flow:** Mapping → Metagraph → Clone.
* **Routing:** Cloned output is passed to Stage 3 (`PROPAGATED_GRAPH_DIR`).

```bash
cd src/s2_mapping && docker compose up -d && docker compose -f meta-docker-compose.yml up -d && cd ../..
PYTHONPATH=. python3 -m src.s2_mapping.main
```

---

## Stage 3: Propagation

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
