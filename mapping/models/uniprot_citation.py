from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniprotCitation(Neo4jBaseModel):
    __label__ = "UniProt_Citation"
    date: Optional[str] = None
    db_references: Optional[list] = None
    __id: Optional[int] = None
    type: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[list] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    journal: Optional[str] = None
    locator: Optional[str] = None
