from neo4j import GraphDatabase
import uuid
import os
from tqdm import tqdm
import json
import time
import re
from collections import Counter

# Strict NLP Stemmer import - no fallback
try:
    from nltk.stem import PorterStemmer
    _stemmer = PorterStemmer()
    def stem_word(word):
        return _stemmer.stem(word)
except ImportError:
    raise Exception("The 'nltk' library is required. Please install it using 'pip install nltk' to perform stemming.")

def get_consensus_label(labels):
    """Finds the largest overlapping stem among a list of labels."""
    if not labels:
        return "Unknown"
    if len(labels) == 1:
        return labels[0]
        
    stem_counts = Counter()
    stem_to_originals = {}
    
    for label in labels:
        # Tokenize camel case and underscores (e.g., UniprotProtein -> Uniprot Protein)
        split_label = re.sub(r'([a-z])([A-Z])', r'\1 \2', label)
        split_label = split_label.replace('_', ' ').replace('-', ' ')
        tokens = split_label.lower().split()
        
        for token in tokens:
            # Skip overly short connectors if they exist
            if len(token) <= 1: 
                continue
            s = stem_word(token)
            stem_counts[s] += 1
            if s not in stem_to_originals:
                stem_to_originals[s] = set()
            stem_to_originals[s].add(token)
            
    if not stem_counts:
        return labels[0]
        
    # Highest overlap stem
    best_stem = stem_counts.most_common(1)[0][0]
    # Fetch the shortest original string that generated this stem for readability
    best_token = min(stem_to_originals[best_stem], key=len)
    
    return best_token.capitalize()

def lower(string):
    if isinstance(string, str):
        return string.lower()
    return string

def create_secure_id():
    return str(uuid.uuid4())

class Neo4jConnector:
    def __init__(self, uri="bolt://localhost:8083", user="neo4j", password="password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.id_properties_per_node_label_path = "/home/daniel.walke/git/MicrobiomeKG/config/s1_raw_graph/id_properties_per_node_label.json"

    def close(self):
        self.driver.close()

    def get_id_properties_per_node_label(self):
        if not os.path.exists(self.id_properties_per_node_label_path):
            raise FileNotFoundError(f"Candidate IDs JSON not found at {self.id_properties_per_node_label_path}")
            
        with open(self.id_properties_per_node_label_path, "r") as f:
            id_properties = json.load(f)
            
        print(f"Loaded known ID properties from cache.")

        for label in id_properties:
            id_properties[label] = [p for p in id_properties[label] if p != "neo4j_id" and not re.search(r"db_reference_\d+", p) and not p == "__id"]
            if "gene" in lower(label):
                id_properties[label].extend(["ids_str", "name", "names_str"])
            id_properties[label].append("db_references_str")
            if "publication" in lower(label) or "citation" in lower(label):
                id_properties[label].extend(["db_reference_0", "pmid"])
            if label == "Uniprot_Protein":
                id_properties[label] = list(filter(lambda p: p in ["accession", "processed_accession"], id_properties[label]))
                
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


class EntityResolver:
    def __init__(self, connector):
        self.connector = connector
        self.value_to_universal_id = dict()
        self.universal_id_to_nodes = dict()
        self.universal_id_to_values = dict()
        self.invalid_values = {"none", "null", "unknown", "na", "n/a", ""}

    def is_valid_value(self, val):
        if val is None:
            return False
        if str(val).strip().lower() in self.invalid_values:
            return False
        return True

    def preprocess_node_properties(self, raw_props):
        """Processes all arrays, prefixes, and replacements client-side."""
        props = dict(raw_props)
        
        # 1. Clean up '-'
        for k in list(props.keys()):
            if props[k] == '-':
                props.pop(k)

        # 2. Add prefixes and handle special ID processing
        property_key_to_prefix = {
            "omim_id": "OMIM:",
            "refseq_id": "Genbank:",
            "accession": "UniProtKB:",
            "entrez_gene_id": "NCBIGene:",
        }
        
        for key, prefix in property_key_to_prefix.items():
            if key in props and props[key] is not None:
                val = str(props[key])
                if key == "refseq_id":
                    val = val.split('.')[0]
                
                if not val.startswith(prefix):
                    props[f"processed_{key}"] = f"{prefix}{val}"
                else:
                    props[f"processed_{key}"] = val

        # 3. String Replacements
        if "db_references_str" in props and props["db_references_str"]:
            props["processed_db_references_str"] = str(props["db_references_str"]).replace("PubMed:", "PMID:")
            
        if "db_references" in props and props["db_references"]:
            v = props["db_references"]
            if isinstance(v, list):
                props["db_references"] = [str(x).replace("NCBI Taxonomy:", "NCBITaxon:") for x in v]
            elif isinstance(v, str):
                props["db_references"] = str(v).replace("NCBI Taxonomy:", "NCBITaxon:")

        # 4. Expand Arrays
        for key in ["ids", "db_references", "names"]:
            if key in props and props[key] is not None:
                val = props[key]
                
                if key == "ids":
                    if isinstance(val, list):
                        for idx, identifier in enumerate(val):
                            props[f"id_{idx}"] = identifier
                    elif isinstance(val, str):
                        props["id_0"] = val
                        
                elif key == "db_references":
                    if isinstance(val, list):
                        for idx, reference in enumerate(val):
                            props[f"db_reference_{idx}"] = reference
                    elif isinstance(val, str):
                        props["db_reference_0"] = val
                        
                elif key == "names":
                    if isinstance(val, list) and len(val) == 1:
                        props["names_str"] = val[0]
                        
        return props

    def register_values(self, valid_key_values, universal_id, neo4j_node_id, label):
        if universal_id not in self.universal_id_to_nodes:
            self.universal_id_to_nodes[universal_id] = []
            self.universal_id_to_values[universal_id] = set()
            
        self.universal_id_to_nodes[universal_id].append({
            "node_id": neo4j_node_id,
            "label": label,
            "key_values": valid_key_values
        })
        
        for key, val in valid_key_values:
            self.value_to_universal_id[val] = universal_id
            self.universal_id_to_values[universal_id].add(val)

    def resolve_node(self, neo4j_node_id, label, valid_key_values):
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
                nodes_to_move = self.universal_id_to_nodes.pop(losing_id, [])
                self.universal_id_to_nodes[winning_id].extend(nodes_to_move)
                
                values_to_update = self.universal_id_to_values.pop(losing_id, set())
                for val in values_to_update:
                    self.value_to_universal_id[val] = winning_id
                    self.universal_id_to_values[winning_id].add(val)
                    
        self.register_values(valid_key_values, winning_id, neo4j_node_id, label)

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
                # Process the node properties strictly in memory
                processed_props = self.preprocess_node_properties(dict(node))
                
                valid_key_values = []
                for prop in id_props:
                    val = processed_props.get(prop)
                    if self.is_valid_value(val):
                        valid_key_values.append((prop, val))
                
                if valid_key_values:
                    self.resolve_node(node.id, label, valid_key_values)

    def export_to_json(self, output_path="merged_nodes.json"):
        export_dict = {}
        
        for uid, nodes in tqdm(self.universal_id_to_nodes.items(), desc="Aggregating Schema for JSON"):
            # Only track groups that actually resulted in a merge (multiple nodes combined)
            if len(nodes) > 1:
                unique_labels = list(set([n["label"] for n in nodes]))
                consensus_key = get_consensus_label(unique_labels)
                
                if consensus_key not in export_dict:
                    export_dict[consensus_key] = set()
                    
                for n in nodes:
                    for k, v in n["key_values"]:
                        # Store just the label and attribute as a tuple in the set (drops values, auto-deduplicates)
                        export_dict[consensus_key].add((n["label"], k))
                        
        # Format into clean JSON list of dicts
        final_json_structure = {}
        for consensus_key, attributes in export_dict.items():
            final_json_structure[consensus_key] = [
                {"nodelabel": label, "attribute": attr} 
                for label, attr in sorted(list(attributes))
            ]
                
        with open(output_path, "w") as f:
            json.dump(final_json_structure, f, indent=4)
        print(f"Exported aggregated node configurations to {output_path}")


if __name__ == "__main__":
    connector = Neo4jConnector()
    
    id_identification_time_start = time.time()    
    id_props_map = connector.get_id_properties_per_node_label()
    print(f"ID property identification time: {time.time() - id_identification_time_start:.2f} seconds")

    # Processing and grouping into universal id clusters
    entity_resolution_time_start = time.time()
    resolver = EntityResolver(connector)
    resolver.process_graph(id_props_map)
    print(f"Entity resolution time: {time.time() - entity_resolution_time_start:.2f} seconds")
    
    # Export overlapping elements dynamically to JSON
    json_output_path = "merged_nodes_output.json"
    resolver.export_to_json(json_output_path)
    
    connector.close()