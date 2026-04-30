from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class DiseaseOntology_Typedef(Neo4jBaseModel):
    __label__ = "DiseaseOntology_Typedef"
    __id: Optional[int] = None
    id: Optional[str] = None
    def_: Optional[str] = Field(default=None, alias="def")
    name: Optional[str] = None
