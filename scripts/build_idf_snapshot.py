import datetime
import json
import math
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.nlp.parser import parse_document
from app.nlp.skill_taxonomy import SkillMatcher
import spacy

def build_idf_snapshot():
    print("Building frozen IDF snapshot v1...")
    nlp = spacy.load("en_core_web_sm")
    skills_path = os.path.join("backend", "data", "skills.json")
    skill_matcher = SkillMatcher(nlp, skills_path)

    canonical_dirs = [
        "sample_data",
        r"C:\Users\3star\Downloads\claude_test",
        r"C:\Users\3star\Downloads\avum_testing"
    ]

    doc_paths = []
    for d in canonical_dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if (f.endswith(".pdf") or f.endswith(".docx")) and not f.startswith("empty") and not f.startswith("corrupt"):
                        doc_paths.append(os.path.join(root, f))

    doc_paths = sorted(list(set(doc_paths)))
    print(f"Total documents found for IDF corpus: {len(doc_paths)}")

    N = 0
    df_counts = {}

    for path in doc_paths:
        try:
            parsed = parse_document(path)
            text = parsed.raw_text if hasattr(parsed, "raw_text") else str(parsed)
            if not text or len(text.strip()) < 50:
                continue
            N += 1
            skills = skill_matcher.extract_skills(text)
            for s in set(skills):
                df_counts[s] = df_counts.get(s, 0) + 1
        except Exception as e:
            print(f"Error parsing {path}: {e}")

    print(f"Successfully processed {N} documents for IDF calculation.")

    idf_weights = {}
    for s, df in df_counts.items():
        raw_idf = math.log((N + 1) / (df + 1)) + 1.0
        idf_weights[s] = round(raw_idf, 4)

    if idf_weights:
        vals = list(idf_weights.values())
        avg_val = sum(vals) / len(vals)
        normalized_weights = {k: round(v / avg_val, 4) for k, v in idf_weights.items()}
    else:
        normalized_weights = {}

    # Domain adjustments: ubiquitous baseline tools receive discounted weight
    manual_overrides = {
        "Git": 0.45,
        "Agile": 0.50,
        "REST APIs": 0.65,
        "Testing / QA": 0.60,
    }
    for k, override_w in manual_overrides.items():
        normalized_weights[k] = override_w

    snapshot = {
        "version": "1.0.0",
        "created_at": datetime.datetime.now().isoformat(),
        "corpus_size": N,
        "fallback_weight": 1.0,
        "weights": normalized_weights
    }

    out_path = os.path.join("backend", "data", "idf_snapshot_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"IDF snapshot saved to {out_path} ({len(normalized_weights)} skills indexed).")

if __name__ == "__main__":
    build_idf_snapshot()
