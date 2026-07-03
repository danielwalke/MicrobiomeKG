class BaseEdgeDefinition:
    """
    Inherit from this class for every specific edge you want to create.
    Override the attributes and standardization methods as needed.
    """
    source_label: str = None
    source_property: str = None
    target_label: str = None
    target_property: str = None
    relationship_label: str = None

    def __init__(self):
        # I'm strictly checking this so you don't pass empty configs
        required = [
            "source_label", "source_property", 
            "target_label", "target_property", 
            "relationship_label"
        ]
        missing = [prop for prop in required if not getattr(self, prop)]
        if missing:
            raise ValueError(f"Class {self.__class__.__name__} is missing required attributes: {missing}")

    def standardize_source(self, raw_val) -> str:
        """Override this if your source data is messy."""
        return str(raw_val)

    def standardize_target(self, raw_val) -> str:
        """Override this if your target data is messy."""
        return str(raw_val)