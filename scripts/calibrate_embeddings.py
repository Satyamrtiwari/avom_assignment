import json
import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath("backend"))

from app.nlp.parser import parse_document
from app.nlp.embedder import Embedder
from app.config import settings

def run_calibration():
    print("="*70)
    print("PERCENTILE-BASED SEMANTIC CALIBRATION (ORIGINAL 16 RESUMES x 4 JDS)")
    print("="*70)
    embedder = Embedder.get_instance(settings.SBERT_MODEL)

    jds = {
        "AI": "uploads/jds/JD_AI_Engineer.pdf",
        "Java": "uploads/jds/JD_Java_Developer.pdf",
        "SeniorJava": "sample_data/sample_jd.pdf",
        "Python": "uploads/jds/JD_Python_Developer.pdf",
    }

    resumes = {
        "Rohan (AI)": "uploads/34b770c8-d20d-4bf2-92be-256fbe0bf299/strong_candidate_AI_engineer.pdf",
        "Ananya (AI)": "uploads/34b770c8-d20d-4bf2-92be-256fbe0bf299/medium_candidate_AI_engineer.pdf",
        "Vikram (PHP/AI)": "uploads/34b770c8-d20d-4bf2-92be-256fbe0bf299/weak_candidate_AI_engineer.pdf",
        "Satyam (AI)": "uploads/34b770c8-d20d-4bf2-92be-256fbe0bf299/02_Satyam_Tiwari_Infinx_Aug2026.pdf",
        "Amit (Java/Py)": "sample_data/resumes/candidate_01_amit_sharma.pdf",
        "Rohit (Java)": "sample_data/resumes/candidate_02_rohit_verma.docx",
        "Neha (Java)": "sample_data/resumes/candidate_03_neha_patel.pdf",
        "Vikas (Java)": "sample_data/resumes/candidate_04_vikas_singh.docx",
        "SnehaR (Java)": "sample_data/resumes/candidate_05_sneha_reddy.pdf",
        "Manish (Java)": "sample_data/resumes/candidate_06_manish_gupta.docx",
        "Kavita (Python)": "sample_data/resumes/candidate_07_kavita_nair.pdf",
        "Arjun (React)": "sample_data/resumes/candidate_08_arjun_kumar.docx",
        "Pooja (Java)": "sample_data/resumes/candidate_09_pooja_joshi.pdf",
        "Rahul (DataAnalyst)": "sample_data/resumes/candidate_10_rahul_deshmukh.docx",
        "Sanjay (DevOps)": "sample_data/resumes/candidate_11_sanjay_rawat.pdf",
        "Divya (Marketing)": "sample_data/resumes/candidate_12_divya_mehta.docx",
    }

    jd_embs = {k: embedder.embed(parse_document(p).raw_text) for k, p in jds.items()}
    res_embs = {k: embedder.embed(parse_document(p).raw_text) for k, p in resumes.items()}

    matrix = {}
    for rname, remb in res_embs.items():
        row = {}
        for jname, jemb in jd_embs.items():
            cos = embedder.similarity(jemb, remb)
            row[jname] = cos
        matrix[rname] = row

    # 30 Labelled Related Pairs from original training corpus:
    related_pairs = [
        # AI JD
        ("AI", "Rohan (AI)"), ("AI", "Ananya (AI)"), ("AI", "Satyam (AI)"),
        # Java JD
        ("Java", "Amit (Java/Py)"), ("Java", "Rohit (Java)"), ("Java", "Neha (Java)"),
        ("Java", "Vikas (Java)"), ("Java", "SnehaR (Java)"), ("Java", "Manish (Java)"),
        ("Java", "Pooja (Java)"),
        # Senior Java JD
        ("SeniorJava", "Amit (Java/Py)"), ("SeniorJava", "Rohit (Java)"), ("SeniorJava", "Neha (Java)"),
        ("SeniorJava", "Vikas (Java)"), ("SeniorJava", "SnehaR (Java)"), ("SeniorJava", "Manish (Java)"),
        ("SeniorJava", "Pooja (Java)"),
        # Python JD
        ("Python", "Kavita (Python)"), ("Python", "Rohan (AI)"), ("Python", "Ananya (AI)"),
        ("Python", "Amit (Java/Py)"), ("Python", "Satyam (AI)"), ("Python", "Rahul (DataAnalyst)"),
        # Secondary related (DevOps, Data Analyst on AI/Java/Python)
        ("Java", "Sanjay (DevOps)"), ("SeniorJava", "Sanjay (DevOps)"),
        ("Python", "Sanjay (DevOps)"),
        ("AI", "Kavita (Python)"),
        ("SeniorJava", "Vikram (PHP/AI)"),
        ("Java", "Vikram (PHP/AI)"),
        ("AI", "Rahul (DataAnalyst)"),
    ]

    # 30 Labelled Unrelated Pairs from original training corpus:
    unrelated_pairs = [
        # Divya (Marketing) vs all technical JDs
        ("AI", "Divya (Marketing)"), ("Java", "Divya (Marketing)"),
        ("SeniorJava", "Divya (Marketing)"), ("Python", "Divya (Marketing)"),
        # Arjun (React frontend) vs backend / AI JDs
        ("Java", "Arjun (React)"), ("SeniorJava", "Arjun (React)"),
        ("Python", "Arjun (React)"), ("AI", "Arjun (React)"),
        # Rahul (Data Analyst) vs Java backend JDs
        ("Java", "Rahul (DataAnalyst)"), ("SeniorJava", "Rahul (DataAnalyst)"),
        # Java developers vs AI JD
        ("AI", "Rohit (Java)"), ("AI", "Neha (Java)"), ("AI", "Vikas (Java)"),
        ("AI", "SnehaR (Java)"), ("AI", "Manish (Java)"), ("AI", "Pooja (Java)"),
        # Java developers vs Python JD (lacking Python)
        ("Python", "Rohit (Java)"), ("Python", "Neha (Java)"), ("Python", "Vikas (Java)"),
        ("Python", "SnehaR (Java)"), ("Python", "Manish (Java)"), ("Python", "Pooja (Java)"),
        # AI candidates vs Java JDs
        ("Java", "Rohan (AI)"), ("SeniorJava", "Rohan (AI)"),
        ("Java", "Ananya (AI)"), ("SeniorJava", "Ananya (AI)"),
        ("Java", "Satyam (AI)"), ("SeniorJava", "Satyam (AI)"),
        ("SeniorJava", "Kavita (Python)"), ("Java", "Kavita (Python)"),
    ]

    rel_vals = [matrix[r][j] for j, r in related_pairs]
    unrel_vals = [matrix[r][j] for j, r in unrelated_pairs]

    floor_p75 = float(np.percentile(unrel_vals, 75))
    floor_p90 = float(np.percentile(unrel_vals, 90))
    ceil_p90 = float(np.percentile(rel_vals, 90))

    floor_val = round(floor_p75, 2)  # 0.50
    ceil_val = round(ceil_p90, 2)    # 0.80 (rounded from 0.745-0.85)

    print("\n" + "="*70)
    print("CALIBRATION DISTRIBUTION (N=30 Related, N=30 Unrelated)")
    print("="*70)
    print(f"Related Pairs   (N=30): Min={min(rel_vals):.4f}, Mean={np.mean(rel_vals):.4f}, P50={np.percentile(rel_vals, 50):.4f}, P75={np.percentile(rel_vals, 75):.4f}, P90={ceil_p90:.4f}, Max={max(rel_vals):.4f}")
    print(f"Unrelated Pairs (N=30): Min={min(unrel_vals):.4f}, Mean={np.mean(unrel_vals):.4f}, P50={np.percentile(unrel_vals, 50):.4f}, P75={floor_p75:.4f}, P90={floor_p90:.4f}, Max={max(unrel_vals):.4f}")
    print(f"\nCalibrated Floor:   {floor_val} (P75 of unrelated pairs = {floor_p75:.4f})")
    print(f"Calibrated Ceiling: {ceil_val} (Upper P90 of related pairs = {ceil_p90:.4f})")

    return floor_val, ceil_val

if __name__ == "__main__":
    run_calibration()
