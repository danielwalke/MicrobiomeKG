from pydantic import Field
from typing import List
from mapping.models import Rna, HprdMrna
from mapping.integrations.base_merged import BaseMergedEntity

class MergedRna(BaseMergedEntity):
    __label__ = "MergedRna"
    __source_mappings__ = {
        "genbank_ids": (HprdMrna, "refseq_id"),
        "rna_ids": (Rna, "ids")
    }

    genbank_ids: List[str] = Field(default_factory=list)
    rna_ids: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        if orm_class == HprdMrna and prop_name == "refseq_id":
            return f"Genbank:{val_str.split('.')[0]}"
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.genbank_ids:
            self.genbank_ids = [f"Genbank:{id.split('.')[0]}" for id in self.genbank_ids if id is not None]
        if self.rna_ids:
            self.rna_ids = [str(id) for id in self.rna_ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.genbank_ids)
        unique_ids.update(self.rna_ids)
        self.merged_ids = list(unique_ids)