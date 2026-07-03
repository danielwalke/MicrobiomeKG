from pydantic import BaseModel, Field
from typing import Dict, Tuple, Type, List

class BaseMergedEntity(BaseModel):
    __label__: str = "BaseMerged"
    # Format: {"local_field_name": (ORMClass, "orm_property")}
    __source_mappings__: Dict[str, Tuple[Type[BaseModel], str]] = {}
    
    universal_id: str

    def preprocess(self): pass
    def integrate(self): pass

    @classmethod
    def standardize_id_for_resolver(cls, orm_class, prop_name, raw_val):
        """
        Hook used by the EntityResolver to ensure IDs from different sources
        look identical before attempting to group them.
        """
        return str(raw_val)

    def get_final_properties(self) -> dict:
        exclude_fields = set(self.__source_mappings__.keys())
        return self.model_dump(exclude=exclude_fields)

