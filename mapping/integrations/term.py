from pydantic import Field
from typing import List
from mapping.models import InterproClassification, GeneontologyTerm
from mapping.integrations.base_merged import BaseMergedEntity

class MergedTerm(BaseMergedEntity):
    __label__ = "MergedTerm"
    __source_mappings__ = {
        "interpro_ids": (InterproClassification, "id"),
        "go_ids": (GeneontologyTerm, "id")
    }

    interpro_ids: List[str] = Field(default_factory=list)
    go_ids: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        if orm_class == InterproClassification and prop_name == "id":
            return f"{val_str}"
        if orm_class == GeneontologyTerm and prop_name == "id":
            return f"{val_str}"
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.interpro_ids:
            self.interpro_ids = [f"{id}" for id in self.interpro_ids if id is not None]
        if self.go_ids:
            self.go_ids = [f"{id}" for id in self.go_ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.interpro_ids)
        unique_ids.update(self.go_ids)
        self.merged_ids = list(unique_ids)