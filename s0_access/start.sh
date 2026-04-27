#!/bin/bash
# set -e

# if [ -z "$TMUX" ]; then
#     tmux new-session -s microbiome_kg "bash $0; exec bash"
#     exit 0
# fi

# #python -m venv .venv
# #. .venv/bin/activate
# #pip install -r requirements.txt

# if [ ! -f "BioDWH2-v0.6.8.jar" ]; then
#     curl -LO https://github.com/BioDWH2/BioDWH2/releases/download/v0.6.8/BioDWH2-v0.6.8.jar
# fi

# if [ ! -f "BioDWH2-Neo4j-Server-v1.3.2.jar" ]; then
#     curl -LO https://github.com/BioDWH2/BioDWH2-Neo4j-Server/releases/download/v1.3.2/BioDWH2-Neo4j-Server-v1.3.2.jar
# fi

# if [ ! -d "$HOME/git/MicrobiomeKG/s1_raw_graph/workspace/sources" ] || [ -z "$(ls -A $HOME/git/MicrobiomeKG/s1_raw_graph/workspace/sources 2>/dev/null)" ]; then
#     java -jar BioDWH2-v0.6.8.jar -c ~/mnt/client_data/mikrobiome_kg/workspace
#     python -m s1_raw_graph.identify_relevant_db
#     python -m s1_raw_graph.update_workspace
#     java -jar BioDWH2-v0.6.8.jar -u ~/mnt/client_data/mikrobiome_kg/workspace
#     java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create ~/mnt/client_data/mikrobiome_kg/workspace
# fi

# java -jar BioDWH2-v0.6.8.jar -u ~/mnt/client_data/mikrobiome_kg/workspace
# java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create ~/mnt/client_data/mikrobiome_kg/workspace/

# java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start ~/mnt/client_data/mikrobiome_kg/workspace/ &

# sleep 15

# python -m s1_raw_graph.extract_possible_concepts
# python -m s1_raw_graph.identify_relevant_concepts
# python -m s1_raw_graph.identify_matching_properties
# python -m s1_raw_graph.identify_cypher_preprocessing_steps
# python -m s1_raw_graph.execute_identified_cypher_preprocessing


# python -m s1_raw_graph.add_missing_mapping_connections
# python -m s1_raw_graph.identify_concept_for_node_label
# python -m s1_raw_graph.add_new_concepts_with_mappings

# python -m s1_raw_graph.remove_dot_from_node_labels

echo "Starting Docker containers for s2_raw_metagraph..."
docker compose -f s2_raw_metagraph/docker-compose.yml up -d --wait
echo "Extracting metagraph for s2_raw_metagraph..."
python -m s2_raw_metagraph.extract_metagraph
echo "Starting Docker containers for s3_filtered_raw_metagraph..."
docker compose -f s3_filtered_raw_metagraph/docker-compose.yml up -d --wait
echo "Identifying properties for filtering in s3_filtered_raw_metagraph..."
python -m s3_filtered_raw_metagraph.identify_properties_from_raw_graph
echo "Filtering metagraph in s3_filtered_raw_metagraph..."
python -m s3_filtered_raw_metagraph.filter_metagraph



echo "Cloning raw KG"
sudo -E python3 -m s4_filtered_rolledup_graph.clone_kg
echo "Starting Docker containers for s4_filtered_rolledup_graph..." 
docker compose -f s4_filtered_rolledup_graph/docker-compose.yml up -d --wait
echo "Filtering knowledge graph in s4_filtered_rolledup_graph..."
python -m s4_filtered_rolledup_graph.filter_knowledge_graph
echo "Starting Docker containers for s5_filtered_rolledup_metagraph..."
docker compose -f s5_filtered_rolledup_metagraph/docker-compose.yml up -d --wait
echo "Extracting metagraph for s5_filtered_rolledup_metagraph..."
python -m s5_filtered_rolledup_metagraph.extract_metagraph
echo "Starting Docker containers for s6_postfiltered_metagraph..."
docker compose -f s6_postfiltered_metagraph/docker-compose.yml up -d --wait
echo "Identifying relevant concept properties in s6_postfiltered_metagraph..."
python -m s6_postfiltered_metagraph.identify_relevant_concept_properties
echo "Filtering metagraph in s6_postfiltered_metagraph..."
python -m s6_postfiltered_metagraph.filter_metagraph


echo "Cloning postfiltered graph..."
sudo -E python3 -m s7_postfiltered_graph.clone_kg
docker compose -f s7_postfiltered_graph/docker-compose.yml up -d --wait
echo "Filtering knowledge graph in s7_postfiltered_graph..."
python -m s7_postfiltered_graph.filter_knowledge_graph
echo "Identifying accession keys in s8_postfiltered_graph_with_accessions..."
python -m s8_postfiltered_graph_with_accessions.identify_accession_keys
echo "Adding accessions to graph in s8_postfiltered_graph_with_accessions..."
python -m s8_postfiltered_graph_with_accessions.add_accessions_in_graph
echo "Calculating knowledge graph metrics in s9_kg_metrics..."
python -m s9_kg_metrics.quant_compare


##TODO maybe reduce databases and filtering less selective -> Check connected compounds  