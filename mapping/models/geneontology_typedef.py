from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneontologyTypedef(Neo4jBaseModel):
    __label__ = "GeneOntology_Typedef"
    __id: Optional[int] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    xrefs: Optional[list] = None
    id: Optional[str] = None
    is_transitive: Optional[bool] = None
    is_class_level: Optional[bool] = None
    is_metadata_tag: Optional[bool] = None
