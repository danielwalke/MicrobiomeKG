from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniprotFeature(Neo4jBaseModel):
    __label__ = "UniProt_Feature"
    __id: Optional[int] = None
    description: Optional[str] = None
    location_begin: Optional[int] = None
    location_end: Optional[int] = None
    id: Optional[str] = None
    type: Optional[str] = None
    location_position: Optional[int] = None
