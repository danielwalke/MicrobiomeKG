from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class ProteinDomain(Neo4jBaseModel):
    __label__ = "PROTEIN_DOMAIN"
    names: Optional[list] = None
    __id: Optional[int] = None
    __mapped: Optional[bool] = None
    ids: Optional[list] = None
