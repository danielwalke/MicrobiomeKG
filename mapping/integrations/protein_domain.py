from pydantic import Field
from typing import List
from mapping.models import InterPro_Domain, HPRD_Domain
from mapping.integrations.base_merged import BaseMergedEntity

class MergedProteinDomain(BaseMergedEntity):
    __label__ = "PROTEIN_DOMAIN"
    __source_mappings__ = {
        "members_names": (InterPro_Domain, "members_names"),
        "member_ids": (InterPro_Domain, "members"),
        "hprd_names": (HPRD_Domain, "name")
    }

    members_names: List[str] = Field(default_factory=list)
    member_ids: List[str] = Field(default_factory=list)
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
        if self.members_names:
            self.members_names = [str(id) for id in self.members_names if id is not None]
        if self.member_ids:
            self.member_ids = [str(id) for id in self.member_ids if id is not None]
        if self.hprd_names:
            self.hprd_names = [str(id) for id in self.hprd_names if id is not None]

    def integrate(self):
        unique_ids = set()
        unique_ids.update(self.members_names)
        unique_ids.update(self.member_ids)
        unique_ids.update(self.hprd_names)
        self.merged_ids = list(unique_ids)