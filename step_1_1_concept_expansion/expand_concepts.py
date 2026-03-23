import json

with open("step_1_1_concept_expansion/relevant_additional_concepts.json", "r") as f:
    relevant_additional_concepts = json.load(f)
    print(json.dumps(relevant_additional_concepts, indent=4))