from mapping.linking.base_edge import BaseEdgeDefinition

RELATIONSHIP_LABEL = "HAS_ONTOLOGY"
class HasOntologyEdge(BaseEdgeDefinition):
    # Just define the config at the class level
    source_label = "DISEASE"
    source_property = "ids"
    target_label = "DiseaseOntology_Term"
    target_property = "id"
    relationship_label = RELATIONSHIP_LABEL

    def standardize_source(self, raw_val):
        val_str = str(raw_val)
        if not val_str:
            return ""
        return f"{val_str}"

    def standardize_target(self, raw_val):
        """
        Target is already clean? Great, just return the string.
        (Or override if it also needs cleaning).
        """
        return str(raw_val)
    