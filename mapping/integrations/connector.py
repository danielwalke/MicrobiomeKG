from neo4j import GraphDatabase

class Neo4jConnector:
    def __init__(self, uri="bolt://localhost:8083", user="neo4j", password="password"):
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