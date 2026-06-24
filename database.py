# database.py
import json
from config import OUTPUT_JSON


class ResultsDatabase:
    def export_to_json(self, groups, summary):
        data = {"summary": summary, "groups": groups}
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
