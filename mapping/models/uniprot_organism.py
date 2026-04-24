from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniprotOrganism(Neo4jBaseModel):
    __label__ = "UniProt_Organism"
    lineage: Optional[list] = None
    scientific_names: Optional[list] = None
    db_references: Optional[list] = None
    __id: Optional[int] = None
    common_names: Optional[list] = None
    id: Optional[str] = None
    synonym_names: Optional[list] = None
