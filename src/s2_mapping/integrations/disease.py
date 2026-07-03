from pydantic import Field
from typing import List
from src.s2_mapping.models import HPRD_Disease, DISEASES_Disease
from src.s2_mapping.integrations.base_merged import BaseMergedEntity

class MergedDisease(BaseMergedEntity):
    __label__ = "DISEASE"
    __source_mappings__ = {
        "hprd_names": (HPRD_Disease, "name"),
        "diseases_names": (DISEASES_Disease, "name")
    }

    hprd_names: List[str] = Field(default_factory=list)
    diseases_names: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.hprd_names:
            self.hprd_names = [f"{id}" for id in self.hprd_names if id is not None]
        if self.diseases_names:
            self.diseases_names = [f"{id}" for id in self.diseases_names if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.hprd_names)
        unique_ids.update(self.diseases_names)
        self.merged_ids = list(unique_ids)