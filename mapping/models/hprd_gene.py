from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class HprdGene(Neo4jBaseModel):
    __label__ = "HPRD_Gene"
    entrez_gene_id: Optional[int] = None
    symbol: Optional[str] = None
    omim_id: Optional[int] = None
    __id: Optional[int] = None
    name: Optional[str] = None
    swissprot_id: Optional[list] = None
    id: Optional[str] = None
