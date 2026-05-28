from typing import Optional
from pydantic import Field
from .base_model import Neo4jBaseModel

class KEGG_Module(Neo4jBaseModel):
    __label__ = "KEGG_Module"
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")

class KEGG_Reaction(Neo4jBaseModel):
    __label__ = "KEGG_Reaction"
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")

class KEGG_Pathway(Neo4jBaseModel):
    __label__ = "KEGG_Pathway"
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")

class KEGG_Enzyme(Neo4jBaseModel):
    __label__ = "KEGG_Enzyme"
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")
