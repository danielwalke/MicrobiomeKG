from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class Publication(Neo4jBaseModel):
    __label__ = "PUBLICATION"
    names: Optional[list] = None
    __id: Optional[int] = None
    __mapped: Optional[bool] = None
    ids: Optional[list] = None
    pmid: Optional[int] = None
