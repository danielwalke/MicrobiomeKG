from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneOntology_Term(Neo4jBaseModel):
    __label__ = "GeneOntology_Term"
    __id: Optional[int] = None
    id: Optional[str] = None
    subsets: Optional[List[str]] = None
    created_by: Optional[str] = None
    alt_ids: Optional[List[str]] = None
    xrefs: Optional[List[str]] = None
    namespace: Optional[str] = None
    obsolete: Optional[bool] = None
    def_: Optional[str] = Field(default=None, alias="def")
    property_values: Optional[List[str]] = None
    comment: Optional[str] = None
    name: Optional[str] = None
    creation_date: Optional[str] = None
