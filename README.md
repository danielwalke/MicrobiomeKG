# MicrobiomeKG Pipeline Documentation

## Table of Contents
* [Setup and Dependencies](#setup-and-dependencies)
* [Stage 1: Raw Graph Generation (`s1_raw_graph`)](#stage-1-raw-graph-generation)
* [Stage 2: Raw Metagraph Extraction (`s2_raw_metagraph`)](#stage-2-raw-metagraph-extraction)
* [Stage 3: Filtered Raw Metagraph (`s3_filtered_raw_metagraph`)](#stage-3-filtered-raw-metagraph)
* [Stage 4: Filtered Rolled-up Graph (`s4_filtered_rolledup_graph`)](#stage-4-filtered-rolled-up-graph)
* [Stage 5: Filtered Rolled-up Metagraph (`s5_filtered_rolledup_metagraph`)](#stage-5-filtered-rolled-up-metagraph)
* [Stage 6: Post-filtered Metagraph (`s6_postfiltered_metagraph`)](#stage-6-post-filtered-metagraph)
* [Stage 7: Post-filtered Graph (`s7_postfiltered_graph`)](#stage-7-post-filtered-graph)
* [Stage 8: Post-filtered Graph with Accessions (`s8_postfiltered_graph_with_accessions`)](#stage-8-post-filtered-graph-with-accessions)
* [Stage 9: Knowledge Graph Metrics (`s9_kg_metrics`)](#stage-9-knowledge-graph-metrics)

---

Just run bash s0_access/start.sh

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

Curl required .jar files:
```bash
curl -s https://api.github.com/repos/BioDWH2/BioDWH2/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO
curl -s https://api.github.com/repos/BioDWH2/BioDWH2-Neo4j-Server/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO
```

---

## Stage 1: Raw Graph Generation

Create a workspace:
```bash
java -jar BioDWH2-v0.6.8.jar -c ~/git/MicrobiomeKG/s1_raw_graph/workspace
```

Select databases for your KG by running:
```bash
python -m s1_raw_graph.identify_relevant_db
```

Update workspace config:
```bash
python -m s1_raw_graph.update_workspace
```

Update workspace:
```bash
java -jar BioDWH2-v0.6.8.jar -u ~/git/MicrobiomeKG/s1_raw_graph/workspace
```

Create raw database with raw knowledge graph:
```bash
java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create ~/git/MicrobiomeKG/s1_raw_graph/workspace/
```

Start raw database:
```bash
java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start ~/git/MicrobiomeKG/s1_raw_graph/workspace/
```

Extract concept nodes with MAPPED_TO connections and possible additional concept nodes:
```bash
python -m s1_raw_graph.extract_possible_concepts
```

Identify relevant concepts:
```bash
python -m s1_raw_graph.identify_relevant_concepts
```

Identify matching properties for node types:
```bash
python -m s1_raw_graph.identify_matching_properties
```

Expand concept nodes:
```bash
python -m s1_raw_graph.expand_concepts
```

---

## Stage 2: Raw Metagraph Extraction

Start metagraph container:
```bash
docker compose -f s2_raw_metagraph/docker-compose.yml up -d
```

Extract Metagraph:
```bash
python -m s2_raw_metagraph.extract_metagraph
```

---

## Stage 3: Filtered Raw Metagraph

Start filtered metagraph container:
```bash
docker compose -f s3_filtered_raw_metagraph/docker-compose.yml up -d
```

Identify relevant properties:
```bash
python -m s3_filtered_raw_metagraph.identify_properties_from_raw_graph
```

Filter metagraph and store in filtered metagraph docker container:
```bash
python -m s3_filtered_raw_metagraph.filter_metagraph 
```

---

## Stage 4: Filtered Rolled-up Graph

Clone raw graph:
```bash
sudo -E python3 -m s4_filtered_rolledup_graph.clone_kg
```

Start docker container for cloned graph:
```bash
docker compose -f s4_filtered_rolledup_graph/docker-compose.yml up -d
```

Filter and roll up knowledge graph:
```bash
python -m s4_filtered_rolledup_graph.filter_knowledge_graph
```

---

## Stage 5: Filtered Rolled-up Metagraph

Start docker container for filtered rolled up metagraph:
```bash
docker compose -f s5_filtered_rolledup_metagraph/docker-compose.yml up -d
```

Extract metagraph from filtered rolled up graph:
```bash
python -m s5_filtered_rolledup_metagraph.extract_metagraph
```

---

## Stage 6: Post-filtered Metagraph

Start docker container for post filtered metagraph:
```bash
docker compose -f s6_postfiltered_metagraph/docker-compose.yml up -d
```

Identify relevant properties from concept nodes after roll up:
```bash
python -m s6_postfiltered_metagraph.identify_relevant_concept_properties
```

Postfilter metagraph:
```bash
python -m s6_postfiltered_metagraph.filter_metagraph
```

---

## Stage 7: Post-filtered Graph

Start docker container for post filtered graph:
```bash
docker compose -f s7_postfiltered_graph/docker-compose.yml up -d
```

Clone knowledge graph again:
```bash
sudo -E python3 -m s7_postfiltered_graph.clone_kg
```

Postfilter Knowledge graph and remove database nodes:
```bash
python -m s7_postfiltered_graph.filter_knowledge_graph
```

---

## Stage 8: Post-filtered Graph with Accessions

Identify accessions:
```bash
python -m s8_postfiltered_graph_with_accessions.identify_accession_keys
```

Add accessions:
```bash
python -m s8_postfiltered_graph_with_accessions.add_accessions_in_graph
```

---

## Stage 9: Knowledge Graph Metrics

See statistics to compare against raw graph:
```bash
python -m s9_kg_metrics.quant_compare
```