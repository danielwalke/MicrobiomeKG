from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterproDbinfo(Neo4jBaseModel):
    __label__ = "InterPro_DBInfo"
    file_date: Optional[str] = None
    entry_count: Optional[int] = None
    __id: Optional[int] = None
    name: Optional[str] = None
    version: Optional[str] = None
