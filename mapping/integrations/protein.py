from pydantic import Field
from typing import List
from mapping.models import UniprotProtein, HprdProtein, Protein
from mapping.integrations.base_merged import BaseMergedEntity

class MergedProtein(BaseMergedEntity):
    __label__ = "MergedProtein"
    __source_mappings__ = {
        "accessions": (UniprotProtein, "accession"),
        "protein_ids": (Protein, "ids"),
        "genebank_ids": (HprdProtein, "refseq_id")
    }

    accessions: List[str] = Field(default_factory=list)
    protein_ids: List[str] = Field(default_factory=list)
    genebank_ids: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        if orm_class == UniprotProtein and prop_name == "accession":
            return f"UniProtKB:{val_str}"
        if orm_class == HprdProtein and prop_name == "refseq_id":
            return f"Genbank:{val_str.split('.')[0]}"
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.accessions:
            self.accessions = [f"UniProtKB:{id}" for id in self.accessions if id is not None]
        if self.protein_ids:
            self.protein_ids = [f"Protein:{id}" for id in self.protein_ids if id is not None]
        if self.genebank_ids:
            self.genebank_ids = [f"Genbank:{id.split('.')[0]}" for id in self.genebank_ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.accessions)
        unique_ids.update(self.protein_ids)
        unique_ids.update(self.genebank_ids)
        self.merged_ids = list(unique_ids)