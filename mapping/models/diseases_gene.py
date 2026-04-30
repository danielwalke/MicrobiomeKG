from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class DISEASES_Gene(Neo4jBaseModel):
    __label__ = "DISEASES_Gene"
    __id: Optional[int] = None
    id: Optional[str] = None
    name: Optional[str] = None
