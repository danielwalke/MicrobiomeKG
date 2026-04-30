from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class RNAInter_HistoneModification(Neo4jBaseModel):
    __label__ = "RNAInter_HistoneModification"
    __id: Optional[int] = None
    symbol: Optional[str] = None
