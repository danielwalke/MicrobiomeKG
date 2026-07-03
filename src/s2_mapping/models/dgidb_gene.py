from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class DGIdb_Gene(Neo4jBaseModel):
    __label__ = "DGIdb_Gene"
    __id: Optional[int] = None
    id: Optional[str] = None
    gene_symbol: Optional[str] = None
    ensembl_gene_id: Optional[str] = None
    ncbi_gene_name: Optional[str] = None
    uniprotkb_id: Optional[str] = None
    primary_gene_name: Optional[str] = None
    oncokb_gene_name: Optional[str] = None
    gene_name: Optional[str] = None
    sources: Optional[List[str]] = None
    name: Optional[str] = None
