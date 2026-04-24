from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterproClassification(Neo4jBaseModel):
    __label__ = "InterPro_Classification"
    __id: Optional[int] = None
    description: Optional[str] = None
    id: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
