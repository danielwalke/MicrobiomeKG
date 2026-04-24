from pydantic import Field
from typing import List
from mapping.models import Publication, InterproPublication, UniprotCitation
from mapping.integrations.base_merged import BaseMergedEntity

class MergedPublication(BaseMergedEntity):
    __label__ = "MergedPublication"
    __source_mappings__ = {
        "interpro_pmids": (InterproPublication, "pmid"),
        "uniprot_refs": (UniprotCitation, "db_references"),
        "pub_ids": (Publication, "ids")
    }

    interpro_pmids: List[int] = Field(default_factory=list)
    uniprot_refs: List[str] = Field(default_factory=list)
    pub_ids: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        if orm_class == InterproPublication and prop_name == "pmid":
            return f"PMID:{val_str}"
        if orm_class == UniprotCitation and prop_name == "db_references":
            return val_str.replace("PubMed:", "PMID:")
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.interpro_pmids:
            self.interpro_pmids = [f"PMID:{p}" for p in self.interpro_pmids if p is not None]
        if self.uniprot_refs:
            self.uniprot_refs = [r.replace("PubMed:", "PMID:") for r in self.uniprot_refs if r is not None]
        if self.pub_ids:
            self.pub_ids = [str(p) for p in self.pub_ids if p is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.interpro_pmids)
        unique_ids.update(self.uniprot_refs)
        unique_ids.update(self.pub_ids)
        self.merged_ids = list(unique_ids)