from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:8083")          
def remove_dot_from_node_labels(tx):
    query = """
    MATCH (n)
    WHERE any(label IN labels(n) WHERE label CONTAINS '.')
    WITH n, [label IN labels(n) | CASE WHEN label CONTAINS '.' THEN replace(label, '.', '_') ELSE label END] AS newLabels
    CALL apoc.create.setLabels(n, newLabels) YIELD node
    RETURN count(node) AS updatedNodes
    """
    result = tx.run(query)
    return result.single()["updatedNodes"]

with driver.session() as session:
    updated_nodes = session.write_transaction(remove_dot_from_node_labels)
    print(f"Updated {updated_nodes} nodes by replacing dots in labels with underscores.")
    