from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniProt_Reference(Neo4jBaseModel):
    __label__ = "UniProt_Reference"
    __id: Optional[int] = None
    key: Optional[Any] = None
    scopes: Optional[List[str]] = None
