import os
import keyword
import re
from neo4j import GraphDatabase

# --- Configuration ---
URI = "bolt://localhost:8083" # or neo4j://localhost:8083
AUTH = None
OUTPUT_DIR = os.path.expanduser("./mapping/models/")

# --- Templates ---

BASE_MODEL_TEMPLATE = """from pydantic import BaseModel, ConfigDict
from neo4j import GraphDatabase
from typing import TypeVar, Type, List, Optional, Any

URI = "bolt://localhost:8083"
# Driver is initialized once for the ORM
driver = GraphDatabase.driver(URI, auth=None)

T = TypeVar('T', bound='Neo4jBaseModel')

class Neo4jBaseModel(BaseModel):
    # Allow Neo4j specific types (like spatial points or Neo4j datetimes)
    # populate_by_name allows initializing with either the python field or the alias
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    
    @classmethod
    def _get_label(cls) -> str:
        # Use the explicitly defined __label__ if it exists, fallback to class name
        return getattr(cls, '__label__', cls.__name__)

    @classmethod
    def find(cls: Type[T], **kwargs) -> List[T]:
        \"\"\"Find nodes matching the exact kwargs properties.\"\"\"
        label = cls._get_label()
        
        # Translate python kwargs to Neo4j aliases if necessary
        mapped_kwargs = {}
        for k, v in kwargs.items():
            field = cls.model_fields.get(k)
            if field and field.alias:
                mapped_kwargs[field.alias] = v
            else:
                mapped_kwargs[k] = v
                
        if mapped_kwargs:
            # Safely wrap properties in backticks in case they contain special chars
            conditions = " AND ".join([f"n.`{k}` = $`{k}`" for k in mapped_kwargs.keys()])
            query = f"MATCH (n:`{label}`) WHERE {conditions} RETURN n"
        else:
            query = f"MATCH (n:`{label}`) RETURN n"
            
        with driver.session() as session:
            # We pass the dictionary to session.run to avoid unpacking invalid python identifier keys
            result = session.run(query, mapped_kwargs)
            return [cls(**record["n"]) for record in result]

    def save(self) -> 'Neo4jBaseModel':
        \"\"\"Saves the current Pydantic model to Neo4j.\"\"\"
        label = self._get_label()
        # by_alias=True ensures we save it back to Neo4j with its original database name
        props = self.model_dump(exclude_none=True, by_alias=True)
        
        query = f"CREATE (n:`{label}`) SET n = $props RETURN n"
        with driver.session() as session:
            session.run(query, props=props)
        return self

    @classmethod
    def get_samples(cls: Type[T], limit: int = 10) -> List[T]:
        \"\"\"Extracts a specific number of complete entity records for this node label.\"\"\"
        label = cls._get_label()
        query = f"MATCH (n:`{label}`) RETURN n LIMIT $limit"
        
        with driver.session() as session:
            result = session.run(query, limit=limit)
            return [cls(**record["n"]) for record in result]

    @classmethod
    def get_property_examples(cls, property_name: str, limit: int = 5) -> List[Any]:
        \"\"\"Extracts a specific number of distinct examples for a specific property.\"\"\"
        field = cls.model_fields.get(property_name)
        neo4j_prop = field.alias if field and field.alias else property_name
        
        # Protect against injection
        if "`" in neo4j_prop:
            raise ValueError("Property name contains invalid character (backtick).")
            
        label = cls._get_label()
        query = f"MATCH (n:`{label}`) WHERE n.`{neo4j_prop}` IS NOT NULL RETURN DISTINCT n.`{neo4j_prop}` AS val LIMIT $limit"
        
        with driver.session() as session:
            result = session.run(query, limit=limit)
            return [record["val"] for record in result]
"""

CLASS_TEMPLATE = """from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class {class_name}(Neo4jBaseModel):
    __label__ = "{original_label}"
{properties}
"""

def sanitize_prop_name(name: str) -> str:
    """Sanitizes Neo4j properties into valid Python identifiers."""
    # Replace non-alphanumeric characters with underscore
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # If the string is empty or starts with a digit, prefix with 'f_'
    if not safe or safe[0].isdigit():
        safe = f"f_{safe}"
    # If it conflicts with a python keyword (e.g., 'def', 'class'), append '_'
    if keyword.iskeyword(safe):
        safe = f"{safe}_"
    return safe

def infer_python_type(val: any) -> str:
    """Maps the Python/Neo4j type of a sampled value to a string for Pydantic."""
    type_name = type(val).__name__
    mapping = {
        'str': 'str',
        'int': 'int',
        'float': 'float',
        'bool': 'bool',
        'list': 'list',
        'dict': 'dict',
        'Date': 'date',
        'DateTime': 'datetime',
        'Time': 'time',
    }
    return mapping.get(type_name, 'Any')

def get_neo4j_schema(driver, sample_size=100):
    """
    Fetches node labels and properties by sampling actual data.
    """
    schema = {}
    
    with driver.session() as session:
        labels_result = session.run("CALL db.labels() YIELD label RETURN label")
        labels = [record["label"] for record in labels_result]
        
        for label in labels:
            schema[label] = {}
            # Backticks prevent syntax errors on labels that contain spaces or special chars
            query = f"MATCH (n:`{label}`) RETURN n LIMIT $limit"
            result = session.run(query, limit=sample_size)
            
            for record in result:
                node = record["n"]
                for key, val in node.items():
                    if key not in schema[label] or schema[label][key] == 'Any':
                        if val is not None:
                            schema[label][key] = infer_python_type(val)
                        else:
                            schema[label][key] = 'Any'
                            
    return schema

def generate_orm():
    print(f"Connecting to Neo4j at {URI}...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        driver.verify_connectivity()
        print("Connected. Inspecting schema via data sampling...")
        schema = get_neo4j_schema(driver)
    finally:
        driver.close()
        
    print(f"Found {len(schema)} node labels. Generating files...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "__init__.py"), "w") as f:
        f.write("# Auto-generated Neo4j ORM Models\n")
        
    base_model_path = os.path.join(OUTPUT_DIR, "base_model.py")
    with open(base_model_path, "w") as f:
        f.write(BASE_MODEL_TEMPLATE)
        
    for label, properties in schema.items():
        # Sanitize label for python class
        class_name = "".join(x.title() for x in label.replace(".", "_").replace("-", "_").split("_"))
        file_name = f"{label.lower()}.py"
        file_path = os.path.join(OUTPUT_DIR, file_name)
        
        seen_props = set()
        prop_lines = []
        
        for prop_name, prop_type in properties.items():
            safe_prop_name = sanitize_prop_name(prop_name)
            
            # Resolve potential sanitized duplications
            original_safe = safe_prop_name
            counter = 1
            while safe_prop_name in seen_props:
                safe_prop_name = f"{original_safe}_{counter}"
                counter += 1
            seen_props.add(safe_prop_name)
            
            # If changed/sanitized, hook it back up using Pydantic's 'alias'
            if safe_prop_name != prop_name:
                escaped_prop_name = prop_name.replace('"', '\\"')
                prop_lines.append(f"    {safe_prop_name}: Optional[{prop_type}] = Field(default=None, alias=\"{escaped_prop_name}\")")
            else:
                prop_lines.append(f"    {safe_prop_name}: Optional[{prop_type}] = None")
            
        if not prop_lines:
            prop_lines.append("    pass")
            
        properties_str = "\n".join(prop_lines)
        
        # INJECT THE ORIGINAL LABEL HERE:
        class_content = CLASS_TEMPLATE.format(
            class_name=class_name, 
            original_label=label.replace('"', '\\"'),
            properties=properties_str
        )
        
        with open(file_path, "w") as f:
            f.write(class_content)
            
        with open(os.path.join(OUTPUT_DIR, "__init__.py"), "a") as f:
            f.write(f"from .{label.lower()} import {class_name}\n")
            
    print(f"Success! Models generated in {OUTPUT_DIR}")

if __name__ == "__main__":
    generate_orm()