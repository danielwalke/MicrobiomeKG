from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneontologyIdspace(Neo4jBaseModel):
    __label__ = "GeneOntology_Idspace"
    iri: Optional[str] = None
    __id: Optional[int] = None
    id: Optional[str] = None
