from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneOntology_Subset(Neo4jBaseModel):
    __label__ = "GeneOntology_Subset"
    __id: Optional[int] = None
    description: Optional[str] = None
    id: Optional[str] = None
