from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterproActivesite(Neo4jBaseModel):
    __label__ = "InterPro_ActiveSite"
    external_docs: Optional[list] = None
    structure_db_links: Optional[list] = None
    members: Optional[list] = None
    __id: Optional[int] = None
    protein_count: Optional[int] = None
    name: Optional[str] = None
    members_names: Optional[list] = None
    short_name: Optional[str] = None
    id: Optional[str] = None
    members_protein_counts: Optional[list] = None
    key_species_ncbi_taxids: Optional[list] = None
    key_species_protein_counts: Optional[list] = None
    key_species: Optional[list] = None
