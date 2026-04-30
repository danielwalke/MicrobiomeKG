from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class RNA(Neo4jBaseModel):
    __label__ = "RNA"
    names: Optional[List[str]] = None
    __id: Optional[int] = None
    __mapped: Optional[bool] = None
    ids: Optional[List[str]] = None
    rna_type: Optional[str] = None
