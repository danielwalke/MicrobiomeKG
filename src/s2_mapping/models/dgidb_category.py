from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class DGIdb_Category(Neo4jBaseModel):
    __label__ = "DGIdb_Category"
    __id: Optional[int] = None
    name: Optional[str] = None
