import os
import sys
import glob
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath("backend"))

import spacy
from app.nlp.parser import parse_document
from app.nlp.embedder import Embedder
from app.nlp.skill_taxonomy import SkillMatcher
from app.nlp.extractor import ResumeExtractor
from app.nlp.jd_extractor import JDExtractor
from app.nlp.scorer import ResumeScorer
from app.config import settings

def run_evaluation():
    print("=" * 80)
    print("RESUME-JD MATCHING & RANKING: COMPLETE VERIFICATION & EVALUATION")
    print("=" * 80)

    nlp = spacy.load(settings.SPACY_MODEL)
    embedder = Embedder.get_instance(settings.SBERT_MODEL)
    matcher = SkillMatcher(nlp, settings.DATA_DIR + "/skills.json")
    jd_extractor = JDExtractor(nlp, matcher)
    resume_extractor = ResumeExtractor(nlp, matcher)
    scorer = ResumeScorer(embedder, skill_matcher=matcher)

    jds_info = [
        ("JD_AI_Engineer", "uploads/jds/JD_AI_Engineer.pdf"),
        ("JD_Java_Developer", "uploads/jds/JD_Java_Developer.pdf"),
        ("JD_Python_Developer", "uploads/jds/JD_Python_Developer.pdf"),
        ("JD_Senior_Java", "sample_data/sample_jd.pdf"),
        ("JD_Data_Scientist", "C:/Users/3star/Downloads/claude_test/JD_Data_Scientist.pdf"),
        ("JD_Frontend_React", "C:/Users/3star/Downloads/claude_test/JD_Frontend_React_Developer.pdf"),
        ("JD_Digital_Marketing", "C:/Users/3star/Downloads/claude_test/JD_Digital_Marketing_Executive.pdf"),
    ]

    resumes_info = [
        # AI Resumes
        ("Rohan Mehta (Strong AI)", "uploads/34b770c8-d20d-4bf2-92be-256fbe0bf299/strong_candidate_AI_engineer.pdf"),
        ("Aditya Joshi (Medium AI)", "uploads/34b770c8-d20d-4bf2-92be-256fbe0bf299/medium_candidate_AI_engineer.pdf"),
        ("Vikram Patil (Weak AI)", "uploads/34b770c8-d20d-4bf2-92be-256fbe0bf299/weak_candidate_AI_engineer.pdf"),
        ("Satyam Tiwari (AI)", "uploads/34b770c8-d20d-4bf2-92be-256fbe0bf299/02_Satyam_Tiwari_Infinx_Aug2026.pdf"),
        # Hold-out test set
        ("Priya Nair (DS)", "C:/Users/3star/Downloads/claude_test/test01_colon_headers_hands_on_5yrs.pdf"),
        ("Karan Malhotra (Mismatch)", "C:/Users/3star/Downloads/claude_test/test02_summary_vs_dates_mismatch.pdf"),
        ("Sneha Kulkarni (Final Year)", "C:/Users/3star/Downloads/claude_test/test03_final_year_student_strong_skills.pdf"),
        ("Nisha Reddy (React)", "C:/Users/3star/Downloads/claude_test/test09_frontend_react_overlapping_jobs.pdf"),
        ("Imran Shaikh (No Dates)", "C:/Users/3star/Downloads/claude_test/test10_two_column_no_dates.pdf"),
    ]

    # Add all 12 sample resumes dynamically
    import re
    for fpath in sorted(glob.glob("sample_data/resumes/*.*")):
        fname = os.path.basename(fpath)
        clean_label = fname.replace("candidate_", "").replace(".pdf", "").replace(".docx", "").replace("_", " ").title()
        clean_label = re.sub(r"^\d+\s*", "", clean_label).strip()
        resumes_info.append((clean_label, fpath))

    # Pre-parse resumes
    parsed_resumes = {}
    for name, rpath in resumes_info:
        if not os.path.exists(rpath):
            print(f"Warning: Resume {name} not found at {rpath}")
            continue
        p = parse_document(rpath)
        text = p.raw_text if hasattr(p, "raw_text") else str(p)
        rdata = resume_extractor.extract(text)
        emb = embedder.embed(text)
        parsed_resumes[name] = {
            "path": rpath,
            "text": text,
            "data": rdata,
            "embedding": emb,
        }

    results_matrix = {}
    detailed_audits = {}

    for jd_name, jd_path in jds_info:
        if not os.path.exists(jd_path):
            print(f"Warning: JD {jd_name} not found at {jd_path}")
            continue

        jp = parse_document(jd_path)
        jtext = jp.raw_text if hasattr(jp, "raw_text") else str(jp)
        jdata = jd_extractor.extract(jtext)
        jemb = embedder.embed(jtext)

        results_matrix[jd_name] = {}
        detailed_audits[jd_name] = {}

        candidate_scores = []

        for cand_name, rdict in parsed_resumes.items():
            rdata = rdict["data"]
            remb = rdict["embedding"]

            breakdown = scorer.score(
                candidate_name=rdata.candidate_name or cand_name,
                jd_skills=jdata.required_skills,
                resume_skills=rdata.skills,
                jd_embedding=jemb,
                resume_embedding=remb,
                jd_exp_years=jdata.experience_years,
                resume_exp_years=rdata.experience_years,
                jd_exp_str=jdata.experience_required,
                jd_qualifications=jdata.qualifications,
                resume_education=rdata.education,
                preferred_skills=jdata.preferred_skills,
                or_groups=jdata.or_groups,
                roles=rdata.role_blocks,
                degree_details=rdata.degree_details,
                experience_source=rdata.experience_source,
                is_experience_unknown=rdata.is_experience_unknown,
                warnings=rdata.warnings,
                resume_text=rdict["text"],
            )

            candidate_scores.append((cand_name, breakdown))
            detailed_audits[jd_name][cand_name] = breakdown

        # Rank candidates for this JD
        candidate_scores.sort(key=lambda x: x[1].overall_score, reverse=True)
        for rank, (cand_name, bd) in enumerate(candidate_scores, start=1):
            results_matrix[jd_name][cand_name] = {
                "rank": rank,
                "score": bd.overall_score,
                "skill": bd.skill_score,
                "semantic": bd.semantic_score,
                "raw_cos": bd.raw_cosine,
                "exp": bd.experience_score,
                "qual": bd.qualification_score,
                "matched_skills": bd.matched_skills,
                "missing_skills": bd.missing_skills,
                "warnings": bd.warnings,
            }

    # Save evaluation artifacts
    with open("scripts/evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results_matrix, f, indent=2)

    print("\nEvaluation successfully completed! Results saved to scripts/evaluation_results.json")
    return results_matrix, parsed_resumes

if __name__ == "__main__":
    run_evaluation()
