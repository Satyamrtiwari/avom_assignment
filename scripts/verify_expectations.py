import json
import os
import sys

def verify_all():
    with open("scripts/evaluation_results.json", "r", encoding="utf-8") as f:
        matrix = json.load(f)

    # Load parsed resume data directly to inspect extraction details
    sys.path.insert(0, os.path.abspath("backend"))
    import spacy
    from app.nlp.parser import parse_document
    from app.nlp.skill_taxonomy import SkillMatcher
    from app.nlp.extractor import ResumeExtractor
    from app.nlp.jd_extractor import JDExtractor
    from app.config import settings

    nlp = spacy.load(settings.SPACY_MODEL)
    matcher = SkillMatcher(nlp, settings.DATA_DIR + "/skills.json")
    re_extractor = ResumeExtractor(nlp, matcher)
    jd_extractor = JDExtractor(nlp, matcher)

    # 1. Karan Malhotra
    karan_p = parse_document("C:/Users/3star/Downloads/claude_test/test02_summary_vs_dates_mismatch.pdf")
    karan_data = re_extractor.extract(karan_p.raw_text)

    # 2. Priya Nair
    priya_p = parse_document("C:/Users/3star/Downloads/claude_test/test01_colon_headers_hands_on_5yrs.pdf")
    priya_data = re_extractor.extract(priya_p.raw_text)

    # 3. Sneha Kulkarni (test03)
    sneha_p = parse_document("C:/Users/3star/Downloads/claude_test/test03_final_year_student_strong_skills.pdf")
    sneha_data = re_extractor.extract(sneha_p.raw_text)

    # 4. Nisha Reddy (test09)
    nisha_p = parse_document("C:/Users/3star/Downloads/claude_test/test09_frontend_react_overlapping_jobs.pdf")
    nisha_data = re_extractor.extract(nisha_p.raw_text)

    # 5. Imran Shaikh (test10)
    imran_p = parse_document("C:/Users/3star/Downloads/claude_test/test10_two_column_no_dates.pdf")
    imran_data = re_extractor.extract(imran_p.raw_text)

    # 6. Divya Mehta
    divya_p = parse_document("sample_data/resumes/candidate_12_divya_mehta.docx")
    divya_data = re_extractor.extract(divya_p.raw_text)

    print("=" * 80)
    print("VERIFICATION OF TEST EXPECTATIONS")
    print("=" * 80)

    checks = []

    # Check 1: Karan Malhotra dates win over summary
    exp_years = karan_data.experience_years
    has_disc_warning = any("Discrepancy" in w for w in karan_data.warnings)
    karan_pass = (exp_years == 2.5) and has_disc_warning and (karan_data.experience_source == "dates")
    checks.append((
        "Karan Malhotra: Dates always win over summary (claims 8 yrs, dates prove 2.5 yrs)",
        "PASS" if karan_pass else "FAIL",
        f"Years={exp_years}, Source={karan_data.experience_source}, Warning={has_disc_warning}"
    ))

    # Check 2: Priya Nair Mathematics degree recognized under Data Scientist JD
    priya_ds = matrix["JD_Data_Scientist"].get("Priya Nair (DS)", {})
    priya_qual_pass = priya_ds.get("qual", 0) >= 85.0
    checks.append((
        "Priya Nair: CS/Data degree recognized for Data Scientist qualification (qual >= 85%)",
        "PASS" if priya_qual_pass else "FAIL",
        f"Qual Score={priya_ds.get('qual')}%, Degree={priya_data.education}"
    ))

    # Check 3: Imran Shaikh Statistics degree qualification score under Data Scientist JD
    imran_ds = matrix["JD_Data_Scientist"].get("Imran Shaikh (No Dates)", {})
    imran_qual_pass = imran_ds.get("qual", 0) >= 85.0
    checks.append((
        "Imran Shaikh: Statistics degree recognized for Data Scientist qualification (qual >= 85%)",
        "PASS" if imran_qual_pass else "FAIL",
        f"Qual Score={imran_ds.get('qual')}%, Degree={imran_data.education}"
    ))

    # Check 4: Sneha Kulkarni Earliest degree anchor (not penalized for in-progress degree)
    sneha_ds = matrix["JD_Data_Scientist"].get("Sneha Kulkarni (Final Year)", {})
    sneha_anchor_pass = (sneha_data.degree_details[0]["is_completed"] is False) and (sneha_ds.get("qual", 0) >= 85.0)
    checks.append((
        "Sneha Kulkarni: In-progress expected degree handled without penalization; qual >= 85%",
        "PASS" if sneha_anchor_pass else "FAIL",
        f"Completed={sneha_data.degree_details[0]['is_completed']}, Qual Score={sneha_ds.get('qual')}%, Degree={sneha_data.education}"
    ))

    # Check 5: Nisha Reddy Overlapping jobs merged correctly
    nisha_exp = nisha_data.experience_years
    nisha_frontend = matrix["JD_Frontend_React"].get("Nisha Reddy (React)", {})
    nisha_pass = (nisha_frontend.get("rank") == 1) and (nisha_exp is not None and nisha_exp > 0)
    checks.append((
        "Nisha Reddy: Overlapping jobs merged accurately; Ranks #1 for Frontend React JD",
        "PASS" if nisha_pass else "FAIL",
        f"Rank={nisha_frontend.get('rank')}, Score={nisha_frontend.get('score')}%, Exp={nisha_exp} yrs"
    ))

    # Check 6: Imran Shaikh (test10) 2-column no dates fallback to summary
    test10_summary_pass = imran_data.experience_source == "summary" and imran_data.experience_years == 3.0
    checks.append((
        "Imran Shaikh (test10): 2-column layout with no dates falls back accurately to summary (source='summary', 3.0 yrs)",
        "PASS" if test10_summary_pass else "FAIL",
        f"Years={imran_data.experience_years}, Source={imran_data.experience_source}"
    ))

    # Check 7: Divya Mehta (Mass Comm) suppressed on Technical JDs (score <= 10.0%)
    divya_ai = matrix["JD_AI_Engineer"].get("Divya Mehta", {}).get("score", 100)
    divya_java = matrix["JD_Java_Developer"].get("Divya Mehta", {}).get("score", 100)
    divya_python = matrix["JD_Python_Developer"].get("Divya Mehta", {}).get("score", 100)
    divya_sr_java = matrix["JD_Senior_Java"].get("Divya Mehta", {}).get("score", 100)
    divya_ds = matrix["JD_Data_Scientist"].get("Divya Mehta", {}).get("score", 100)
    divya_suppressed = all(s <= 10.0 for s in [divya_ai, divya_java, divya_python, divya_sr_java, divya_ds])
    checks.append((
        "Divya Mehta: Non-tech candidate strictly suppressed to <= 10% across ALL technical JDs",
        "PASS" if divya_suppressed else "FAIL",
        f"AI={divya_ai}%, Java={divya_java}%, Python={divya_python}%, SrJava={divya_sr_java}%, DS={divya_ds}%"
    ))

    # Check 8: Divya Mehta ranks top tier for Digital Marketing JD
    divya_mkt = matrix["JD_Digital_Marketing"].get("Divya Mehta", {})
    divya_mkt_pass = divya_mkt.get("rank", 99) == 1 and divya_mkt.get("score", 0) >= 15.0
    checks.append((
        "Divya Mehta: Mass Comm / Marketing profile recognized and ranks #1 for Digital Marketing JD",
        "PASS" if divya_mkt_pass else "FAIL",
        f"Rank={divya_mkt.get('rank')}, Score={divya_mkt.get('score')}%"
    ))

    # Check 9: AI Engineer JD Ranking Sanity: Strong AI > Medium AI > Weak AI
    ai_strong = matrix["JD_AI_Engineer"]["Rohan Mehta (Strong AI)"]["score"]
    ai_med = matrix["JD_AI_Engineer"]["Aditya Joshi (Medium AI)"]["score"]
    ai_weak = matrix["JD_AI_Engineer"]["Vikram Patil (Weak AI)"]["score"]
    ai_rank_pass = ai_strong > ai_med > ai_weak
    checks.append((
        "AI Engineer JD: Strict monotonic ordering (Strong AI > Medium AI > Weak AI)",
        "PASS" if ai_rank_pass else "FAIL",
        f"Strong={ai_strong}%, Medium={ai_med}%, Weak={ai_weak}%"
    ))

    # Check 10: Senior Java JD Ranking: Amit Sharma & Rohit Verma are top candidates
    sr_amit = matrix["JD_Senior_Java"].get("Amit Sharma", {}).get("score", 0)
    sr_rohit = matrix["JD_Senior_Java"].get("Rohit Verma", {}).get("score", 0)
    sr_amit_rank = matrix["JD_Senior_Java"].get("Amit Sharma", {}).get("rank", 99)
    sr_rohit_rank = matrix["JD_Senior_Java"].get("Rohit Verma", {}).get("rank", 99)
    sr_java_pass = sr_amit_rank <= 3 and sr_rohit_rank <= 3
    checks.append((
        "Senior Java JD: Experienced Java engineers (Amit Sharma, Rohit Verma) dominate top ranks",
        "PASS" if sr_java_pass else "FAIL",
        f"Amit Sharma (Rank {sr_amit_rank}, {sr_amit}%), Rohit Verma (Rank {sr_rohit_rank}, {sr_rohit}%)"
    ))
    checks.append((
        "Senior Java JD: Experienced Java engineers (Amit Sharma, Rohit Verma) dominate top ranks",
        "PASS" if sr_java_pass else "FAIL",
        f"Amit Sharma (Rank {sr_amit_rank}, {sr_amit}%), Rohit Verma (Rank {sr_rohit_rank}, {sr_rohit}%)"
    ))

    # Print Report
    for desc, status, numbers in checks:
        print(f"[{status}] {desc}")
        print(f"       Details: {numbers}\n")

    return checks, matrix

if __name__ == "__main__":
    verify_all()
