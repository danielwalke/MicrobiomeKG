from pydantic import Field
from typing import List
from src.s2_mapping.models.kegg_models import KEGG_Module, KEGG_Reaction, KEGG_Pathway, KEGG_Enzyme
from src.s2_mapping.integrations.base_merged import BaseMergedEntity

class MergedModule(BaseMergedEntity):
    __label__ = "MODULE"
    __source_mappings__ = {
        "ids": (KEGG_Module, "id")
    }

    ids: List[str] = Field(default_factory=list)
    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        return str(raw_val)

    def preprocess(self):
        if self.ids:
            self.ids = [f"{id}" for id in self.ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.ids)
        self.merged_ids = list(unique_ids)

class MergedReaction(BaseMergedEntity):
    __label__ = "REACTION"
    __source_mappings__ = {
        "ids": (KEGG_Reaction, "id")
    }

    ids: List[str] = Field(default_factory=list)
    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        return str(raw_val)

    def preprocess(self):
        if self.ids:
            self.ids = [f"{id}" for id in self.ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.ids)
        self.merged_ids = list(unique_ids)

class MergedPathway(BaseMergedEntity):
    __label__ = "PATHWAY"
    __source_mappings__ = {
        "ids": (KEGG_Pathway, "id")
    }

    ids: List[str] = Field(default_factory=list)
    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        return str(raw_val)

    def preprocess(self):
        if self.ids:
            self.ids = [f"{id}" for id in self.ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.ids)
        self.merged_ids = list(unique_ids)

class MergedEnzyme(BaseMergedEntity):
    __label__ = "ENZYME"
    __source_mappings__ = {
        "ids": (KEGG_Enzyme, "id")
    }

    ids: List[str] = Field(default_factory=list)
    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        return str(raw_val)

    def preprocess(self):
        if self.ids:
            self.ids = [f"{id}" for id in self.ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.ids)
        self.merged_ids = list(unique_ids)
