#!/bin/bash
set -e

if [ -z "$TMUX" ]; then
    tmux new-session -s microbiome_kg "bash $0; exec bash"
    exit 0
fi

#python -m venv .venv
#. .venv/bin/activate
#pip install -r requirements.txt

if [ ! -f "BioDWH2-v0.6.8.jar" ]; then
    curl -LO https://github.com/BioDWH2/BioDWH2/releases/download/v0.6.8/BioDWH2-v0.6.8.jar
fi

if [ ! -f "BioDWH2-Neo4j-Server-v1.3.2.jar" ]; then
    curl -LO https://github.com/BioDWH2/BioDWH2-Neo4j-Server/releases/download/v1.3.2/BioDWH2-Neo4j-Server-v1.3.2.jar
fi

if [ ! -d "$HOME/git/MicrobiomeKG/s1_raw_graph/workspace/sources" ] || [ -z "$(ls -A $HOME/git/MicrobiomeKG/s1_raw_graph/workspace/sources 2>/dev/null)" ]; then
    java -jar BioDWH2-v0.6.8.jar -c $HOME/git/MicrobiomeKG/s1_raw_graph/workspace
    python -m s1_raw_graph.identify_relevant_db
    python -m s1_raw_graph.update_workspace
    java -jar BioDWH2-v0.6.8.jar -u $HOME/git/MicrobiomeKG/s1_raw_graph/workspace
    java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create $HOME/git/MicrobiomeKG/s1_raw_graph/workspace/
fi

#java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start $HOME/git/MicrobiomeKG/s1_raw_graph/workspace/ &

#sleep 15

#python -m s1_raw_graph.extract_possible_concepts
#python -m s1_raw_graph.identify_relevant_concepts
#python -m s1_raw_graph.identify_matching_properties
#python -m s1_raw_graph.identify_cypher_preprocessing_steps
#python -m s1_raw_graph.execute_identified_cypher_preprocessing
#python -m s1_raw_graph.expand_concepts
#python -m s1_raw_graph.remove_dot_from_node_labels
#docker compose -f s2_raw_metagraph/docker-compose.yml up -d --wait
#python -m s2_raw_metagraph.extract_metagraph
#docker compose -f s3_filtered_raw_metagraph/docker-compose.yml up -d --wait
#python -m s3_filtered_raw_metagraph.identify_properties_from_raw_graph
#python -m s3_filtered_raw_metagraph.filter_metagraph
#sudo -E python3 -m s4_filtered_rolledup_graph.clone_kg
#docker compose -f s4_filtered_rolledup_graph/docker-compose.yml up -d --wait
#python -m s4_filtered_rolledup_graph.filter_knowledge_graph
#docker compose -f s5_filtered_rolledup_metagraph/docker-compose.yml up -d --wait
#python -m s5_filtered_rolledup_metagraph.extract_metagraph
#docker compose -f s6_postfiltered_metagraph/docker-compose.yml up -d --wait
#python -m s6_postfiltered_metagraph.identify_relevant_concept_properties
#python -m s6_postfiltered_metagraph.filter_metagraph
#sudo -E python3 -m s7_postfiltered_graph.clone_kg
# docker compose -f s7_postfiltered_graph/docker-compose.yml up -d --wait
python -m s7_postfiltered_graph.filter_knowledge_graph
python -m s8_postfiltered_graph_with_accessions.identify_accession_keys
python -m s8_postfiltered_graph_with_accessions.add_accessions_in_graph
python -m s9_kg_metrics.quant_compare
