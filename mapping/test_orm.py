import sys
sys.path.append("/mappings/")

from models import InterproFamily 
name_examples = InterproFamily.get_property_examples(property_name="name", limit=5)
print("Example Names:", name_examples) 


# ---------------------------------------------------------
# NEW FEATURE 2: Extract complete entities
# ---------------------------------------------------------

# Extract 3 complete InterproFamily nodes from the database
sample_families = InterproFamily.get_samples(limit=3)

for family in sample_families:
    print(f"Sample: {family.name}")


