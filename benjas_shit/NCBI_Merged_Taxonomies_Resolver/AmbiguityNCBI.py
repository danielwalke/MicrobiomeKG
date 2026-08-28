#structure to match the merged_id in the dmp file of NCBI


class NcbiMergedTaxonomy:
    def __init__(self, old_tax_id: int, new_tax_id: int):
        self.old_tax_id = old_tax_id
        self.new_tax_id = new_tax_id

    @classmethod
    def load_merged_dmp(cls, path: str) -> dict:
        """Parse NCBI's merged.dmp into {old_tax_id: new_tax_id}."""
        merged_map = {}
        with open(path, "r") as merged_dmp:
            for line in merged_dmp:
                fields = [field.strip() for field in line.split("|")]
                if len(fields) < 2 or not fields[0]:
                    continue
                record = cls(old_tax_id=int(fields[0]), new_tax_id=int(fields[1]))
                merged_map[record.old_tax_id] = record.new_tax_id
        return merged_map
