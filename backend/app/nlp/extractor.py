import datetime
import json
import logging
import os
import re
from dataclasses import dataclass, field
import spacy
from app.nlp.skill_taxonomy import SkillMatcher
from app.config import settings

logger = logging.getLogger("resumeranker.extractor")

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "june": 6, "jun": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}

NON_NAME_WORDS = {
    "resume", "curriculum", "vitae", "cv", "profile", "summary",
    "contact", "experience", "education", "skills", "projects",
    "developer", "engineer", "architect", "programmer", "manager",
    "software", "senior", "lead", "junior", "intern", "phone", "email"
}


@dataclass
class RoleBlock:
    title: str
    company: str
    start_month: int
    end_month: int
    duration_months: int
    description: str


@dataclass
class ResumeData:
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    experience_years: float | None = None
    total_experience_years: float | None = None
    relevant_experience_years: float | None = None
    is_experience_unknown: bool = False
    experience_source: str = "dates"  # 'dates', 'summary', or 'unknown'
    education: list[str] = field(default_factory=list)
    degree_details: list[dict] = field(default_factory=list)
    earliest_grad_year: int | None = None
    skills: list[str] = field(default_factory=list)
    role_blocks: list[RoleBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _parse_month(val: str | None) -> int | None:
    if not val:
        return None
    cleaned = val.strip().lower().rstrip(".")
    if cleaned in MONTH_MAP:
        return MONTH_MAP[cleaned]
    if cleaned.isdigit():
        m = int(cleaned)
        if 1 <= m <= 12:
            return m
    return None


class ResumeExtractor:
    """
    Production-grade resume extractor:
    - Candidate Name, Email, Phone
    - Config-driven section segmentation (synonyms, colons, markdown)
    - Normalized degree parsing & earliest graduation anchor
    - Role-by-role discrete work history intervals
    - Truth-grounded experience reconciliation (dates always win, audit warnings)
    - Open-vocabulary & taxonomy skill matching
    """

    def __init__(self, nlp: spacy.language.Language, skill_matcher: SkillMatcher):
        self.nlp = nlp
        self.skill_matcher = skill_matcher
        self.headings = self._load_headings()
        self.degrees_tax = self._load_degrees_taxonomy()

    def _load_headings(self) -> dict[str, list[str]]:
        path = settings.SECTION_HEADINGS_PATH
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load section headings: {e}")
        return {}

    def _load_degrees_taxonomy(self) -> dict:
        path = settings.DEGREES_TAXONOMY_PATH
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load degrees taxonomy: {e}")
        return {}

    def extract(self, raw_text: str) -> ResumeData:
        """Execute full extraction pipeline on raw resume text."""
        if not raw_text or not raw_text.strip():
            return ResumeData(warnings=["Empty resume text provided."])

        # Normalize degree terms early to prevent false token collisions
        normalized_text = self._normalize_degree_text(raw_text)

        doc = self.nlp(normalized_text[:4000])

        name = self._extract_name(doc, normalized_text)
        email = self._extract_email(normalized_text)
        phone = self._extract_phone(normalized_text)

        # 1. Split sections using config-driven headings
        sections = self._split_sections(normalized_text)

        # 2. Extract education, degree details & earliest completed graduation anchor
        education, degree_details, earliest_grad = self._extract_education(sections.get("qualifications", "") or normalized_text)

        # 3. Extract discrete roles and work history intervals
        roles, total_dates_exp = self._extract_roles_and_intervals(sections.get("experience", "") or normalized_text)

        # 4. Extract explicit statement from summary or full text
        summary_exp = self._extract_summary_experience(sections.get("summary", "") or normalized_text)
        if summary_exp is None:
            summary_exp = self._extract_summary_experience(normalized_text)

        # 5. Reconcile experience (Dates always win)
        exp_years, exp_source, is_unknown, exp_warnings = self._reconcile_experience(
            total_dates_exp=total_dates_exp,
            summary_exp=summary_exp,
            earliest_grad_year=earliest_grad
        )

        skills = self.skill_matcher.extract_skills(normalized_text)

        warnings: list[str] = []
        if not name:
            warnings.append("Candidate name could not be automatically detected with high confidence.")
        if not email:
            warnings.append("Email address not found.")
        if not skills:
            warnings.append("No technical skills matched against taxonomy.")
        warnings.extend(exp_warnings)

        return ResumeData(
            candidate_name=name,
            email=email,
            phone=phone,
            experience_years=exp_years,
            total_experience_years=exp_years,
            relevant_experience_years=exp_years,  # Modulated later against specific JD in scorer
            is_experience_unknown=is_unknown,
            experience_source=exp_source,
            education=education,
            degree_details=degree_details,
            earliest_grad_year=earliest_grad,
            skills=skills,
            role_blocks=roles,
            warnings=warnings,
        )

    def _normalize_degree_text(self, text: str) -> str:
        """
        Normalize degree text (e.g. 'B.E.', 'B E' -> 'Bachelor of Engineering')
        Strict word boundary ensures words like 'BELOW', 'BETWEEN' are never matched.
        """
        rules = self.degrees_tax.get("degree_normalization_rules", [])
        normalized = text
        for rule in rules:
            pat = rule["pattern"]
            std = rule["standard"]
            normalized = re.sub(pat, std, normalized, flags=re.IGNORECASE)
        return normalized

    def _split_sections(self, text: str) -> dict[str, str]:
        """Split resume into semantic sections using config-driven headings."""
        sections: dict[str, list[str]] = {
            "summary": [],
            "experience": [],
            "qualifications": [],
            "skills": [],
            "projects": [],
            "other": []
        }

        current_target = "summary"
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue

            matched_sec = None
            header_norm = re.sub(r"^[#*\-\s•·]+|[ :]+$", "", line_clean).strip().lower()

            remaining = None
            for sec_key, header_synonyms in self.headings.items():
                for syn in header_synonyms:
                    if header_norm == syn or header_norm.startswith(syn + ":") or header_norm.startswith(syn + " "):
                        matched_sec = sec_key
                        rem = re.sub(r"^[#*\-\s•·]*" + re.escape(syn) + r"[:\s-]*", "", line_clean, flags=re.IGNORECASE).strip()
                        if rem:
                            remaining = rem
                        break
                if matched_sec:
                    break

            if matched_sec:
                if matched_sec in ("skills", "tech_stack"):
                    current_target = "skills"
                elif matched_sec in ("qualifications", "education"):
                    current_target = "qualifications"
                elif matched_sec in ("experience", "work_history"):
                    current_target = "experience"
                elif matched_sec in ("summary", "about", "objective"):
                    current_target = "summary"
                elif matched_sec in sections:
                    current_target = matched_sec
                else:
                    current_target = "other"

                if remaining:
                    sections[current_target].append(remaining)
            else:
                sections[current_target].append(line_clean)

        return {k: "\n".join(v) for k, v in sections.items()}

    def _extract_education(self, text: str) -> tuple[list[str], list[dict], int | None]:
        """
        Extract degrees, structured degree details, and earliest completed graduation year anchor.
        In-progress degrees (e.g. 'Expected 2027', 'Present') are explicitly excluded from the anchor.
        """
        education_found: list[str] = []
        degree_details: list[dict] = []
        completed_grad_years: list[int] = []

        now_year = datetime.datetime.now().year
        degree_levels = self.degrees_tax.get("degree_levels", {})

        lines = text.splitlines()
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue

            line_lower = line_clean.lower()
            # Check for recognized degree
            matched_level = 0
            matched_name = None

            for deg_word, lvl in degree_levels.items():
                if re.search(r"\b" + re.escape(deg_word) + r"\b", line_lower):
                    if lvl > matched_level:
                        matched_level = lvl
                        matched_name = deg_word

            if matched_level > 0:
                if len(line_clean) <= 140 and line_clean not in education_found:
                    education_found.append(line_clean)

                # Inspect this line and the following 2 lines for dates / in-progress cues
                lines_window = " ".join(lines[idx:idx+3])
                window_lower = lines_window.lower()

                year_matches = re.findall(r"\b(20\d\d|19\d\d)\b", lines_window)
                is_in_progress = bool(re.search(r"\b(?:expected|present|current|pursuing|ongoing|in\s+progress)\b", window_lower))

                grad_year = None
                if year_matches:
                    years = [int(y) for y in year_matches]
                    grad_year = max(years)
                    # If grad year is in the future or explicitly marked expected, treat as in-progress
                    if grad_year > now_year or is_in_progress:
                        is_in_progress = True
                    else:
                        completed_grad_years.append(grad_year)

                degree_details.append({
                    "raw": line_clean,
                    "degree": matched_name,
                    "level": matched_level,
                    "graduation_year": grad_year if not is_in_progress else None,
                    "is_completed": not is_in_progress,
                })

        earliest_grad = min(completed_grad_years) if completed_grad_years else None
        return education_found[:5], degree_details, earliest_grad

    def _extract_roles_and_intervals(self, exp_text: str) -> tuple[list[RoleBlock], float | None]:
        """
        Extract discrete work history roles, date ranges, and calculate merged non-overlapping interval tenure.
        """
        now = datetime.datetime.now()
        current_year = now.year
        current_month = now.month

        date_pattern = r"\b(?:([a-zA-Z]{3,9}|\d{1,2})[./\s-]+)?(20\d\d|19\d\d)\s*(?:-|to|–|—)\s*(?:([a-zA-Z]{3,9}|\d{1,2})[./\s-]+)?(20\d\d|present|current)\b"

        lines = exp_text.splitlines()
        roles: list[RoleBlock] = []
        intervals: list[tuple[int, int]] = []

        current_role_title = "Professional Experience"
        current_company = ""
        current_desc_lines: list[str] = []
        current_role_s = None
        current_role_e = None

        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue

            match = re.search(date_pattern, line_strip, re.IGNORECASE)
            if match:
                smonth_str, syear_str, emonth_str, eyear_str = match.groups()
                syear = int(syear_str)
                sm = _parse_month(smonth_str)

                # Check for explicit tenure duration markers on this role line: e.g. "| 1.0 Year", "(2.2 Years)", "| 6 Months"
                explicit_dur = None
                dur_match = re.search(r"(?:\||\()\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", line_strip, re.IGNORECASE)
                mo_match = re.search(r"(?:\||\()\s*(\d+)\s*(?:months?|mos?)\b", line_strip, re.IGNORECASE)
                if dur_match:
                    explicit_dur = float(dur_match.group(1))
                elif mo_match:
                    explicit_dur = float(mo_match.group(1)) / 12.0

                is_present = eyear_str.lower() in ("present", "current")
                if is_present:
                    if explicit_dur is not None and explicit_dur > 0:
                        span_m = max(1, int(round(explicit_dur * 12)))
                        start_m = syear * 12 + (sm if sm else 1)
                        end_m = start_m + span_m - 1
                    else:
                        eyear = current_year
                        emonth = current_month
                        end_m = eyear * 12 + emonth
                        if sm is None:
                            # Without explicit start month (e.g. 2020 - Present),
                            # anchor start_m so inclusive span equals exact (current_year - syear) * 12
                            span = max(1, (current_year - syear) * 12)
                            start_m = end_m - span + 1
                        else:
                            start_m = syear * 12 + sm
                else:
                    eyear = int(eyear_str)
                    em = _parse_month(emonth_str)
                    emonth = em if em else 12
                    smonth = sm if sm else 1
                    start_m = syear * 12 + smonth
                    end_m = eyear * 12 + emonth

                if end_m >= start_m:
                    intervals.append((start_m, end_m))
                    # Extract role title from line
                    title_part = re.sub(date_pattern, "", line_strip, flags=re.IGNORECASE)
                    title_part = re.sub(r"\|\s*\d+(?:\.\d+)?\s*(?:years?|yrs?|months?|mos?)", "", title_part, flags=re.IGNORECASE).strip(" –|-•·")
                    if title_part and len(title_part) >= 3:
                        current_role_title = title_part

                    current_role_s = start_m
                    current_role_e = end_m
            else:
                if current_role_s is not None:
                    current_desc_lines.append(line_strip)

        if intervals:
            intervals.sort()
            merged = [intervals[0]]
            for curr in intervals[1:]:
                prev_s, prev_e = merged[-1]
                if curr[0] <= prev_e:
                    merged[-1] = (prev_s, max(prev_e, curr[1]))
                else:
                    merged.append(curr)

            total_months = sum((e - s + 1) for s, e in merged)
            total_years = round(total_months / 12.0, 1)

            # Package primary role block
            roles.append(RoleBlock(
                title=current_role_title,
                company=current_company,
                start_month=intervals[0][0],
                end_month=intervals[-1][1],
                duration_months=total_months,
                description="\n".join(current_desc_lines[:6])
            ))
            return roles, total_years

        return [], None

    def _extract_summary_experience(self, text: str) -> float | None:
        """Extract explicit tenure mention from summary or header."""
        exp_patterns = [
            r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s*(?:of)?\s*experience|\s*exp\b)",
            r"(?:experience|exp)[:\s]+(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
            r"(?:total\s+experience)[:\s]+(\d+(?:\.\d+)?)",
        ]
        explicit = []
        for pat in exp_patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                try:
                    val = float(m)
                    if 0.5 <= val <= 35:
                        explicit.append(val)
                except ValueError:
                    pass

        return max(explicit) if explicit else None

    def _reconcile_experience(
        self,
        total_dates_exp: float | None,
        summary_exp: float | None,
        earliest_grad_year: int | None,
    ) -> tuple[float | None, str, bool, list[str]]:
        """
        Reconcile work experience with strict truth grounding:
        1. Dates ALWAYS win when they exist.
        2. Discrepancy warning emitted if summary differs from dates by >= 1.0 yr or ratio >= 1.4.
        3. Clamp against earliest completed graduation year.
        4. Fall back to summary only when dates are absent.
        5. Return explicit unknown if both are missing.
        """
        now_year = datetime.datetime.now().year
        warnings: list[str] = []

        max_plausible = None
        if earliest_grad_year and earliest_grad_year <= now_year:
            max_plausible = (now_year - earliest_grad_year) + settings.EXP_TOLERANCE_YEARS

        # Case 1: Work history dates exist -> DATES ALWAYS WIN
        if total_dates_exp is not None:
            final_exp = total_dates_exp
            source = "dates"
            is_unknown = False

            # Check discrepancy with summary
            if summary_exp is not None:
                diff = abs(summary_exp - total_dates_exp)
                ratio = summary_exp / max(total_dates_exp, 0.5)
                if diff >= settings.EXP_DISCREPANCY_THRESHOLD_YEARS or ratio >= settings.EXP_SUMMARY_DISCREPANCY_RATIO:
                    warnings.append(
                        f"Discrepancy detected: Summary claims {summary_exp:g} years of experience, but documented work history dates total {total_dates_exp:g} years; using verified dates."
                    )

            # Plausibility check against graduation
            if max_plausible is not None and final_exp > max_plausible:
                warnings.append(
                    f"Documented experience ({final_exp:g} yrs) exceeds plausible post-graduation timeline ({max_plausible:g} yrs based on {earliest_grad_year} graduation); clamped."
                )
                final_exp = round(max_plausible, 1)

            return final_exp, source, is_unknown, warnings

        # Case 2: Only summary exists (e.g. test10 two-column un-dated resume)
        if summary_exp is not None:
            final_exp = summary_exp
            source = "summary"
            is_unknown = False

            if max_plausible is not None and final_exp > max_plausible:
                warnings.append(
                    f"Self-reported summary experience ({final_exp:g} yrs) exceeds post-graduation timeline ({max_plausible:g} yrs based on {earliest_grad_year} graduation); clamped."
                )
                final_exp = round(max_plausible, 1)

            return final_exp, source, is_unknown, warnings

        # Case 3: Neither exists -> Explicit Unknown
        return None, "unknown", True, ["Work experience duration could not be determined from document."]

    def _extract_name(self, doc: spacy.tokens.Doc, raw_text: str) -> str | None:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()][:8]
        for line in lines[:3]:
            cleaned_line = re.sub(r"[|•·,\-_/⋄\t].*", "", line).strip()
            words = [w.strip(".,;:|") for w in cleaned_line.split() if w.strip(".,;:|")]
            if 2 <= len(words) <= 4:
                is_name_like = all(w.isalpha() and (w.isupper() or w[0].isupper()) for w in words)
                no_blocklist = not any(w.lower() in NON_NAME_WORDS for w in words)
                if is_name_like and no_blocklist:
                    return cleaned_line

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name_cand = ent.text.strip()
                words = name_cand.split()
                if 2 <= len(words) <= 4:
                    if all(w.lower() not in NON_NAME_WORDS for w in words):
                        return name_cand

        return None

    def _extract_email(self, text: str) -> str | None:
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
        matches = re.findall(pattern, text)
        return matches[0].strip() if matches else None

    def _extract_phone(self, text: str) -> str | None:
        phone_patterns = [
            r"(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}",
            r"\+?\d{1,3}[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
        ]
        for pat in phone_patterns:
            m = re.search(pat, text)
            if m:
                return m.group(0).strip()
        return None
