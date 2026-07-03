from tqdm import tqdm

class NodeIntegrator:
    def __init__(self, connector):
        self.connector = connector

    def integrate(self, blueprint_class, universal_id_to_neo4j_ids):
        # Setup lookup mapping for fast Neo4j property injection
        reverse_map = {
            (getattr(orm, "__label__", orm.__name__), prop): field_name 
            for field_name, (orm, prop) in blueprint_class.__source_mappings__.items()
        }
        
        batch_to_save = []
        
        for universal_id, neo4j_ids in tqdm(universal_id_to_neo4j_ids.items(), desc=f"Integrating {blueprint_class.__label__}"):
            # 1. Fetch properties for all merged nodes
            raw_data = self._fetch_raw_data(neo4j_ids, reverse_map)
            
            # 2. Build the Pydantic model
            model = blueprint_class(universal_id=universal_id, **raw_data)
            
            # 3. Process & Integrate
            model.preprocess()
            model.integrate()
            
            # 4. Queue for saving
            batch_to_save.append({
                "universal_id": universal_id,
                "props": model.get_final_properties(),
                "orig_ids": neo4j_ids
            })
            
        # 5. Save batch
        self._save_to_neo4j(blueprint_class.__label__, batch_to_save)

    def _fetch_raw_data(self, node_ids, reverse_map):
        raw_data = {field_name: [] for field_name in reverse_map.values()}
        
        query = """
        MATCH (n) WHERE id(n) IN $node_ids
        RETURN labels(n)[0] AS label, properties(n) AS props
        """
        with self.connector.driver.session() as session:
            result = session.run(query, node_ids=node_ids)
            for record in result:
                label = record["label"]
                props = record["props"]
                
                for (mapped_label, target_prop), field_name in reverse_map.items():
                    if label == mapped_label and target_prop in props:
                        val = props[target_prop]
                        if isinstance(val, list):
                            raw_data[field_name].extend(val)
                        else:
                            raw_data[field_name].append(val)
        return raw_data

    def _save_to_neo4j(self, target_label, batch):
        if not batch: return
        query = f"""
        UNWIND $batch AS row
        CREATE (m:`{target_label}`)
        SET m = row.props
        WITH m, row
        MATCH (orig) WHERE id(orig) IN row.orig_ids
        MERGE (orig)-[:MAPPED_TO]->(m)
        """
        self.connector.execute_write(query, {"batch": batch})