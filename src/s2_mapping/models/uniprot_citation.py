from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniProt_Citation(Neo4jBaseModel):
    __label__ = "UniProt_Citation"
    __id: Optional[int] = None
    date: Optional[str] = None
    db_references: Optional[List[str]] = None
    title: Optional[str] = None
    type: Optional[str] = None
    authors: Optional[List[str]] = None
    volume: Optional[str] = None
    journal: Optional[str] = None
    pages: Optional[str] = None
    locator: Optional[str] = None
    city: Optional[str] = None
    publisher: Optional[str] = None
    editors: Optional[List[str]] = None
    country: Optional[str] = None
    institute: Optional[str] = None
    number: Optional[str] = None
