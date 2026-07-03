from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class DGIdb_Drug(Neo4jBaseModel):
    __label__ = "DGIdb_Drug"
    __id: Optional[int] = None
    id: Optional[str] = None
    primary_drug_names: Optional[List[str]] = None
    drugs_at_fda_id: Optional[str] = None
    primary_name: Optional[str] = None
    sources: Optional[List[str]] = None
    primary_drug_name: Optional[str] = None
    primary_names: Optional[List[str]] = None
    name: Optional[str] = None
    drugs_at_fda_ids: Optional[List[str]] = None
