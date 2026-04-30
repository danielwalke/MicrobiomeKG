from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class TAXON(Neo4jBaseModel):
    __label__ = "TAXON"
    names: Optional[List[str]] = None
    __id: Optional[int] = None
    __mapped: Optional[bool] = None
    ids: Optional[List[str]] = None
