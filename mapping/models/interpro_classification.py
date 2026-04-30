from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterPro_Classification(Neo4jBaseModel):
    __label__ = "InterPro_Classification"
    __id: Optional[int] = None
    description: Optional[str] = None
    id: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
