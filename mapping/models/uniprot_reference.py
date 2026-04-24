from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniprotReference(Neo4jBaseModel):
    __label__ = "UniProt_Reference"
    __id: Optional[int] = None
    scopes: Optional[list] = None
    key: Optional[int] = None
