from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterPro_DBInfo(Neo4jBaseModel):
    __label__ = "InterPro_DBInfo"
    __id: Optional[int] = None
    version: Optional[str] = None
    entry_count: Optional[Any] = None
    name: Optional[str] = None
    file_date: Optional[str] = None
