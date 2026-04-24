from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HprdMrna(Neo4jBaseModel):
    __label__ = "HPRD_mRNA"
    sequence: Optional[str] = None
    refseq_id: Optional[str] = None
    __id: Optional[int] = None
