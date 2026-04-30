from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneOntology_Typedef(Neo4jBaseModel):
    __label__ = "GeneOntology_Typedef"
    __id: Optional[int] = None
    id: Optional[str] = None
    namespace: Optional[str] = None
    is_class_level: Optional[bool] = None
    is_transitive: Optional[bool] = None
    xrefs: Optional[List[str]] = None
    is_metadata_tag: Optional[bool] = None
    name: Optional[str] = None
