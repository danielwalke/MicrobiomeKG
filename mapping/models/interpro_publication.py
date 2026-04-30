from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterPro_Publication(Neo4jBaseModel):
    __label__ = "InterPro_Publication"
    __id: Optional[int] = None
    id: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    volume: Optional[str] = None
    journal: Optional[str] = None
    pages: Optional[str] = None
    pmid: Optional[Any] = None
    issue: Optional[str] = None
    year: Optional[Any] = None
