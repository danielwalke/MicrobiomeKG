from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class GeneontologyHeader(Neo4jBaseModel):
    __label__ = "GeneOntology_Header"
    property_values: Optional[list] = None
    format_version: Optional[str] = None
    data_version: Optional[list] = None
    __id: Optional[int] = None
    default_namespace: Optional[str] = None
    ontology: Optional[str] = None
