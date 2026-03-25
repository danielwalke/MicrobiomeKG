#!/bin/bash
set -e

prompt_for_review() {
    eval "$1"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$2"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        open "$2"
    else
        explorer.exe "$2"
    fi

    echo "Please review the choices in the opened file browser for: $2"
    read -p "Press Enter once you have edited the JSON files to continue..."
}

python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

if [ ! -f "BioDWH2-v0.6.8.jar" ]; then
    curl -LO https://github.com/BioDWH2/BioDWH2/releases/download/v0.6.8/BioDWH2-v0.6.8.jar
fi

if [ ! -f "BioDWH2-Neo4j-Server-v1.3.2.jar" ]; then
    curl -LO https://github.com/BioDWH2/BioDWH2-Neo4j-Server/releases/download/v1.3.2/BioDWH2-Neo4j-Server-v1.3.2.jar
fi

java -jar BioDWH2-v0.6.8.jar -c $HOME/git/MicrobiomeKG/s1_raw_graph/workspace
prompt_for_review "python -m s1_raw_graph.identify_relevant_db" "$HOME/git/MicrobiomeKG/config/s1_raw_graph"
python -m s1_raw_graph.update_workspace
java -jar BioDWH2-v0.6.8.jar -u $HOME/git/MicrobiomeKG/s1_raw_graph/workspace
java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create $HOME/git/MicrobiomeKG/s1_raw_graph/workspace/
java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start $HOME/git/MicrobiomeKG/s1_raw_graph/workspace/
python -m s1_raw_graph.extract_possible_concepts
prompt_for_review "python -m s1_raw_graph.identify_relevant_concepts" "$HOME/git/MicrobiomeKG/config/s1_raw_graph"
prompt_for_review "python -m s1_raw_graph.identify_matching_properties" "$HOME/git/MicrobiomeKG/config/s1_raw_graph"
python -m s1_raw_graph.expand_concepts
docker compose -f s2_raw_metagraph/docker-compose.yml up -d
python -m s2_raw_metagraph.extract_metagraph
docker compose -f s3_filtered_raw_metagraph/docker-compose.yml up -d
prompt_for_review "python -m s3_filtered_raw_metagraph.identify_properties_from_raw_graph" "$HOME/git/MicrobiomeKG/config/s3_filtered_raw_metagraph"
python -m s3_filtered_raw_metagraph.filter_metagraph
sudo -E python3 -m s4_filtered_rolledup_graph.clone_kg
docker compose -f s4_filtered_rolledup_graph/docker-compose.yml up -d
python -m s4_filtered_rolledup_graph.filter_knowledge_graph
docker compose -f s5_filtered_rolledup_metagraph/docker-compose.yml up -d
python -m s5_filtered_rolledup_metagraph.extract_metagraph
docker compose -f s6_postfiltered_metagraph/docker-compose.yml up -d
prompt_for_review "python -m s6_postfiltered_metagraph.identify_relevant_concept_properties" "$HOME/git/MicrobiomeKG/config/s6_postfiltered_metagraph"
python -m s6_postfiltered_metagraph.filter_metagraph
docker compose -f s7_postfiltered_graph/docker-compose.yml up -d
sudo -E python3 -m s7_postfiltered_graph.clone_kg
python -m s7_postfiltered_graph.filter_knowledge_graph
prompt_for_review "python -m s8_postfiltered_graph_with_accessions.identify_accession_keys" "$HOME/git/MicrobiomeKG/config/s8_postfiltered_graph_with_accessions"
python -m s8_postfiltered_graph_with_accessions.add_accessions_in_graph
python -m s9_kg_metrics.quant_compare