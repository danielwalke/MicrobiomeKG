from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniProt_Organism(Neo4jBaseModel):
    __label__ = "UniProt_Organism"
    __id: Optional[int] = None
    id: Optional[str] = None
    db_references: Optional[List[str]] = None
    common_names: Optional[List[str]] = None
    scientific_names: Optional[List[str]] = None
    lineage: Optional[List[str]] = None
    synonym_names: Optional[List[str]] = None
