from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class UniProt_Protein(Neo4jBaseModel):
    __label__ = "UniProt_Protein"
    names: Optional[List[str]] = None
    __id: Optional[int] = None
    db_references: Optional[List[str]] = None
    version: Optional[Any] = None
    keywords: Optional[List[str]] = None
    keyword_ids: Optional[List[str]] = None
    protein_recommended_name_short: Optional[List[str]] = None
    protein_recommended_name_full: Optional[str] = None
    sequence_modified: Optional[str] = None
    dataset: Optional[str] = None
    sequence_version: Optional[Any] = None
    existence: Optional[str] = None
    sequence: Optional[str] = None
    secondary_accessions: Optional[List[str]] = None
    modified: Optional[str] = None
    accession: Optional[str] = None
    created: Optional[str] = None
    sequence_length: Optional[Any] = None
    sequence_checksum: Optional[str] = None
    sequence_mass: Optional[Any] = None
    sequence_fragment: Optional[str] = None
    protein_recommended_name_ec_numbers: Optional[List[str]] = None
    sequence_precursor: Optional[bool] = None
