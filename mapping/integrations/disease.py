from pydantic import Field
from typing import List
from mapping.models import HprdDisease
from mapping.integrations.base_merged import BaseMergedEntity

class MergedDisease(BaseMergedEntity):
    __label__ = "MergedDisease"
    __source_mappings__ = {
        "hprd_names": (HprdDisease, "name"),
    }

    hprd_names: List[str] = Field(default_factory=list)

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

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.hprd_names)
        self.merged_ids = list(unique_ids)