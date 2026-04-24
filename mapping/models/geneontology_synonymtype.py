from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneontologySynonymtype(Neo4jBaseModel):
    __label__ = "GeneOntology_SynonymType"
    __id: Optional[int] = None
    description: Optional[str] = None
    id: Optional[str] = None
    scope: Optional[str] = None
