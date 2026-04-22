from neo4j import GraphDatabase
import uuid
import os
from tqdm import tqdm
import json
import time

def create_secure_id():
    return str(uuid.uuid4())

class Neo4jConnector:
    def __init__(self, uri="bolt://localhost:8083", user="neo4j", password="password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.id_properties_per_node_label_path = os.path.expanduser("~/git/MicrobiomeKG/config/s1_raw_graph/id_properties_per_node_label.json")

    def close(self):
        self.driver.close()

    def pre_process_ids(self):
        property_key_to_prefix = {
            "omim_id": "OMIM:",
            "refseq_id": "Genbank:",
        }
        property_to_property_value_query = {
            "refseq_id": "MATCH (n) WHERE n.refseq_id IS NOT NULL SET n.processed_refseq_id = split(n.refseq_id, '.')[0]"
        }
        with self.driver.session() as session:
            for property_key, prefix in property_key_to_prefix.items():
                session.run(f"MATCH (n) WHERE n.{property_key} IS NOT NULL SET n.processed_{property_key} = CASE WHEN NOT toString(n.{property_key}) STARTS WITH '{prefix}' THEN '{prefix}' + toString(n.{property_key}) ELSE toString(n.{property_key}) END")
            for property_key, query in property_to_property_value_query.items():
                session.run(query)

    def expand_array_properties(self):
        fetch_query = "MATCH (n) WHERE n.names IS NOT NULL OR n.ids IS NOT NULL OR n.db_references IS NOT NULL RETURN id(n) AS node_id, properties(n) AS props"
        
        with self.driver.session() as session:
            result = session.run(fetch_query)
            batch = []
            
            for record in result:
                updates = {}
                node_id = record["node_id"]
                props = record["props"]
                
                for key, value in props.items():
                    if key == "ids":
                        if isinstance(value, list):
                            for idx, identifier in enumerate(value):
                                updates[f"id_{idx}"] = identifier
                        elif isinstance(value, str):
                            updates["id_0"] = value
                    elif key == "db_references":
                        if isinstance(value, list):
                            for idx, reference in enumerate(value):
                                updates[f"db_reference_{idx}"] = reference
                        elif isinstance(value, str):
                            updates["db_reference_0"] = value
                    else:
                        if isinstance(value, list) and len(value) == 1:
                            updates[f"{key}_str"] = value[0]
                            
                if updates:
                    batch.append({"node_id": node_id, "updates": updates})
                    
                if len(batch) >= 1000:
                    update_query = "UNWIND $batch AS record MATCH (n) WHERE id(n) = record.node_id SET n += record.updates"
                    session.run(update_query, batch=batch)
                    batch = []
                    
            if batch:
                update_query = "UNWIND $batch AS record MATCH (n) WHERE id(n) = record.node_id SET n += record.updates"
                session.run(update_query, batch=batch)

    def fetch_id_properties_per_node_label(self):
        ## Check all unique prooperties that might have a unique property value and the extracted names and ids 
        with self.driver.session() as session:
            result = session.run("""
                CALL db.schema.nodeTypeProperties() YIELD nodeLabels, propertyName, propertyTypes
                WHERE all(pt IN propertyTypes WHERE NOT pt CONTAINS 'Array')
                UNWIND nodeLabels AS label
                WITH DISTINCT label, propertyName
                WHERE label <> 'Entity'
                WITH label, propertyName, (propertyName =~ '(?i)(id_|processed_|db_reference_).*') AS is_regex_match
                CALL {
                    WITH label, propertyName, is_regex_match
                    WITH * WHERE is_regex_match = false
                    CALL apoc.cypher.run(
                        "MATCH (n:`" + label + "`) WHERE n.`" + propertyName + "` IS NOT NULL " +
                        "RETURN count(n) AS total_count, count(DISTINCT n.`" + propertyName + "`) AS distinct_count",
                        {}
                    ) YIELD value
                    RETURN value.total_count AS total_count, value.distinct_count AS distinct_count
                    UNION
                    WITH label, propertyName, is_regex_match
                    WITH * WHERE is_regex_match = true
                    RETURN 1 AS total_count, 1 AS distinct_count
                }
                WITH *
                WHERE is_regex_match OR (total_count = distinct_count AND total_count > 0)
                RETURN label, collect(propertyName) AS unique_properties
                """) #|name_
            return list(result)

    def get_id_properties_per_node_label(self):
        if os.path.exists(self.id_properties_per_node_label_path):
            with open(self.id_properties_per_node_label_path, "r") as f:
                return json.load(f)

        id_properties = dict()
        result = self.fetch_id_properties_per_node_label()

        for record in result:
            node_label = record["label"]
            properties = record["unique_properties"]
            properties = list(filter(lambda prop: prop != "neo4j_id", properties))
            id_properties[node_label] = properties

        with open(self.id_properties_per_node_label_path, "w") as f:
            json.dump(id_properties, f)
        return id_properties

    def get_nodes_by_label(self, label):
        with self.driver.session() as session:
            query = f"MATCH (n:`{label}`) RETURN n"
            result = session.run(query)
            return [record["n"] for record in result]
    
    def get_node_labels(self):
        with self.driver.session() as session:
            result = session.run("CALL db.labels() YIELD label RETURN label")
            return [record["label"] for record in result]

    def write_merged_nodes_to_db(self, universal_id_to_neo4j_ids, batch_size=10000):
        query = """
        UNWIND $batch AS record
        CREATE (m:MergedNode {merged_node_id: record.universal_id})
        WITH m, record.neo4j_ids AS raw_ids
        UNWIND raw_ids AS raw_id
        MATCH (n) WHERE id(n) = raw_id
        CREATE (n)-[:MERGED_TO]->(m)
        """
        
        valid_items_count = sum(1 for n_ids in universal_id_to_neo4j_ids.values() if len(n_ids) > 1)
        
        if valid_items_count == 0:
            return
            
        total_batches = (valid_items_count + batch_size - 1) // batch_size

        def generate_batches(data_dict, size):
            current_batch = []
            for u_id, n_ids in data_dict.items():
                if len(n_ids) > 1:
                    current_batch.append({"universal_id": u_id, "neo4j_ids": n_ids})
                    if len(current_batch) == size:
                        yield current_batch
                        current_batch = []
            if current_batch:
                yield current_batch

        with self.driver.session() as session:
            for batch in tqdm(generate_batches(universal_id_to_neo4j_ids, batch_size), total=total_batches, desc="Writing MergedNodes"):
                session.run(query, batch=batch)

class EntityResolver:
    def __init__(self, connector):
        self.connector = connector
        self.value_to_universal_id = dict()
        self.universal_id_to_neo4j_ids = dict()
        self.universal_id_to_values = dict()
        self.invalid_values = {"none", "null", "unknown", "na", "n/a", ""}

    def is_valid_value(self, val):
        if val is None:
            return False
        if str(val).strip().lower() in self.invalid_values:
            return False
        return True

    def register_values(self, valid_values, universal_id, neo4j_node_id):
        if universal_id not in self.universal_id_to_neo4j_ids:
            self.universal_id_to_neo4j_ids[universal_id] = []
            self.universal_id_to_values[universal_id] = set()
            
        self.universal_id_to_neo4j_ids[universal_id].append(neo4j_node_id)
        
        for val in valid_values:
            self.value_to_universal_id[val] = universal_id
            self.universal_id_to_values[universal_id].add(val)

    def resolve_node(self, neo4j_node_id, valid_values):
        matched_universal_ids = set()
        
        for val in valid_values:
            if val in self.value_to_universal_id:
                matched_universal_ids.add(self.value_to_universal_id[val])
                
        matched_universal_ids = list(matched_universal_ids)

        if not matched_universal_ids:
            winning_id = create_secure_id()
            
        elif len(matched_universal_ids) == 1:
            winning_id = matched_universal_ids[0]
            
        else:
            winning_id = matched_universal_ids[0]
            losing_ids = matched_universal_ids[1:]
            
            for losing_id in losing_ids:
                nodes_to_move = self.universal_id_to_neo4j_ids.pop(losing_id, [])
                self.universal_id_to_neo4j_ids[winning_id].extend(nodes_to_move)
                
                values_to_update = self.universal_id_to_values.pop(losing_id, set())
                for val in values_to_update:
                    self.value_to_universal_id[val] = winning_id
                    self.universal_id_to_values[winning_id].add(val)
                    
        self.register_values(valid_values, winning_id, neo4j_node_id)

    def process_graph(self, node_label_to_id_properties):
        labels = self.connector.get_node_labels()
        
        for label in labels:
            if label == "Entity" or label == "MergedNode":
                continue
                
            id_props = node_label_to_id_properties.get(label, [])
            if not id_props:
                continue
                
            nodes = self.connector.get_nodes_by_label(label)
            
            for node in tqdm(nodes, desc=f"Resolving {label}"):
                valid_values = []
                for prop in id_props:
                    val = node.get(prop)
                    if self.is_valid_value(val):
                        valid_values.append(val)
                
                if valid_values:
                    self.resolve_node(node.id, valid_values)

if __name__ == "__main__":
    preprocessinmg_time_start = time.time()
    connector = Neo4jConnector()
    # connector.pre_process_ids()
    # connector.expand_array_properties()
    print(f"Preprocessing time: {time.time() - preprocessinmg_time_start:.2f} seconds")
    

    if os.path.exists(connector.id_properties_per_node_label_path):
        os.remove(connector.id_properties_per_node_label_path)

    id_identification_time_start = time.time()    
    id_props_map = connector.get_id_properties_per_node_label()
    print(f"ID property identification time: {time.time() - id_identification_time_start:.2f} seconds")

    entity_resolution_time_start = time.time()
    resolver = EntityResolver(connector)
    resolver.process_graph(id_props_map)
    print(f"Entity resolution time: {time.time() - entity_resolution_time_start:.2f} seconds")
    
    connector.write_merged_nodes_to_db(resolver.universal_id_to_neo4j_ids)
    connector.close()

    """TODO: 
    - Compare to marcels MAPPED_TO
    - Broaden to single nodes (Just keep them with me to not lose them right now)
    - Label resolution (assign each MergedNode a concept) -> think about efficient ways (caching might work - either dict for checking existing node label combinationor more advanced stuff eg with dspy to cache LLM requests itself? not sure yet but more hopeful now)
    - Filtering with less strict criteria by the LLM
    """