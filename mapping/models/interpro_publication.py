from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterproPublication(Neo4jBaseModel):
    __label__ = "InterPro_Publication"
    volume: Optional[str] = None
    pages: Optional[str] = None
    journal: Optional[str] = None
    issue: Optional[str] = None
    year: Optional[int] = None
    __id: Optional[int] = None
    id: Optional[str] = None
    pmid: Optional[int] = None
    title: Optional[str] = None
    authors: Optional[str] = None
