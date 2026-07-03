from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HPRD_Protein(Neo4jBaseModel):
    __label__ = "HPRD_Protein"
    __id: Optional[int] = None
    id: Optional[str] = None
    length: Optional[Any] = None
    refseq_id: Optional[str] = None
    sequence: Optional[str] = None
    molecular_weight: Optional[str] = None
