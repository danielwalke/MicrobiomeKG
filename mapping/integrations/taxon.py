from pydantic import Field
from typing import List
from mapping.models import UniprotOrganism, Taxon
from mapping.integrations.base_merged import BaseMergedEntity

class MergedTaxon(BaseMergedEntity):
    __label__ = "MergedTaxon"
    __source_mappings__ = {
        "ncbi_ids": (UniprotOrganism, "db_references"),
        "taxon_ids": (Taxon, "ids")
    }

    ncbi_ids: List[str] = Field(default_factory=list)
    taxon_ids: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        if orm_class == UniprotOrganism and prop_name == "db_references":
            return f"{val_str}".replace("NCBI Taxonomy:", "NCBITaxon:")
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.ncbi_ids:
            self.ncbi_ids = [f"{id.replace('NCBI Taxonomy:', 'NCBITaxon:')}" for id in self.ncbi_ids if id is not None]
        if self.taxon_ids:
            self.taxon_ids = [f"{id}" for id in self.taxon_ids if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.ncbi_ids)
        unique_ids.update(self.taxon_ids)
        self.merged_ids = list(unique_ids)