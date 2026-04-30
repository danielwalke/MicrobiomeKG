from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HPRD_Gene(Neo4jBaseModel):
    __label__ = "HPRD_Gene"
    __id: Optional[int] = None
    id: Optional[str] = None
    swissprot_id: Optional[List[str]] = None
    omim_id: Optional[Any] = None
    entrez_gene_id: Optional[Any] = None
    symbol: Optional[str] = None
    name: Optional[str] = None
