from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HPRD_ProteinComplex(Neo4jBaseModel):
    __label__ = "HPRD_ProteinComplex"
    __id: Optional[int] = None
    id: Optional[str] = None
