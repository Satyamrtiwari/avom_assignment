import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Sequence, Any
import numpy as np

from app.nlp.embedder import Embedder
from app.config import settings

logger = logging.getLogger("resumeranker.scorer")


@dataclass
class ScoreBreakdown:
    overall_score: float
    semantic_score: float
    skill_score: float
    experience_score: float
    qualification_score: float
    raw_cosine: float = 0.0
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    matched_skills_detailed: list[dict] = field(default_factory=list)
    total_experience_years: float | None = None
    relevant_experience_years: float | None = None
    experience_source: str = "dates"
    is_experience_unknown: bool = False
    experience_comparison: dict = field(default_factory=dict)
    qualification_audit: dict = field(default_factory=dict)
    weights_used: dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    warnings: list[str] = field(default_factory=list)


class ResumeScorer:
    """
    Production-grade explainable multi-signal matching & candidate scoring engine:
    1. Skill Overlap (w=0.35): IDF-weighted skill coverage, OR-group satisfaction & preferred skill ratio.
    2. Semantic Fit (w=0.30): Percentile-calibrated cosine similarity.
    3. Experience Match (w=0.20): Role-relevance weighted tenure vs JD required years.
    4. Qualification Match (w=0.15): Degree hierarchy with OR-clause min-threshold & semantic field alignment.
    5. Proportional Weight Renormalization: Safely handles non-tech/zero-skill JDs without phantom matches.
    6. Smooth Continuous Relevance: Differentiable modulation factor R without discontinuous cliff caps.
    """

    def __init__(self, embedder: Embedder, weights: dict[str, float] | None = None, skill_matcher: Any = None):
        self.embedder = embedder
        self.skill_matcher = skill_matcher
        self.default_weights = weights or {
            "skill": settings.WEIGHT_SKILL,
            "semantic": settings.WEIGHT_SEMANTIC,
            "experience": settings.WEIGHT_EXPERIENCE,
            "qualification": settings.WEIGHT_QUALIFICATION,
        }
        self.degrees_tax = self._load_degrees_taxonomy()
        self.idf_weights = self._load_idf_snapshot()

    def _load_degrees_taxonomy(self) -> dict:
        path = settings.DEGREES_TAXONOMY_PATH
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load degrees taxonomy in scorer: {e}")
        return {}

    def _load_idf_snapshot(self) -> dict:
        path = settings.IDF_SNAPSHOT_PATH
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f).get("weights", {})
            except Exception as e:
                logger.warning(f"Failed to load IDF snapshot in scorer: {e}")
        return {}

    def get_skill_weight(self, skill: str) -> float:
        """Fetch IDF weight with fallback 1.0."""
        # Generic ubiquitous skills receive discounted weight
        if skill in ("Git", "Agile"):
            return 0.45
        if skill in ("REST APIs", "Testing / QA"):
            return 0.60
        return self.idf_weights.get(skill, settings.IDF_FALLBACK_WEIGHT)

    def score(
        self,
        candidate_name: str | None,
        jd_skills: list[str],
        resume_skills: list[str],
        jd_embedding: Sequence[float] | None,
        resume_embedding: Sequence[float] | None,
        jd_exp_years: float | None,
        resume_exp_years: float | None,
        jd_exp_str: str | None,
        jd_qualifications: list[str],
        resume_education: list[str],
        preferred_skills: list[str] | None = None,
        or_groups: list[list[str]] | None = None,
        roles: list[Any] | None = None,
        jd_text: str | None = None,
        is_experience_unknown: bool = False,
        experience_source: str = "dates",
        weight_overrides: dict[str, float] | None = None,
        degree_details: list[dict] | None = None,
        warnings: list[str] | None = None,
        resume_text: str | None = None,
        primary_skills: list[str] | None = None,
        responsibilities_skills: list[str] | None = None,
    ) -> ScoreBreakdown:
        """Compute complete multi-signal scoring breakdown, provenance audit, and explanation."""
        preferred_skills = preferred_skills or []
        primary_skills = primary_skills or []
        responsibilities_skills = responsibilities_skills or []
        or_groups = or_groups or []
        warnings = list(warnings or [])

        # Open-vocabulary and target-skill matching directly against candidate text
        if resume_text and self.skill_matcher:
            target_res = self.skill_matcher.match_target_skills(jd_skills, resume_text, or_groups=or_groups)
            resume_skills = list(set(resume_skills + target_res.get("matched", [])))
            if preferred_skills:
                target_pref = self.skill_matcher.match_target_skills(preferred_skills, resume_text)
                resume_skills = list(set(resume_skills + target_pref.get("matched", [])))
            if responsibilities_skills:
                target_resp = self.skill_matcher.match_target_skills(responsibilities_skills, resume_text)
                resume_skills = list(set(resume_skills + target_resp.get("matched", [])))

        # 1. Weight Resolution & Zero-Skill JD Proportional Renormalization
        active_weights = dict(weight_overrides or self.default_weights)
        is_zero_skill_jd = len(jd_skills) == 0

        if is_zero_skill_jd:
            # Drop skill weight and renormalize remaining weights proportionally
            skill_w = active_weights.pop("skill", 0.0)
            remaining_sum = sum(active_weights.values())
            if remaining_sum > 0:
                active_weights = {k: v / remaining_sum for k, v in active_weights.items()}
            active_weights["skill"] = 0.0
            warnings.append("Role specifies no cataloged technical skills. Scoring weights renormalized proportionally.")

        total_w = sum(active_weights.values())
        if total_w > 0:
            active_weights = {k: v / total_w for k, v in active_weights.items()}

        # 2. Skill Overlap & OR-Group Satisfaction
        skill_res = self._compute_skill_score(
            jd_skills=jd_skills,
            resume_skills=resume_skills,
            preferred_skills=preferred_skills,
            primary_skills=primary_skills,
            responsibilities_skills=responsibilities_skills,
            or_groups=or_groups,
            is_zero_skill_jd=is_zero_skill_jd,
        )

        # 3. Semantic Fit (Percentile-Calibrated)
        sem_score, raw_cos = self._compute_semantic_score(jd_embedding, resume_embedding)

        # 4. Continuous Smooth Relevance Factor (No hard cliffs)
        # R in [RELEVANCE_MIN_THRESHOLD, 1.0] modulated by primary domain skill presence
        skill_ratio = skill_res["matched_ratio"]
        sem_ratio = sem_score / 100.0
        r_raw = (
            settings.RELEVANCE_SKILL_COEFF * skill_ratio
            + settings.RELEVANCE_SEMANTIC_COEFF * sem_ratio
        )
        min_th = settings.RELEVANCE_MIN_THRESHOLD
        full_th = settings.RELEVANCE_FULL_THRESHOLD
        if r_raw >= full_th:
            relevance_factor = 1.0
        elif r_raw <= min_th:
            relevance_factor = min_th
        else:
            relevance_factor = min_th + (1.0 - min_th) * ((r_raw - min_th) / (full_th - min_th))

        # Primary skill damping: candidates lacking primary role skills are damped
        primary_total = skill_res.get("primary_total", 0)
        primary_matched = skill_res.get("primary_matched", 0)
        if primary_total > 0:
            if primary_matched == 0:
                primary_damping = settings.PRIMARY_ZERO_DAMPING
                warnings.append(f"Candidate lacks primary role skills ({', '.join(primary_skills[:3])}); primary domain damping applied.")
                skill_res["score"] = round(skill_res["score"] * primary_damping, 1)
            else:
                primary_damping = 0.5 + 0.5 * (primary_matched / primary_total)
            relevance_factor *= primary_damping

        relevance_factor = float(np.clip(relevance_factor, min_th, 1.0))

        # 5. Experience Score & Role Relevance
        exp_res = self._compute_experience_score(
            jd_exp_years=jd_exp_years,
            resume_exp_years=resume_exp_years,
            jd_exp_str=jd_exp_str,
            is_unknown=is_experience_unknown,
            roles=roles,
            jd_embedding=jd_embedding,
            relevance_factor=relevance_factor,
        )

        # 6. Qualification Score & Semantic Field Alignment
        qual_res = self._compute_qualification_score(
            jd_qualifications=jd_qualifications,
            resume_education=resume_education,
            degree_details=degree_details,
            relevance_factor=relevance_factor,
        )

        # 7. Final Weighted Overall Score
        overall = (
            active_weights.get("skill", 0.0) * skill_res["score"]
            + active_weights.get("semantic", 0.0) * sem_score
            + active_weights.get("experience", 0.0) * exp_res["score"]
            + active_weights.get("qualification", 0.0) * qual_res["score"]
        )
        overall = round(max(0.0, min(100.0, overall)), 1)

        # 8. Provenance Grounding & Keyword Stuffing Defense
        # Check if matched technical skills are supported by documented work experience or project history
        if (resume_text or roles) and self.skill_matcher and len(skill_res["matched"]) >= 4:
            work_history_text = ""
            if roles:
                work_history_text = "\n".join(getattr(r, "description", "") for r in roles)
            if resume_text:
                exp_sections = re.findall(
                    r"(?:experience|employment|work\s+history|projects)[\s\S]*?(?=(?:education|certifications|skills|languages|$))",
                    resume_text,
                    re.IGNORECASE,
                )
                if exp_sections:
                    work_history_text += "\n" + "\n".join(exp_sections)
                elif not work_history_text:
                    work_history_text = resume_text

            if work_history_text:
                exp_skills = set(self.skill_matcher.extract_skills(work_history_text))
                matched_set = set(skill_res["matched"])
                unverified_skills = matched_set - exp_skills
                unverified_ratio = len(unverified_skills) / max(1, len(matched_set))

                if unverified_ratio >= 0.70 and len(exp_skills) <= 2:
                    logger.warning(
                        f"Adversarial keyword stuffing detected for candidate '{candidate_name}': "
                        f"{len(unverified_skills)} ungrounded skills."
                    )
                    overall = round(overall * 0.60, 1)
                    warnings.append(
                        "Adversarial keyword stuffing detected: core technical skills are absent from documented work experience/project history."
                    )

        # Generate Transparent Explanation
        explanation = self._generate_explanation(
            name=candidate_name or "Candidate",
            overall=overall,
            skill_score=skill_res["score"],
            matched_skills=skill_res["matched"],
            missing_skills=skill_res["missing"],
            sem_score=sem_score,
            exp_comparison=exp_res["comparison"],
            qual_score=qual_res["score"],
            is_zero_skill_jd=is_zero_skill_jd,
            relevance_factor=relevance_factor,
            exp_source=experience_source,
            warnings=warnings,
        )

        return ScoreBreakdown(
            overall_score=overall,
            semantic_score=round(sem_score, 1),
            skill_score=round(skill_res["score"], 1),
            experience_score=round(exp_res["score"], 1),
            qualification_score=round(qual_res["score"], 1),
            raw_cosine=round(raw_cos, 4),
            matched_skills=skill_res["matched"],
            missing_skills=skill_res["missing"],
            matched_skills_detailed=skill_res["detailed"],
            total_experience_years=resume_exp_years,
            relevant_experience_years=exp_res["relevant_years"],
            experience_source=experience_source,
            is_experience_unknown=is_experience_unknown,
            experience_comparison=exp_res["comparison"],
            qualification_audit=qual_res["audit"],
            weights_used={k: round(v, 4) for k, v in active_weights.items()},
            explanation=explanation,
            warnings=warnings,
        )

    def _compute_skill_score(
        self,
        jd_skills: list[str],
        resume_skills: list[str],
        preferred_skills: list[str] | None = None,
        primary_skills: list[str] | None = None,
        responsibilities_skills: list[str] | None = None,
        or_groups: list[list[str]] | None = None,
        is_zero_skill_jd: bool = False,
    ) -> dict:
        """
        IDF-weighted skill scoring with OR-group resolution, primary skill multiplier,
        responsibilities weighting, and preferred skill weighting.
        """
        if is_zero_skill_jd:
            return {
                "score": 0.0,
                "matched": [],
                "missing": [],
                "detailed": [],
                "matched_ratio": 0.0,
                "primary_matched": 0,
                "primary_total": 0,
            }

        resume_set = {s.strip().lower(): s for s in resume_skills if s and s.strip()}
        matched_req: list[str] = []
        missing_req: list[str] = []
        detailed_list: list[dict] = []

        total_weight = 0.0
        earned_weight = 0.0

        or_groups = or_groups or []
        preferred_skills = preferred_skills or []
        primary_skills = primary_skills or []
        responsibilities_skills = responsibilities_skills or []
        primary_set = {s.strip().lower() for s in primary_skills if s and s.strip()}

        primary_total = 0
        primary_matched = 0

        # 1. Evaluate Required Skills & OR-Groups
        or_group_satisfied = [False] * len(or_groups)

        for req in jd_skills:
            req_clean = req.strip()
            if not req_clean:
                continue

            w = self.get_skill_weight(req_clean)
            is_primary = req_clean.lower() in primary_set
            if is_primary:
                w *= settings.PRIMARY_SKILL_WEIGHT_MULTIPLIER
                primary_total += 1

            total_weight += w

            # Check if this skill is in an OR-group
            in_or_group = False
            for idx, grp in enumerate(or_groups):
                if req_clean in grp or any(m.lower() == req_clean.lower() for m in grp):
                    in_or_group = True
                    for member in grp:
                        if member.lower() in resume_set:
                            or_group_satisfied[idx] = True
                            break

            is_matched = False
            if req_clean.lower() in resume_set:
                is_matched = True
            elif in_or_group:
                for idx, grp in enumerate(or_groups):
                    if (req_clean in grp or any(m.lower() == req_clean.lower() for m in grp)) and or_group_satisfied[idx]:
                        is_matched = True
                        break

            if is_matched:
                matched_req.append(req_clean)
                earned_weight += w
                if is_primary:
                    primary_matched += 1
                detailed_list.append({
                    "skill": req_clean,
                    "category": "required" if not is_primary else "primary",
                    "matched": True,
                    "weight": round(w, 3)
                })
            else:
                missing_req.append(req_clean)
                detailed_list.append({
                    "skill": req_clean,
                    "category": "required" if not is_primary else "primary",
                    "matched": False,
                    "weight": round(w, 3)
                })

        # 2. Evaluate Preferred Skills (scaled by WEIGHT_PREFERRED_SKILL_RATIO)
        pref_ratio = settings.WEIGHT_PREFERRED_SKILL_RATIO
        for pref in preferred_skills:
            pref_clean = pref.strip()
            if not pref_clean or pref_clean in jd_skills:
                continue

            w = self.get_skill_weight(pref_clean) * pref_ratio
            total_weight += w

            if pref_clean.lower() in resume_set:
                earned_weight += w
                detailed_list.append({
                    "skill": pref_clean,
                    "category": "preferred",
                    "matched": True,
                    "weight": round(w, 3)
                })
            else:
                detailed_list.append({
                    "skill": pref_clean,
                    "category": "preferred",
                    "matched": False,
                    "weight": round(w, 3)
                })

        # 3. Evaluate Responsibilities-Section Skills (scaled by RESPONSIBILITIES_SKILL_RATIO)
        resp_ratio = settings.RESPONSIBILITIES_SKILL_RATIO
        for resp in responsibilities_skills:
            resp_clean = resp.strip()
            if not resp_clean or resp_clean in jd_skills or resp_clean in preferred_skills:
                continue

            w = self.get_skill_weight(resp_clean) * resp_ratio
            total_weight += w

            if resp_clean.lower() in resume_set:
                earned_weight += w
                detailed_list.append({
                    "skill": resp_clean,
                    "category": "responsibilities",
                    "matched": True,
                    "weight": round(w, 3)
                })
            else:
                detailed_list.append({
                    "skill": resp_clean,
                    "category": "responsibilities",
                    "matched": False,
                    "weight": round(w, 3)
                })

        score = (earned_weight / total_weight * 100.0) if total_weight > 0 else 100.0
        score = min(100.0, max(0.0, score))
        matched_ratio = (earned_weight / total_weight) if total_weight > 0 else 0.0

        return {
            "score": round(score, 1),
            "matched": matched_req,
            "missing": missing_req,
            "detailed": detailed_list,
            "matched_ratio": matched_ratio,
            "primary_matched": primary_matched,
            "primary_total": primary_total,
        }

    def _compute_semantic_score(
        self,
        jd_embedding: Sequence[float] | None,
        resume_embedding: Sequence[float] | None,
    ) -> tuple[float, float]:
        """
        Calibrated semantic similarity mapping:
        Maps raw cosine similarity [floor, ceiling] -> [0.0, 100.0].
        Floor is calibrated from unrelated pair percentiles, ceiling from related pairs.
        """
        if jd_embedding is None or resume_embedding is None:
            return 50.0, 0.0

        raw_cos = self.embedder.similarity(jd_embedding, resume_embedding)

        cos_floor = settings.SEMANTIC_COSINE_FLOOR
        cos_ceil = settings.SEMANTIC_COSINE_CEILING

        if raw_cos <= cos_floor:
            norm_score = 0.0
        elif raw_cos >= cos_ceil:
            norm_score = 100.0
        else:
            norm_score = ((raw_cos - cos_floor) / (cos_ceil - cos_floor)) * 100.0

        return round(float(np.clip(norm_score, 0.0, 100.0)), 1), float(raw_cos)

    def _compute_experience_score(
        self,
        jd_exp_years: float | None,
        resume_exp_years: float | None,
        jd_exp_str: str | None = None,
        is_unknown: bool = False,
        roles: list[Any] | None = None,
        jd_embedding: Sequence[float] | None = None,
        relevance_factor: float = 1.0,
    ) -> dict:
        """
        Experience evaluation combining role relevance and continuous relevance modulation.
        """
        req_display = f"{jd_exp_years:g} years" if jd_exp_years is not None else (jd_exp_str or "Not specified")
        actual_display = f"{resume_exp_years:g} years" if resume_exp_years is not None else "Unknown"

        if is_unknown or resume_exp_years is None:
            return {
                "score": 40.0 * relevance_factor,
                "relevant_years": None,
                "comparison": {
                    "required": req_display,
                    "actual": "Unknown",
                    "verdict": "Work experience duration could not be determined from document; evaluated with neutral baseline.",
                    "meets_requirement": False,
                }
            }

        required_years = jd_exp_years if jd_exp_years is not None else 2.0
        actual_years = resume_exp_years

        # Calculate relevant experience years via role relevance
        # If roles are provided with descriptions, compute embedding similarity to JD
        relevant_years = actual_years
        if roles and jd_embedding:
            weighted_months = 0.0
            total_role_months = 0.0
            for r in roles:
                role_text = f"{r.title} {r.company} {r.description}"
                role_emb = self.embedder.embed(role_text)
                sim = self.embedder.similarity(role_emb, jd_embedding)
                # Map similarity to role weight w in [0.2, 1.0]
                role_w = float(np.clip((sim - 0.3) / 0.4, 0.2, 1.0))
                weighted_months += r.duration_months * role_w
                total_role_months += r.duration_months

            if total_role_months > 0:
                relevant_years = round((weighted_months / total_role_months) * actual_years, 1)

        # Graduated ratio curve
        ratio = relevant_years / required_years if required_years > 0 else 1.0

        if ratio >= 1.0:
            raw_score = 100.0
            verdict = f"Meets or exceeds requirement ({actual_years:g} years actual, {relevant_years:g} relevant vs {required_years:g} required)."
            meets = True
        elif ratio >= 0.7:
            raw_score = 70.0 + ((ratio - 0.7) / 0.3) * 30.0
            verdict = f"Close to requirement ({actual_years:g} years actual, {relevant_years:g} relevant vs {required_years:g} required)."
            meets = False
        else:
            raw_score = (ratio / 0.7) * 70.0
            verdict = f"Below requirement ({actual_years:g} years actual vs {required_years:g} required)."
            meets = False

        # Continuous smooth relevance modulation
        score = raw_score * relevance_factor
        if relevance_factor < 0.6:
            verdict += f" Credited at {relevance_factor*100:.0f}% relevance factor due to domain skill alignment."

        return {
            "score": round(max(0.0, min(100.0, score)), 1),
            "relevant_years": relevant_years,
            "comparison": {
                "required": req_display,
                "actual": actual_display,
                "verdict": verdict,
                "meets_requirement": meets,
            }
        }

    def _compute_qualification_score(
        self,
        jd_qualifications: list[str],
        resume_education: list[str],
        degree_details: list[dict] | None = None,
        relevance_factor: float = 1.0,
    ) -> dict:
        """
        Degree level and semantic field alignment:
        - Resolves 'Bachelor's or Master's' clauses to minimum acceptable tier.
        - Evaluates field relevance against JD requested fields via embeddings, taxonomy clusters, and direct keyword matches.
        - Educational credential scoring is independent of technical skill overlap.
        """
        if not jd_qualifications:
            return {
                "score": 100.0,
                "audit": {"required_level": "none", "candidate_level": "any", "field_relevance": 100.0}
            }

        if not resume_education:
            return {
                "score": 35.0,
                "audit": {"required_level": "bachelor", "candidate_level": "omitted", "field_relevance": 0.0}
            }

        degree_levels = self.degrees_tax.get("degree_levels", {})
        stem_quant = self.degrees_tax.get("stem_quant_clusters", [])
        biz_marketing = self.degrees_tax.get("business_marketing_clusters", [])
        all_clusters = [c for c in [stem_quant, biz_marketing] if c]

        # 1. Parse minimum acceptable degree level from JD
        jd_text = " ".join(jd_qualifications).lower()
        levels_mentioned = []
        for deg_name, lvl in degree_levels.items():
            if re.search(r"\b" + re.escape(deg_name) + r"\b", jd_text):
                levels_mentioned.append(lvl)

        # Handle 'Bachelor's or Master's' OR-clauses: minimum degree satisfies requirement
        if levels_mentioned:
            req_level = min(levels_mentioned)
        else:
            req_level = 2  # Default to Bachelor's

        # 2. Detect candidate's highest degree level
        cand_level = 0
        res_text = " ".join(resume_education).lower()
        for deg_name, lvl in degree_levels.items():
            if re.search(r"\b" + re.escape(deg_name) + r"\b", res_text):
                cand_level = max(cand_level, lvl)

        if degree_details:
            for d in degree_details:
                lvl = d.get("level", 0)
                if lvl > cand_level:
                    cand_level = lvl

        # 3. Multi-Domain Semantic Field Alignment
        # Check if JD specifies any specific field requirement
        has_field_req = False
        jd_cluster_matches = []
        for cluster in all_clusters:
            for term in cluster:
                if re.search(r"\b" + re.escape(term) + r"\b", jd_text):
                    has_field_req = True
                    jd_cluster_matches.append(cluster)
                    break

        # Check candidate's cluster alignments
        cand_matches_stem = any(re.search(r"\b" + re.escape(term) + r"\b", res_text) for term in stem_quant)

        # Direct keyword overlap: e.g. "information technology", "computer science" in both JD and resume
        direct_keyword_overlap = False
        for cluster in all_clusters:
            for term in cluster:
                if re.search(r"\b" + re.escape(term) + r"\b", jd_text) and re.search(r"\b" + re.escape(term) + r"\b", res_text):
                    direct_keyword_overlap = True
                    break
            if direct_keyword_overlap:
                break

        # Semantic field similarity against JD education requirements
        jd_field_emb = self.embedder.embed(jd_text)
        res_edu_emb = self.embedder.embed(res_text)
        field_sim = float(self.embedder.similarity(jd_field_emb, res_edu_emb))

        # Cluster match: candidate belongs to the same cluster the JD targets
        same_cluster_match = any(
            any(re.search(r"\b" + re.escape(t) + r"\b", res_text) for t in cl)
            for cl in jd_cluster_matches
        )

        is_related_field = False
        if not has_field_req and field_sim >= 0.40:
            field_matched = True
        elif direct_keyword_overlap or same_cluster_match:
            field_matched = True
        elif cand_matches_stem and any(k in jd_text for k in ("computer", "software", "developer", "engineer", "data", "technology", "technical")):
            field_matched = True
        elif field_sim >= 0.55:
            field_matched = True
        elif field_sim >= 0.48:
            field_matched = False
            is_related_field = True
        else:
            field_matched = False

        # 4. Transparent Tier Scoring (Credential Compliance)
        if cand_level >= req_level:
            if field_matched:
                base_score = 100.0
            elif is_related_field:
                base_score = 80.0
            else:
                base_score = 40.0
        elif cand_level == req_level - 1:
            base_score = 75.0 if field_matched else (60.0 if is_related_field else 25.0)
        elif cand_level > 0:
            base_score = 50.0 if field_matched else 15.0
        else:
            base_score = 20.0 if field_matched else 0.0

        # 5. In-progress degree deduction (Part 3.7)
        is_in_progress = False
        in_progress_deduction = 0.0
        if degree_details:
            qualifying_degrees = [d for d in degree_details if d.get("level", 0) >= req_level]
            if qualifying_degrees and all(d.get("is_completed") is False for d in qualifying_degrees):
                is_in_progress = True
                in_progress_deduction = settings.IN_PROGRESS_DEGREE_PENALTY
                base_score = max(0.0, base_score - in_progress_deduction)

        final_score = base_score

        return {
            "score": round(max(0.0, min(100.0, final_score)), 1),
            "audit": {
                "jd_required_level": req_level,
                "candidate_level": cand_level,
                "field_matched": field_matched,
                "field_similarity": round(field_sim, 3),
                "is_in_progress": is_in_progress,
                "in_progress_penalty": in_progress_deduction,
            }
        }

    def _generate_explanation(
        self,
        name: str,
        overall: float,
        skill_score: float,
        matched_skills: list[str],
        missing_skills: list[str],
        sem_score: float,
        exp_comparison: dict,
        qual_score: float,
        is_zero_skill_jd: bool,
        relevance_factor: float,
        exp_source: str,
        warnings: list[str],
    ) -> str:
        """Construct transparent, plain-English scoring rationale."""
        total_skills = len(matched_skills) + len(missing_skills)
        matched_count = len(matched_skills)

        parts = [f"{name} achieved an overall match score of {overall:.1f}%."]

        if is_zero_skill_jd:
            parts.append("Role specifies no cataloged technical skills; evaluation prioritized contextual semantic similarity and domain experience.")
        elif total_skills > 0:
            if matched_count > 0:
                sample_matched = ", ".join(matched_skills[:5])
                parts.append(f"Matched {matched_count} of {total_skills} required skills ({sample_matched}).")
            else:
                parts.append(f"Matched 0 of {total_skills} required technical skills.")

            if missing_skills:
                sample_missing = ", ".join(missing_skills[:4])
                overflow = f" (+{len(missing_skills)-4} more)" if len(missing_skills) > 4 else ""
                parts.append(f"Key missing skills: {sample_missing}{overflow}.")

        # Experience
        verdict = exp_comparison.get("verdict", "")
        if verdict:
            parts.append(f"Experience: {verdict}")

        # Semantic
        if sem_score >= 80.0:
            parts.append("Project and work history exhibit strong contextual alignment with role objectives.")
        elif sem_score <= 35.0:
            parts.append("Resume exhibits limited semantic alignment with the specific focus areas of this JD.")

        # Relevance modulation
        if relevance_factor < 0.6:
            parts.append(f"Continuous domain relevance factor applied: {relevance_factor*100:.0f}%.")

        return " ".join(parts)
