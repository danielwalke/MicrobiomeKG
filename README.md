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

TODO
python -m s3_filtered_raw_metagraph.identify_properties_from_raw_graph

-> müsste was in config landen
TODO check tomorrow if also for all concept nodes besides TERM the properties were filtered correctly