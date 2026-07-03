from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HPRD_PostTranslationalModification(Neo4jBaseModel):
    __label__ = "HPRD_PostTranslationalModification"
    __id: Optional[int] = None
    type: Optional[str] = None
    experiment_types: Optional[List[str]] = None
    residue: Optional[str] = None
    site: Optional[str] = None
    pubmed_ids: Optional[Any] = None
