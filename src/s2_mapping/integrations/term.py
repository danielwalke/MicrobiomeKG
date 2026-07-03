from pydantic import Field
from typing import List
from src.s2_mapping.models import InterPro_Classification, GeneOntology_Term, DiseaseOntology_Term
from src.s2_mapping.integrations.base_merged import BaseMergedEntity
from src.s2_mapping.models.dgidb_category import DGIdb_Category

class MergedTerm(BaseMergedEntity):
    __label__ = "TERM"
    __source_mappings__ = {
        "interpro_ids": (InterPro_Classification, "id"),
        "go_ids": (GeneOntology_Term, "id"),
        "diseaseontology_ids": (DiseaseOntology_Term, "id"),
        "dgib_categories": (DGIdb_Category, "name")
    }

    interpro_ids: List[str] = Field(default_factory=list)
    go_ids: List[str] = Field(default_factory=list)
    diseaseontology_ids: List[str] = Field(default_factory=list)
    dgib_categories: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """Ensure Resolver sees '12345' and 'PubMed:12345' as the same string."""
        val_str = str(raw_val)
        if orm_class == InterPro_Classification and prop_name == "id":
            return f"{val_str}"
        if orm_class == GeneOntology_Term and prop_name == "id":
            return f"{val_str}"
        if orm_class == DiseaseOntology_Term and prop_name == "id":
            return f"{val_str}"
        if orm_class == DGIdb_Category and prop_name == "name":
            return f"{val_str}"
        return val_str

    def preprocess(self):
        """The actual processing logic that runs inside the Integrator."""
        if self.interpro_ids:
            self.interpro_ids = [f"{id}" for id in self.interpro_ids if id is not None]
        if self.go_ids:
            self.go_ids = [f"{id}" for id in self.go_ids if id is not None]
        if self.diseaseontology_ids:
            self.diseaseontology_ids = [f"{id}" for id in self.diseaseontology_ids if id is not None]
        if self.dgib_categories:
            self.dgib_categories = [f"{id}" for id in self.dgib_categories if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.interpro_ids)
        unique_ids.update(self.go_ids)
        unique_ids.update(self.diseaseontology_ids)
        unique_ids.update(self.dgib_categories)
        self.merged_ids = list(unique_ids)