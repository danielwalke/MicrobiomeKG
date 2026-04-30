from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class DiseaseOntology_Header(Neo4jBaseModel):
    __label__ = "DiseaseOntology_Header"
    __id: Optional[int] = None
    date: Optional[str] = None
    remarks: Optional[List[str]] = None
    property_values: Optional[List[str]] = None
    format_version: Optional[str] = None
    ontology: Optional[str] = None
    data_version: Optional[List[str]] = None
    saved_by: Optional[str] = None
    default_namespace: Optional[str] = None
