from neo4j import GraphDatabase
from s4_filtered_rolledup_graph.filter_knowledge_graph import filter_properties
  
def delete_database_nodes(t_session):
    labels_result = t_session.run(
        """
        CALL db.labels() YIELD label
        WHERE NOT label CONTAINS('Merged') /*=~ '^[A-Z]+$'*/
        RETURN label AS lbl
        """
    ).data()

    deleted_labels = [record["lbl"] for record in labels_result]

    if deleted_labels:
        constraints = t_session.run(
            """
            SHOW CONSTRAINTS YIELD name, labelsOrTypes
            WHERE any(label IN labelsOrTypes WHERE label IN $deleted_labels)
            RETURN name
            """,
            deleted_labels=deleted_labels
        ).data()

        for record in constraints:
            t_session.run(f"DROP CONSTRAINT `{record['name']}`")

        indexes = t_session.run(
            """
            SHOW INDEXES YIELD name, labelsOrTypes, type
            WHERE type <> 'LOOKUP' AND any(label IN labelsOrTypes WHERE label IN $deleted_labels)
            RETURN name
            """,
            deleted_labels=deleted_labels
        ).data()

        for record in indexes:
            t_session.run(f"DROP INDEX `{record['name']}`")

    t_session.run(
        """
        CALL apoc.periodic.iterate(
        "MATCH (n) WHERE size(labels(n)) = 0 OR NOT all(l IN labels(n) WHERE l CONTAINS('Merged') /*=~ '^[A-Z]+$'*/) RETURN n",
        "DETACH DELETE n",
        {batchSize: 10000, parallel: false}
        )
        """
    ).consume()

def remove_redundant_edges(t_session):
    t_session.run(
        """
        CALL apoc.periodic.iterate(
        "MATCH ()-[r]->() WITH r.__id AS relId, collect(r) AS rels WHERE size(rels) > 1 RETURN rels",
        "UNWIND tail(rels) AS relToRemove DELETE relToRemove",
        {batchSize: 10000, parallel: false}
        )
        """
    ).consume()

def run_migration(metagraph_driver, target_driver):
    with target_driver.session() as t_session, metagraph_driver.session() as m_session:
        filter_properties(m_session, t_session)
        delete_database_nodes(t_session)
        remove_redundant_edges(t_session)

    target_driver.close()
    metagraph_driver.close()

if __name__ == "__main__":
    metagraph_uri = 'bolt://localhost:7692'
    metagraph_user = 'neo4j'
    metagraph_pass = 'neo4j'
    target_uri = 'bolt://localhost:7693'
    target_user = 'neo4j'
    target_pass = ''
    metagraph_driver = GraphDatabase.driver(metagraph_uri, auth=(metagraph_user, metagraph_pass))
    target_driver = GraphDatabase.driver(target_uri, auth=(target_user, target_pass))
    
    run_migration(metagraph_driver, target_driver)