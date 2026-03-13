class Neo4jAuth:
    def __init__(self, uri = "bolt://localhost:7687", user = "neo4j", password = "password"):
        self.uri = uri
        self.user =  user
        self.password = password