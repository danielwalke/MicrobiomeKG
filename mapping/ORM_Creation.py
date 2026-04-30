import os
import keyword
import re
from neo4j import GraphDatabase

# --- Configuration ---
URI = "bolt://localhost:8083" 
AUTH = None
OUTPUT_DIR = os.path.expanduser("./mapping/models/")

# --- Templates ---

BASE_MODEL_TEMPLATE = """from pydantic import BaseModel, ConfigDict
from neo4j import GraphDatabase
from typing import TypeVar, Type, List, Optional, Any

URI = "bolt://localhost:8083"
driver = GraphDatabase.driver(URI, auth=None)

T = TypeVar('T', bound='Neo4jBaseModel')

class Neo4jBaseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    
    @classmethod
    def _get_label(cls) -> str:
        return getattr(cls, '__label__', cls.__name__)

    @classmethod
    def find(cls: Type[T], **kwargs) -> List[T]:
        label = cls._get_label()
        
        mapped_kwargs = {}
        for k, v in kwargs.items():
            field = cls.model_fields.get(k)
            if field and field.alias:
                mapped_kwargs[field.alias] = v
            else:
                mapped_kwargs[k] = v
                
        if mapped_kwargs:
            conditions = " AND ".join([f"n.`{k}` = $`{k}`" for k in mapped_kwargs.keys()])
            query = f"MATCH (n:`{label}`) WHERE {conditions} RETURN n"
        else:
            query = f"MATCH (n:`{label}`) RETURN n"
            
        with driver.session() as session:
            result = session.run(query, mapped_kwargs)
            return [cls(**record["n"]) for record in result]

    def save(self) -> 'Neo4jBaseModel':
        label = self._get_label()
        props = self.model_dump(exclude_none=True, by_alias=True)
        query = f"CREATE (n:`{label}`) SET n = $props RETURN n"
        with driver.session() as session:
            session.run(query, props=props)
        return self

    @classmethod
    def get_samples(cls: Type[T], limit: int = 10) -> List[T]:
        label = cls._get_label()
        query = f"MATCH (n:`{label}`) RETURN n LIMIT $limit"
        with driver.session() as session:
            result = session.run(query, limit=limit)
            return [cls(**record["n"]) for record in result]

    @classmethod
    def get_property_examples(cls, property_name: str, limit: int = 5) -> List[Any]:
        field = cls.model_fields.get(property_name)
        neo4j_prop = field.alias if field and field.alias else property_name
        
        if "`" in neo4j_prop:
            raise ValueError("Property name contains invalid character (backtick).")
            
        label = cls._get_label()
        query = f"MATCH (n:`{label}`) WHERE n.`{neo4j_prop}` IS NOT NULL RETURN DISTINCT n.`{neo4j_prop}` AS val LIMIT $limit"
        with driver.session() as session:
            result = session.run(query, limit=limit)
            return [record["val"] for record in result]
"""

CLASS_TEMPLATE = """from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class {class_name}(Neo4jBaseModel):
    __label__ = "{original_label}"
{properties}
"""

def sanitize_class_name(name: str) -> str:
    """Sanitizes into valid Python class names, PRESERVING original casing & underscores."""
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if not safe or safe[0].isdigit():
        safe = f"Node_{safe}"
    if keyword.iskeyword(safe):
        safe = f"{safe}_"
    return safe

def sanitize_module_name(name: str) -> str:
    """Sanitizes into valid lowercase Python module/file names."""
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()
    if not safe or safe[0].isdigit():
        safe = f"node_{safe}"
    if keyword.iskeyword(safe):
        safe = f"{safe}_"
    return safe

def map_db_schema_type(types_list: list) -> str:
    if not types_list:
        return 'Any'
    if len(types_list) > 1:
        return 'Any'
        
    neo4j_type = types_list[0]
    mapping = {
        'String': 'str', 'Long': 'int', 'Double': 'float', 'Boolean': 'bool',
        'Date': 'date', 'DateTime': 'datetime', 'LocalTime': 'time', 'Point': 'Any', 
        'StringArray': 'List[str]', 'LongArray': 'List[int]',
        'DoubleArray': 'List[float]', 'BooleanArray': 'List[bool]'
    }
    return mapping.get(neo4j_type, 'Any')

def get_neo4j_schema(driver):
    schema = {}
    with driver.session() as session:
        # 1. Grab all exact labels
        labels_result = session.run("CALL db.labels() YIELD label RETURN label")
        for record in labels_result:
            schema[record["label"]] = {}
            
        # 2. Grab properties via schema introspection
        try:
            schema_result = session.run("""
                CALL db.schema.nodeTypeProperties() 
                YIELD nodeLabels, propertyName, propertyTypes
            """)
            
            for record in schema_result:
                labels = record.get("nodeLabels", [])
                prop_name = record.get("propertyName")
                prop_types = record.get("propertyTypes", [])
                
                if not prop_name:
                    continue 
                    
                python_type = map_db_schema_type(prop_types)
                for label in labels:
                    if label not in schema:
                        schema[label] = {}
                    schema[label][prop_name] = python_type
        except Exception as e:
            print(f"Warning: Could not fetch exact schema ({e}).")

    return schema

def generate_orm():
    print(f"Connecting to Neo4j at {URI}...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        driver.verify_connectivity()
        print("Connected. Inspecting full schema...")
        schema = get_neo4j_schema(driver)
    finally:
        driver.close()
    
    print(f"Found {len(schema)} node labels. Generating files...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "__init__.py"), "w") as f:
        f.write("# Auto-generated Neo4j ORM Models\n")
        f.write("from .base_model import Neo4jBaseModel\n")
        
    base_model_path = os.path.join(OUTPUT_DIR, "base_model.py")
    with open(base_model_path, "w") as f:
        f.write(BASE_MODEL_TEMPLATE)
        
    for label, properties in schema.items():
        # Using the new, safe-but-accurate naming rules:
        class_name = sanitize_class_name(label)
        module_name = sanitize_module_name(label)
        
        file_name = f"{module_name}.py"
        file_path = os.path.join(OUTPUT_DIR, file_name)
        
        seen_props = set()
        prop_lines = []
        
        for prop_name, prop_type in properties.items():
            safe_prop_name = sanitize_class_name(prop_name).lower()
            
            original_safe = safe_prop_name
            counter = 1
            while safe_prop_name in seen_props:
                safe_prop_name = f"{original_safe}_{counter}"
                counter += 1
            seen_props.add(safe_prop_name)
            
            if safe_prop_name != prop_name:
                escaped_prop_name = prop_name.replace('"', '\\"')
                prop_lines.append(f"    {safe_prop_name}: Optional[{prop_type}] = Field(default=None, alias=\"{escaped_prop_name}\")")
            else:
                prop_lines.append(f"    {safe_prop_name}: Optional[{prop_type}] = None")
            
        if not prop_lines:
            prop_lines.append("    pass")
            
        properties_str = "\n".join(prop_lines)
        
        class_content = CLASS_TEMPLATE.format(
            class_name=class_name, 
            original_label=label.replace('"', '\\"'),
            properties=properties_str
        )
        
        with open(file_path, "w") as f:
            f.write(class_content)
            
        with open(os.path.join(OUTPUT_DIR, "__init__.py"), "a") as f:
            f.write(f"from .{module_name} import {class_name}\n")
            
    print(f"Success! Models generated in {OUTPUT_DIR}")

if __name__ == "__main__":
    generate_orm()