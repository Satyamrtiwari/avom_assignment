import os
import sys
import glob

sys.path.insert(0, 'backend')

from app.nlp.parser import parse_document
from app.nlp.extractor import ResumeExtractor
from app.nlp.jd_extractor import JDExtractor
from app.nlp.skill_taxonomy import SkillMatcher
from app.nlp.embedder import Embedder
from app.nlp.scorer import ResumeScorer
from app.config import settings
import spacy

nlp = spacy.load(settings.SPACY_MODEL)
skill_matcher = SkillMatcher(nlp, os.path.join(settings.DATA_DIR, "skills.json"))
resume_extractor = ResumeExtractor(nlp, skill_matcher)
jd_extractor = JDExtractor(nlp, skill_matcher)
embedder = Embedder.get_instance(settings.SBERT_MODEL)
scorer = ResumeScorer(
    embedder=embedder,
    weights={
        "skill": settings.WEIGHT_SKILL,
        "semantic": settings.WEIGHT_SEMANTIC,
        "experience": settings.WEIGHT_EXPERIENCE,
        "qualification": settings.WEIGHT_QUALIFICATION,
    },
    skill_matcher=skill_matcher,
)

test_dir = r"C:\Users\3star\Downloads\antigravity test"
jd_path = os.path.join(test_dir, "Job_Description_Senior_Python_AI_Engineer.pdf")
parsed_jd_doc = parse_document(jd_path)

# Extract JD with production JDExtractor
jd_data = jd_extractor.extract(parsed_jd_doc.raw_text)
jd_embedding = embedder.embed(parsed_jd_doc.raw_text)

print(f"JD Title: {jd_data.title}")
print(f"JD Exp required: {jd_data.experience_years} years ({jd_data.experience_required})")
print(f"JD Required Skills ({len(jd_data.required_skills)}): {jd_data.required_skills}")
print(f"JD Preferred Skills ({len(jd_data.preferred_skills)}): {jd_data.preferred_skills}")
print(f"JD Primary Skills: {jd_data.primary_skills}")
print(f"JD OR Groups: {jd_data.or_groups}")
print(f"JD Qualifications: {jd_data.qualifications}")

pdf_resumes = sorted([f for f in glob.glob(os.path.join(test_dir, "Candidate_*.pdf"))])
results = []

for pdf_p in pdf_resumes:
    fname = os.path.basename(pdf_p)
    parsed_res_doc = parse_document(pdf_p)
    res_text = parsed_res_doc.raw_text
    
    # Production ResumeExtractor
    res_data = resume_extractor.extract(res_text)
    res_embedding = embedder.embed(res_text)
    
    # Production ResumeScorer
    score_breakdown = scorer.score(
        candidate_name=res_data.candidate_name,
        jd_skills=jd_data.required_skills,
        resume_skills=res_data.skills,
        jd_embedding=jd_embedding,
        resume_embedding=res_embedding,
        jd_exp_years=jd_data.experience_years,
        resume_exp_years=res_data.experience_years,
        jd_exp_str=jd_data.experience_required,
        jd_qualifications=jd_data.qualifications,
        resume_education=res_data.education,
        degree_details=res_data.degree_details,
        preferred_skills=jd_data.preferred_skills,
        primary_skills=jd_data.primary_skills,
        responsibilities_skills=jd_data.responsibilities_skills,
        or_groups=jd_data.or_groups,
        is_experience_unknown=res_data.is_experience_unknown,
        roles=res_data.role_blocks,
        experience_source=res_data.experience_source,
        resume_text=res_text,
    )
    
    results.append({
        "file": fname,
        "name": res_data.candidate_name,
        "exp_years": res_data.experience_years,
        "overall": score_breakdown.overall_score,
        "skill_score": score_breakdown.skill_score,
        "semantic_score": score_breakdown.semantic_score,
        "exp_score": score_breakdown.experience_score,
        "qual_score": score_breakdown.qualification_score,
        "matched_skills": score_breakdown.matched_skills,
        "missing_skills": score_breakdown.missing_skills,
        "warnings": score_breakdown.warnings,
    })

results_sorted = sorted(results, key=lambda x: x["overall"], reverse=True)

print("\n" + "="*120)
print(f"{'RANK':<5} | {'FILE':<35} | {'NAME':<20} | {'EXP':<8} | {'OVERALL':<8} | {'SKILL':<6} | {'SEM':<6} | {'EXP_S':<6} | {'QUAL':<6}")
print("="*120)
for rank, r in enumerate(results_sorted, 1):
    print(f"#{rank:<4} | {r['file'][:35]:<35} | {str(r['name'])[:20]:<20} | {str(r['exp_years']) + 'y':<8} | {r['overall']:<7.1f}% | {r['skill_score']:<5.1f}% | {r['semantic_score']:<5.1f}% | {r['exp_score']:<5.1f}% | {r['qual_score']:<5.1f}%")

print("\n" + "="*120)
print("CANDIDATE DETAILS AUDIT:")
print("="*120)
for rank, r in enumerate(results_sorted, 1):
    print(f"\n[#{rank}] {r['name']} ({r['file']})")
    print(f"  Overall Score: {r['overall']}% | Exp: {r['exp_years']}y")
    print(f"  Matched Skills ({len(r['matched_skills'])}): {', '.join(r['matched_skills'][:10])}")
    print(f"  Missing Skills ({len(r['missing_skills'])}): {', '.join(r['missing_skills'][:8])}")
    if r['warnings']:
        print(f"  Warnings: {r['warnings']}")
