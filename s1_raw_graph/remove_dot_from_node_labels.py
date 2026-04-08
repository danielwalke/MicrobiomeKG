from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:8083", auth=("neo4j", "your_password"))          

def remove_dot_from_node_labels_batched(tx):
    query = """
    CALL apoc.periodic.iterate(
        "MATCH (n) WHERE any(label IN labels(n) WHERE label CONTAINS '.') RETURN n",
        "WITH n, [label IN labels(n) | CASE WHEN label CONTAINS '.' THEN replace(label, '.', '_') ELSE label END] AS newLabels 
         CALL apoc.create.setLabels(n, newLabels) YIELD node RETURN count(node)",
        {batchSize: 10000, parallel: false}
    )
    YIELD batches, total
    RETURN total
    """
    result = tx.run(query)
    return result.single()["total"]

with driver.session() as session:
    updated_nodes = session.execute_write(remove_dot_from_node_labels_batched)
    print(f"Processed {updated_nodes} nodes in batches.")