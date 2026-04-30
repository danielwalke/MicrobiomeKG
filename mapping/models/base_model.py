from pydantic import BaseModel, ConfigDict
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
