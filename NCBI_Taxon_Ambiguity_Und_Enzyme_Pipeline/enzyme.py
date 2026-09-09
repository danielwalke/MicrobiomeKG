from pydantic import Field
from typing import List
from src.s2_mapping.models.kegg_models import  KEGG_Enzyme
from src.s2_mapping.models import  ENZYME_Enzyme, UniProt_Protein
from src.s2_mapping.integrations.base_merged import BaseMergedEntity


class MergedEnzymeTest(BaseMergedEntity):
    __label__ = "ENZYME"
    __source_mappings__ = {
        "ec_numer_kegg": (KEGG_Enzyme, "id"),
        "ec_nummer_enzyme":(ENZYME_Enzyme, "id" ),
        "ec_number_uniprot":(UniProt_Protein, "protein_recommended_name_ec_numbers")
    }

    ec_numbers_kegg: List[str] = Field(default_factory=list)
    ec_numbers_enzyme: List[str] = Field(default_factory=list)
    ec_numbers_uniprot: List[str] = Field(default_factory=list)

    mapped: bool = True
    merged_ids: List[str] = Field(default_factory=list)

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """ """
        print(f"{orm_class};{prop_name};{raw_val}")
        val_str= str(raw_val)
        if orm_class == KEGG_Enzyme and prop_name == "id":
            return f"{val_str}"
        if orm_class == ENZYME_Enzyme and prop_name == "id":
            return f"{val_str}"
        if orm_class == UniProt_Protein and prop_name == "protein_recommended_name_ec_numbers":
            return raw_val[0]
        return val_str

    def preprocess(self):
        if self.ec_numbers_kegg:
            self.ec_numbers_kegg = [f"{ec_number}" for ec_number in self.ec_numbers_kegg if id is not None]
        if self.ec_numbers_enzyme:
            self.ec_numbers_enzyme= [f"{ec_number}" for ec_number in self.ec_numbers_enzyme if id is not None]
        if self.ec_numbers_uniprot:
            self.ec_numbers_enzyme= [f"{ec_number}" for ec_number in self.ec_numbers_uniprot if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.ec_numbers_kegg)
        unique_ids.update(self.ec_numbers_enzyme)
        unique_ids.update(self.ec_numbers_uniprot)
        self.merged_ids = list(unique_ids)
        print(self.merged_ids)
