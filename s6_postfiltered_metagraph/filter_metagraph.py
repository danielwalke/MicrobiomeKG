from neo4j import GraphDatabase
import os
from utils.filter_metagraph import filter_metagraph

if __name__ == "__main__":
    source_uri = 'bolt://localhost:7691'
    source_user = 'neo4j'
    source_pass = 'neo4j'
    target_uri = 'bolt://localhost:7692'
    target_user = 'neo4j'
    target_pass = ''

    source_driver = GraphDatabase.driver(source_uri, auth=(source_user, source_pass))
    target_driver = GraphDatabase.driver(target_uri, auth=(target_user, target_pass))
    intresting_properties_file_path = os.path.expanduser("~/git/MicrobiomeKG/config/s6_postfiltered_metagraph/interesting_concept_properties.json")
    
    filter_metagraph(source_driver, target_driver, intresting_properties_file_path)