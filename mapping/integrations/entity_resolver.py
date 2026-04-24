import uuid
from tqdm import tqdm

def create_secure_id():
    return uuid.uuid4().hex

class EntityResolver:
    def __init__(self, connector):
        self.connector = connector
        self.value_to_universal_id = dict()
        self.universal_id_to_neo4j_ids = dict()
        self.universal_id_to_values = dict()
        self.universal_id_to_key_values = dict()
        self.invalid_values = {"none", "null", "unknown", "na", "n/a", ""}

    def is_valid_value(self, val):
        if val is None: return False
        if str(val).strip().lower() in self.invalid_values: return False
        return True

    def register_values(self, valid_key_values, universal_id, neo4j_node_id):
        if universal_id not in self.universal_id_to_neo4j_ids:
            self.universal_id_to_neo4j_ids[universal_id] = []
            self.universal_id_to_values[universal_id] = set()
            self.universal_id_to_key_values[universal_id] = set()
            
        self.universal_id_to_neo4j_ids[universal_id].append(neo4j_node_id)
        
        for key, val in valid_key_values:
            self.value_to_universal_id[val] = universal_id
            self.universal_id_to_values[universal_id].add(val)
            self.universal_id_to_key_values[universal_id].add((key, val))

    def resolve_node(self, neo4j_node_id, valid_key_values):
        matched_universal_ids = set()
        for key, val in valid_key_values:
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
                
                key_values_to_move = self.universal_id_to_key_values.pop(losing_id, set())
                for kv in key_values_to_move:
                    self.universal_id_to_key_values[winning_id].add(kv)
                    
        self.register_values(valid_key_values, winning_id, neo4j_node_id)

    def process_graph(self, blueprint_class):
        """Builds configuration dynamically from your Blueprint class."""
        
        # 1. Group configuration by Database Label
        label_to_props = {}
        for field, (orm_class, prop) in blueprint_class.__source_mappings__.items():
            db_label = getattr(orm_class, "__label__", orm_class.__name__)
            label_to_props.setdefault(db_label, []).append((orm_class, prop))

        # 2. Iterate through graph
        for label, config_list in label_to_props.items():
            nodes = self.connector.get_nodes_by_label(label)
            
            for node in tqdm(nodes, desc=f"Resolving {label}"):
                valid_key_values = []
                
                for orm_class, prop in config_list:
                    raw_val = node["props"].get(prop)
                    
                    # Flattens Lists to fix the "TypeError: unhashable list" error!
                    values_to_process = raw_val if isinstance(raw_val, list) else [raw_val]
                    
                    for val in values_to_process:
                        if self.is_valid_value(val):
                            # Ensure "12345" and "PubMed:12345" become the same string
                            std_val = blueprint_class.standardize_id_for_resolver(orm_class, prop, val)
                            valid_key_values.append((prop, std_val))
                
                if valid_key_values:
                    self.resolve_node(node["id"], valid_key_values)