from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneontologyTerm(Neo4jBaseModel):
    __label__ = "GeneOntology_Term"
    def_: Optional[str] = Field(default=None, alias="def")
    __id: Optional[int] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    id: Optional[str] = None
    property_values: Optional[list] = None
    obsolete: Optional[bool] = None
    comment: Optional[str] = None
    alt_ids: Optional[list] = None
    xrefs: Optional[list] = None
    creation_date: Optional[str] = None
    created_by: Optional[str] = None
    subsets: Optional[list] = None
