Create .venv: python -m venv .venv
Activate .venv: source .venv/bin/activate
Install requirements: pip install -r requirements.txt
Curl required .jar files:
    curl -s https://api.github.com/repos/BioDWH2/BioDWH2/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO
    curl -s https://api.github.com/repos/BioDWH2/BioDWH2-Neo4j-Server/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | xargs curl -LO
Create a workspace: java -jar BioDWH2-v0.6.8.jar -c ~/git/MicrobiomeKG/s1_raw_graph/workspace
Select databases for your KG by running: python -m s1_raw_graph.identify_relevant_db
Update workspace config: python -m s1_raw_graph.update_workspace
Update workspace: java -jar BioDWH2-v0.6.8.jar -u ~/git/MicrobiomeKG/s1_raw_graph/workspace
Create raw database with raw knowledge graph: java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create ~/git/MicrobiomeKG/s1_raw_graph/workspace/
Start raw database: java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start ~/git/MicrobiomeKG/s1_raw_graph/workspace/
Extract concept nodes with MAPPED_TO connections and possible additional concept nodes: python -m s1_raw_graph.extract_possible_concepts
Identify relevant concepts: python -m s1_raw_graph.identify_relevant_concepts
Identify matching properties for node types: python -m s1_raw_graph.identify_matching_properties
Expand concept nodes: python -m s1_raw_graph.expand_concepts
Start metagraph container: docker compose -f s2_raw_metagraph/docker-compose.yml up -d
Extract Metagraph: python -m s2_raw_metagraph.extract_metagraph
Start filtered metagraph container: docker compose -f s3_filtered_raw_metagraph/docker-compose.yml up -d
Identify relevant properties: python -m s3_filtered_raw_metagraph.identify_properties_from_raw_graph
Filter metagraph and store in filtered metagraph docker container: python -m s3_filtered_raw_metagraph.filter_metagraph 
Clone raw graph: sudo -E python3 -m s4_filtered_rolledup_graph.clone_kg
Start docker container for cloned graph: docker compose -f s4_filtered_rolledup_graph/docker-compose.yml up -d
Filter and roll up knowledge graph: python -m s4_filtered_rolledup_graph.filter_knowledge_graph
Start docker container for filtered rolled up metagraph: docker compose -f s5_filtered_rolledup_metagraph/docker-compose.yml up -d
Extract metagraph from filtered rolled up graph: python -m s5_filtered_rolledup_metagraph.extract_metagraph
Start docker container for post filtered metagraph: docker compose -f s6_postfiltered_metagraph/docker-compose.yml up -d
Identify relevant properties from concept nodes after roll up: python -m s6_postfiltered_metagraph.identify_relevant_concept_properties
Postfilter metagraph: python -m s6_postfiltered_metagraph.filter_metagraph
Start docker container for post filtered graph: docker compose -f s7_postfiltered_graph/docker-compose.yml up -d
Clone knowledge graph again: sudo -E python3 -m s7_postfiltered_graph.clone_kg
Postfilter Knowledge graph and remove database nodes: python -m s7_postfiltered_graph.filter_knowledge_graph
Identify accessions: python -m s8_postfiltered_graph_with_accessions.identify_accession_keys
Add accessions: python -m s8_postfiltered_graph_with_accessions.add_accessions_in_graph
