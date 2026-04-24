from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HprdPosttranslationalmodification(Neo4jBaseModel):
    __label__ = "HPRD_PostTranslationalModification"
    pubmed_ids: Optional[list] = None
    site: Optional[str] = None
    __id: Optional[int] = None
    type: Optional[str] = None
    residue: Optional[str] = None
    experiment_types: Optional[list] = None
