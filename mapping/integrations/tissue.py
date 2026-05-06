from pydantic import Field
from typing import List
from mapping.models import HPRD_Tissue
from mapping.integrations.base_merged import BaseMergedEntity

class MergedTissue(BaseMergedEntity):
    __label__ = "TISSUE"
    __source_mappings__ = {
        "tissue_names": (HPRD_Tissue, "name")
    }

    tissue_names: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.tissue_names:
            self.tissue_names = [f"{id}" for id in self.tissue_names if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.tissue_names)
        self.merged_ids = list(unique_ids)