from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneOntology_Header(Neo4jBaseModel):
    __label__ = "GeneOntology_Header"
    __id: Optional[int] = None
    property_values: Optional[List[str]] = None
    ontology: Optional[str] = None
    format_version: Optional[str] = None
    data_version: Optional[List[str]] = None
    default_namespace: Optional[str] = None
