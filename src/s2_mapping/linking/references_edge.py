from src.s2_mapping.linking.base_edge import BaseEdgeDefinition

RELATIONSHIP_LABEL = "REFERENCES"
class ReferencesPTMEdge(BaseEdgeDefinition):
    # Just define the config at the class level
    source_label = "HPRD_PostTranslationalModification"
    source_property = "pubmed_ids"
    target_label = "MergedPublication"
    target_property = "merged_ids"
    relationship_label = RELATIONSHIP_LABEL

    def standardize_source(self, raw_val):
        """
        Your custom logic for HPRD RefSeq. 
        Put whatever 50-line disaster you need in here.
        """
        val_str = str(raw_val)
        if not val_str:
            return ""
        return f"PMID:{val_str.split('.')[0]}"

    def standardize_target(self, raw_val):
        """
        Target is already clean? Great, just return the string.
        (Or override if it also needs cleaning).
        """
        return str(raw_val)
    



# Add as many edge classes as you need in other files...
##TODO Add more connections and test code