from tqdm import tqdm
from collections import defaultdict
from src.s2_mapping.linking.base_edge import BaseEdgeDefinition

class EntityLinker:
    def __init__(self, connector):
        self.connector = connector
        self.invalid_values = {"none", "null", "unknown", "na", "n/a", ""}

    def is_valid_value(self, val):
        if val is None: return False
        if str(val).strip().lower() in self.invalid_values: return False
        return True

    def _extract_and_standardize(self, raw_val, standardize_method):
        """Flattens arrays and calls your custom class methods."""
        values = raw_val if isinstance(raw_val, list) else [raw_val]
        valid_standardized = set()
        
        for v in values:
            if self.is_valid_value(v):
                std_v = standardize_method(v)
                if self.is_valid_value(std_v):
                    valid_standardized.add(std_v)
                    
        return valid_standardized

    def process_edge(self, edge_def: BaseEdgeDefinition):
        print(f"Fetching {edge_def.source_label} nodes...")
        source_nodes = self.connector.get_nodes_by_label(edge_def.source_label)
        
        val_to_source_ids = defaultdict(list)
        
        for node in tqdm(source_nodes, desc=f"Mapping {edge_def.source_label} values"):
            raw_val = node["props"].get(edge_def.source_property)
            # Call your custom class method
            std_vals = self._extract_and_standardize(raw_val, edge_def.standardize_source)
            
            for std_val in std_vals:
                val_to_source_ids[std_val].append(node["id"])

        if not val_to_source_ids:
            print(f"No valid source values found for {edge_def.source_label}. Skipping.")
            return

        print(f"Fetching {edge_def.target_label} nodes...")
        target_nodes = self.connector.get_nodes_by_label(edge_def.target_label)
        edges_to_create = []
        
        for node in tqdm(target_nodes, desc=f"Linking {edge_def.target_label} nodes"):
            target_id = node["id"]
            raw_val = node["props"].get(edge_def.target_property)
            # Call your custom class method
            std_vals = self._extract_and_standardize(raw_val, edge_def.standardize_target)
            
            for std_val in std_vals:
                if std_val in val_to_source_ids:
                    for source_id in val_to_source_ids[std_val]:
                        if source_id == target_id:
                            continue # Still preventing self-linking. You're welcome.
                            
                        edges_to_create.append({
                            "source_id": source_id,
                            "target_id": target_id,
                            "shared_value": std_val,
                            "source_label": edge_def.source_label,
                            "target_label": edge_def.target_label,
                            "source_property": edge_def.source_property,
                            "target_property": edge_def.target_property
                        })

        if not edges_to_create:
            print("Zero links found. Moving on.")
            return

        print(f"Writing {len(edges_to_create)} edges to Neo4j...")
        
        # Batch inserting with metadata. Don't touch this Cypher.
        cypher_query = f"""
        UNWIND $batch AS row
        MATCH (s) WHERE id(s) = row.source_id
        MATCH (t) WHERE id(t) = row.target_id
        MERGE (s)-[r:`{edge_def.relationship_label}` {{shared_value: row.shared_value}}]->(t)
        SET r.source_label = row.source_label,
            r.target_label = row.target_label,
            r.source_property = row.source_property,
            r.target_property = row.target_property
        """
        
        self.connector.execute_batch_write(cypher_query, edges_to_create)
        print(f"Finished {edge_def.relationship_label}.")