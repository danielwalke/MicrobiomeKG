from pydantic import BaseModel, ConfigDict
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
        """Find nodes matching the exact kwargs properties."""
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
        """Saves the current Pydantic model to Neo4j."""
        label = self._get_label()
        # by_alias=True ensures we save it back to Neo4j with its original database name
        props = self.model_dump(exclude_none=True, by_alias=True)
        
        query = f"CREATE (n:`{label}`) SET n = $props RETURN n"
        with driver.session() as session:
            session.run(query, props=props)
        return self

    @classmethod
    def get_samples(cls: Type[T], limit: int = 10) -> List[T]:
        """Extracts a specific number of complete entity records for this node label."""
        label = cls._get_label()
        query = f"MATCH (n:`{label}`) RETURN n LIMIT $limit"
        
        with driver.session() as session:
            result = session.run(query, limit=limit)
            return [cls(**record["n"]) for record in result]

    @classmethod
    def get_property_examples(cls, property_name: str, limit: int = 5) -> List[Any]:
        """Extracts a specific number of distinct examples for a specific property."""
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
