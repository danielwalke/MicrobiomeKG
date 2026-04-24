from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniprotProtein(Neo4jBaseModel):
    __label__ = "UniProt_Protein"
    sequence_checksum: Optional[str] = None
    created: Optional[str] = None
    existence: Optional[str] = None
    sequence_length: Optional[int] = None
    secondary_accessions: Optional[list] = None
    accession: Optional[str] = None
    version: Optional[int] = None
    sequence: Optional[str] = None
    names: Optional[list] = None
    db_references: Optional[list] = None
    sequence_mass: Optional[int] = None
    __id: Optional[int] = None
    protein_recommended_name_full: Optional[str] = None
    modified: Optional[str] = None
    dataset: Optional[str] = None
    sequence_modified: Optional[str] = None
    sequence_version: Optional[int] = None
    keywords: Optional[list] = None
    keyword_ids: Optional[list] = None
    sequence_precursor: Optional[bool] = None
    protein_recommended_name_short: Optional[list] = None
    protein_recommended_name_ec_numbers: Optional[list] = None
    sequence_fragment: Optional[str] = None
