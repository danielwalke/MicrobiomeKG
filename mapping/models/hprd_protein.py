from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HprdProtein(Neo4jBaseModel):
    __label__ = "HPRD_Protein"
    sequence: Optional[str] = None
    refseq_id: Optional[str] = None
    __id: Optional[int] = None
    length: Optional[int] = None
    id: Optional[str] = None
    molecular_weight: Optional[str] = None
