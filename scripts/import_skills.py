import argparse
import json
import os
import sys

def import_skills(input_file: str, category: str = "imported_skills"):
    """
    Import skills from an external JSON or CSV file into backend/data/skills.json.
    Supported JSON formats:
      1. List of skill strings: ["Airflow", "MLflow", "Tableau", ...]
      2. Dict of skills with aliases: {"airflow": {"canonical": "Apache Airflow", "aliases": ["airflow"]}}
    Supported CSV format:
      skill_name,aliases (comma-separated aliases in quotes)
    """
    skills_path = os.path.join("backend", "data", "skills.json")
    if not os.path.exists(skills_path):
        print(f"Error: {skills_path} does not exist.")
        return

    with open(skills_path, "r", encoding="utf-8") as f:
        taxonomy = json.load(f)

    if category not in taxonomy:
        taxonomy[category] = {}

    imported_count = 0

    if input_file.endswith(".json"):
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            for item in data:
                skill_name = str(item).strip()
                skill_key = skill_name.lower().replace(" ", "_").replace(".", "_")
                if skill_key not in taxonomy[category]:
                    taxonomy[category][skill_key] = {
                        "canonical": skill_name,
                        "aliases": []
                    }
                    imported_count += 1
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    taxonomy[category][k] = v
                    imported_count += 1
                else:
                    taxonomy[category][k] = {"canonical": str(v), "aliases": []}
                    imported_count += 1

    elif input_file.endswith(".csv"):
        import csv
        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or not row[0].strip() or row[0].lower() in ("skill", "name"):
                    continue
                name = row[0].strip()
                aliases = [a.strip() for a in row[1].split(";")] if len(row) > 1 else []
                key = name.lower().replace(" ", "_").replace(".", "_")
                taxonomy[category][key] = {"canonical": name, "aliases": aliases}
                imported_count += 1

    with open(skills_path, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, indent=2)

    print(f"Successfully imported {imported_count} skills into category '{category}'.")
    print("Remember to run 'python scripts/build_idf_snapshot.py' to update IDF weights.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import external skills list into taxonomy")
    parser.add_argument("file", help="Path to JSON or CSV file containing skills")
    parser.add_argument("--category", default="imported_skills", help="Taxonomy category name")
    args = parser.parse_args()
    import_skills(args.file, args.category)
