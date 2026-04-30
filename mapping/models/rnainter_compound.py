from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class RNAInter_Compound(Neo4jBaseModel):
    __label__ = "RNAInter_Compound"
    __id: Optional[int] = None
    id: Optional[str] = None
    name: Optional[str] = None
