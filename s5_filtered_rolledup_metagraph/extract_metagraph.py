from neo4j import GraphDatabase
from utils.migrate_metagraph import migrate_metagraph


def main():
    source_uri = 'bolt://localhost:7690'
    source_user = 'neo4j'
    source_pass = 'neo4j'
    target_uri = 'bolt://localhost:7691'
    target_user = 'neo4j'
    target_pass = ''
    source_driver = GraphDatabase.driver(source_uri, auth=(source_user, source_pass))
    target_driver = GraphDatabase.driver(target_uri, auth=(target_user, target_pass))
    migrate_metagraph(source_driver, target_driver)

if __name__ == "__main__":
    main()