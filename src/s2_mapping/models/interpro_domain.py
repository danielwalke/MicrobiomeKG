from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterPro_Domain(Neo4jBaseModel):
    __label__ = "InterPro_Domain"
    __id: Optional[int] = None
    id: Optional[str] = None
    short_name: Optional[str] = None
    members: Optional[List[str]] = None
    members_names: Optional[List[str]] = None
    external_docs: Optional[List[str]] = None
    structure_db_links: Optional[List[str]] = None
    members_protein_counts: Optional[Any] = None
    key_species: Optional[List[str]] = None
    key_species_protein_counts: Optional[Any] = None
    protein_count: Optional[Any] = None
    key_species_ncbi_taxids: Optional[Any] = None
    name: Optional[str] = None
