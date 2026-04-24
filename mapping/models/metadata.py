from typing import Optional, Any
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class Metadata(Neo4jBaseModel):
    __label__ = "metadata"
    license: Optional[str] = None
    datasource_id: Optional[str] = None
    export_version: Optional[int] = None
    export_properties_hash: Optional[int] = None
    __id: Optional[int] = None
    type: Optional[str] = None
    datasource_oai_id: Optional[str] = None
    version: Optional[str] = None
