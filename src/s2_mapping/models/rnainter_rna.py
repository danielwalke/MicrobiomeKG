from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class RNAInter_RNA(Neo4jBaseModel):
    __label__ = "RNAInter_RNA"
    __id: Optional[int] = None
    id: Optional[str] = None
    type: Optional[str] = None
    species: Optional[str] = None
    symbol: Optional[str] = None
