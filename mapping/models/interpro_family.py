from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class InterproFamily(Neo4jBaseModel):
    __label__ = "InterPro_Family"
    structure_db_links: Optional[list] = None
    members_names: Optional[list] = None
    external_docs: Optional[list] = None
    members: Optional[list] = None
    __id: Optional[int] = None
    protein_count: Optional[int] = None
    name: Optional[str] = None
    key_species_ncbi_taxids: Optional[list] = None
    key_species_protein_counts: Optional[list] = None
    short_name: Optional[str] = None
    id: Optional[str] = None
    key_species: Optional[list] = None
    members_protein_counts: Optional[list] = None
