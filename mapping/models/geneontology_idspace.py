from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneOntology_Idspace(Neo4jBaseModel):
    __label__ = "GeneOntology_Idspace"
    __id: Optional[int] = None
    id: Optional[str] = None
    iri: Optional[str] = None
