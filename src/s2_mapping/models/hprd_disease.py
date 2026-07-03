from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HPRD_Disease(Neo4jBaseModel):
    __label__ = "HPRD_Disease"
    __id: Optional[int] = None
    name: Optional[str] = None
