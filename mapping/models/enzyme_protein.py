from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class ENZYME_Protein(Neo4jBaseModel):
    __label__ = "ENZYME_Protein"
    __id: Optional[int] = None
    accession: Optional[str] = None
    name: Optional[str] = None
