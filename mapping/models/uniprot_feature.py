from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniProt_Feature(Neo4jBaseModel):
    __label__ = "UniProt_Feature"
    __id: Optional[int] = None
    description: Optional[str] = None
    id: Optional[str] = None
    type: Optional[str] = None
    location_end: Optional[int] = None
    location_sequence: Optional[str] = None
    location_begin: Optional[int] = None
    location_position: Optional[int] = None
