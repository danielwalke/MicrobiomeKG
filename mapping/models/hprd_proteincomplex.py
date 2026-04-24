from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HprdProteincomplex(Neo4jBaseModel):
    __label__ = "HPRD_ProteinComplex"
    __id: Optional[int] = None
    id: Optional[str] = None
