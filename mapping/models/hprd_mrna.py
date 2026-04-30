from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HPRD_mRNA(Neo4jBaseModel):
    __label__ = "HPRD_mRNA"
    __id: Optional[int] = None
    refseq_id: Optional[str] = None
    sequence: Optional[str] = None
