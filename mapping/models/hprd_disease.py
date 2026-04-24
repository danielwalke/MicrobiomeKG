from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HprdDisease(Neo4jBaseModel):
    __label__ = "HPRD_Disease"
    __id: Optional[int] = None
    name: Optional[str] = None
