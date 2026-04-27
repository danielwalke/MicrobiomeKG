from pydantic import Field
from typing import List
from mapping.models import HprdPosttranslationalmodification
from mapping.integrations.base_merged import BaseMergedEntity

class MergedPTM(BaseMergedEntity):
    __label__ = "MergedPTM"
    __source_mappings__ = {
        "ptm_ids": (HprdPosttranslationalmodification, "__id"),
    }

    ptm_ids: List[int] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.ptm_ids:
            self.ptm_ids = [f"{id}" for id in self.ptm_ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.ptm_ids)
        self.merged_ids = list(unique_ids)