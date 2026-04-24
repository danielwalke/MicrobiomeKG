from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class Rna(Neo4jBaseModel):
    __label__ = "RNA"
    names: Optional[list] = None
    __id: Optional[int] = None
    __mapped: Optional[bool] = None
    ids: Optional[list] = None
    rna_type: Optional[str] = None
