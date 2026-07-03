from neo4j import GraphDatabase

import os

class Neo4jConnector:
    def __init__(self, uri=None, user=None, password=None):
        if uri is None:
            uri = os.getenv("MAPPED_GRAPH_BOLT_URI", "bolt://localhost:8085")
            user = os.getenv("MAPPED_GRAPH_USERNAME", "neo4j")
            password = os.getenv("MAPPED_GRAPH_PASSWORD", "password")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_nodes_by_label(self, label):
        """Returns clean dictionaries of IDs and properties for safe processing."""
        with self.driver.session() as session:
            query = f"MATCH (n:`{label}`) RETURN id(n) AS node_id, properties(n) AS props"
            result = session.run(query)
            return [{"id": record["node_id"], "props": record["props"]} for record in result]
    
    def get_node_labels(self):
        with self.driver.session() as session:
            result = session.run("CALL db.labels() YIELD label RETURN label")
            return [record["label"] for record in result]

    def execute_write(self, query, parameters=None):
        with self.driver.session() as session:
            session.run(query, parameters or {})
    
    def execute_batch_write(self, query, parameters_list, batch_size=5000):
        with self.driver.session() as session:
            for i in range(0, len(parameters_list), batch_size):
                batch = parameters_list[i : i + batch_size]
                session.run(query, {"batch": batch})