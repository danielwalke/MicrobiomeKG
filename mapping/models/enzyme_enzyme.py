from typing import Optional, Any, List
from datetime import date, datetime, time
from pydantic import Field
from .base_model import Neo4jBaseModel

class ENZYME_Enzyme(Neo4jBaseModel):
    __label__ = "ENZYME_Enzyme"
    __id: Optional[int] = None
    id: Optional[str] = None
    comments: Optional[List[str]] = None
    alternative_names: Optional[List[str]] = None
    official_name: Optional[str] = None
    catalyticactivities: Optional[List[str]] = Field(default=None, alias="catalyticActivities")
