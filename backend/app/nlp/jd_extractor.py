import json
import logging
import os
import re
from dataclasses import dataclass, field
import spacy
from app.nlp.skill_taxonomy import SkillMatcher
from app.config import settings

logger = logging.getLogger("resumeranker.jd_extractor")

# Generic stoplist for open-vocabulary skill extraction
JUNK_WORDS_STOPLIST = {
    "experience", "experiences", "years", "year", "team", "teams", "work", "works",
    "working", "project", "projects", "role", "roles", "candidate", "candidates",
    "responsibility", "responsibilities", "skill", "skills", "ability", "abilities",
    "knowledge", "understanding", "tools", "tool", "technologies", "technology",
    "environment", "environments", "production", "development", "developer",
    "engineering", "engineer", "client", "clients", "stakeholder", "stakeholders",
    "communication", "problem", "solving", "analytical", "business", "solution",
    "solutions", "industry", "practice", "practices", "best", "minimum", "degree",
    "field", "hands", "track", "record", "plus", "bonus", "fast", "paced", "high",
    "impact", "qualifications", "qualification", "education", "relevant", "proficient",
    "strong", "solid", "excellent", "familiarity", "exposure", "building", "designing",
    "deploying", "creating", "managing", "writing", "leading", "support", "services",
    "related", "preferred", "required", "level", "demonstrated", "proven", "good",
    "it", "etc", "e.g", "i.e", "department", "location", "reporting", "salary",
    "ctc", "notice", "benefits", "employment", "type"
}

# Generic non-skill phrases that must not become required technical skills
GENERIC_DISCARD_PHRASES = {
    "cloud services", "sql databases", "database concepts", "web services",
    "software development", "programming", "development", "data preprocessing",
    "cloud platforms", "relational databases", "messaging systems", "orm concepts",
    "jdbc/orm concepts", "cloud experience on aws", "strong sql skills", "core java: oop",
    "sql indexing", "aws cloud deployment", "code review", "peer code review",
    "agile development", "agile/scrum environment", "sprint planning",
    "production issues", "cross-browser", "performance issues",
    "orms", "orm", "databases", "deployment experience with aws", "deployment experience",
    "cloud deployment", "relational database"
}

LEAD_IN_PATTERNS = [
    r"^(?:(?:deep\s+)?expertise\s+in|hands-on\s+experience\s+with|experience\s+with|experience\s+running|experience\s+building|experience\s+integrating|experience\s+in|working\s+knowledge\s+of|good\s+knowledge\s+of|solid\s+knowledge\s+of|solid\s+understanding\s+of|strong\s+command\s+of|strong\s+knowledge\s+of|deep\s+expertise\s+in|proven\s+track\s+record\s+(?:in|with)|track\s+record\s+with|strong\s+proficiency\s+in|proficiency\s+in|proficient\s+in|must\s+be\s+proficient\s+in|must\s+have\s+experience\s+with|must\s+have|skilled\s+in|familiarity\s+with|exposure\s+to|knowledge\s+of|cloud\s+experience\s+on|at\s+least\s+one\s+cloud\s+platform:?)\s*",
    r"^(?:experience\s+with\s+(?:mlops\s+tools|vector\s+databases|data\s+visualization|messaging\s+systems|cloud\s+platforms?|relational\s+databases|email\s+marketing\s+tools|crm\s+tools|tools)\s+such\s+as)\s*",
    r"^(?:vector\s+databases\s+such\s+as|messaging\s+systems\s+such\s+as|mlops\s+tools\s+such\s+as|email\s+marketing\s+tools\s+such\s+as|tools\s+such\s+as|libraries\s+such\s+as|databases\s+such\s+as|such\s+as)\s*",
    r"^(?:integrate\s+messaging\s+systems\s+such\s+as|cloud\s+experience\s+on|at\s+least\s+one\s+cloud\s+platform:?)\s*",
    r"^(?:unit\s+testing\s+using|data\s+visualization\s+using|testing\s+using|using)\s*",
    r"^(?:relational\s+databases\s+such\s+as|relational\s+database\s+schemas\s+and\s+optimize)\s*",
    r"^(?:strong|solid|deep|good|basic|extensive|hands-on|proven|core)\s+",
]

TRAILING_NOISE_PATTERNS = [
    r"\s+(?:for\s+asynchronous\s+workflows|for\s+pipelines|for\s+inference|in\s+production|and\s+data\s+preprocessing\s+techniques|and\s+exception\s+handling|and\s+query\s+optimization|cloud\s+deployment|indexing|deployment)\.?$",
    r"\s+(?:skills?|concepts?|techniques?|best\s+practices|frameworks?|libraries?|databases?|tools?|services?|platforms?|workflows?|methodologies?|management|strategies?|optimization)\.?$",
    r"[.,;:]+$",
]


@dataclass
class JDData:
    title: str | None = None
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    primary_skills: list[str] = field(default_factory=list)
    responsibilities_skills: list[str] = field(default_factory=list)
    or_groups: list[list[str]] = field(default_factory=list)
    experience_required: str | None = None
    experience_years: float | None = None
    qualifications: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    uncatalogued_terms: list[str] = field(default_factory=list)


class JDExtractor:
    """
    Extracts structured requirements and criteria from a Job Description:
    - Clean Job Title
    - Primary Domain Skills (from Title, frequency, and first requirements)
    - Required Skills vs Preferred Skills (Strict section isolation: preferred is NEVER required)
    - Responsibilities-section skills (evaluated at lower configurable weight)
    - Sentence-scoped, non-overlapping OR-groups with parenthetical preservation
    - General phrase normalization: strips lead-ins, splits compounds, drops generic noise
    - Domain-agnostic open-vocabulary skill extraction (Tech, Marketing, Design, Finance)
    - Years of Experience Required
    - Educational Qualifications
    """

    def __init__(self, nlp: spacy.language.Language, skill_matcher: SkillMatcher):
        self.nlp = nlp
        self.skill_matcher = skill_matcher
        self.headings = self._load_headings()

    def _load_headings(self) -> dict[str, list[str]]:
        path = settings.SECTION_HEADINGS_PATH
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load section headings: {e}")
        return {}

    def extract(self, raw_text: str) -> JDData:
        """Execute full extraction pipeline on raw JD text."""
        if not raw_text or not raw_text.strip():
            return JDData()

        title = self._extract_title(raw_text)
        exp_req_str, exp_years = self._extract_experience(raw_text)
        sections = self._split_sections(raw_text)

        req_text = sections.get("requirements", "")
        pref_text = sections.get("preferred", "")
        tech_text = sections.get("tech_stack", "")
        qual_text = sections.get("qualifications", "")
        resp_text = sections.get("responsibilities", "")

        # 1. Extract skills per section
        req_extracted, uncat_req = self._extract_skills_from_section(req_text)
        pref_extracted, uncat_pref = self._extract_skills_from_section(pref_text)
        tech_extracted, uncat_tech = self._extract_skills_from_section(tech_text)
        resp_extracted, uncat_resp = self._extract_skills_from_section(resp_text)

        # 2. Strict Section Provenance Rule:
        # A skill in the preferred section is NEVER required!
        preferred_set = set(pref_extracted)

        # If a skill was extracted in tech_stack, check if it was preferred
        required_set = set()
        for s in (req_extracted + tech_extracted):
            if s not in preferred_set:
                required_set.add(s)

        # Responsibilities skills (lower weight, only if not in required or preferred)
        responsibilities_skills = sorted(list(set(resp_extracted) - required_set - preferred_set))

        # 3. Sentence-scoped OR-groups (no overlap, parenthetical preservation)
        or_groups = self._extract_or_groups(req_text + "\n" + pref_text)

        # 4. Primary Domain Skill Identification (Title, Prominence, Frequency, and OR-group hierarchy)
        primary_skills = self._extract_primary_skills(title, list(required_set), raw_text, or_groups)

        # Aggregate uncatalogued terms
        all_uncatalogued = sorted(list(set(uncat_req + uncat_pref + uncat_tech + uncat_resp)))

        # Document-wide degree qualification fallback
        qualifications = self._extract_qualifications(qual_text) if qual_text else []
        if not qualifications:
            qualifications = self._extract_qualifications(raw_text)
        responsibilities = self._extract_responsibilities(resp_text or raw_text)

        return JDData(
            title=title,
            required_skills=sorted(list(required_set)),
            preferred_skills=sorted(list(preferred_set)),
            primary_skills=primary_skills,
            responsibilities_skills=responsibilities_skills,
            or_groups=or_groups,
            experience_required=exp_req_str,
            experience_years=exp_years,
            qualifications=qualifications,
            responsibilities=responsibilities,
            uncatalogued_terms=all_uncatalogued,
        )

    def _extract_title(self, text: str) -> str:
        """Detect clean job title prioritizing document headers."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return "Job Description"

        for line in lines[:4]:
            if re.match(r"^(?:company|location|date|department|employment)[:\s]", line, re.IGNORECASE):
                continue
            cleaned = re.sub(r"^(?:job\s+title|role|position)[:\s-]+", "", line, flags=re.IGNORECASE).strip()
            if 3 <= len(cleaned) <= 60 and not cleaned.endswith("."):
                return cleaned

        title_patterns = [
            r"(?:job\s+title|role|position)[:\s]+([^\n\r|•]+)",
            r"(?:we\s+are\s+looking\s+for\s+(?:a|an)?\s+)([A-Z][a-zA-Z\s]{3,40})(?:\s+to|\s+who|\.)",
        ]
        for pat in title_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                if 3 <= len(extracted) <= 50:
                    return extracted

        return lines[0][:50]

    def _extract_experience(self, text: str) -> tuple[str | None, float | None]:
        """Extract experience requirement (e.g. '3-5 years', 3.0)."""
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
            r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s*(?:of)?\s*experience)?",
            r"(?:minimum|at\s+least)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                full_match = m.group(0).strip()
                first_num = float(m.group(1))
                return full_match, first_num

        return None, None

    def _split_sections(self, text: str) -> dict[str, str]:
        """
        Segment JD text into semantic sections using strict header boundaries.
        Prevents bullet lines and document body text from triggering false section changes.
        """
        sections: dict[str, list[str]] = {
            "requirements": [],
            "preferred": [],
            "qualifications": [],
            "responsibilities": [],
            "tech_stack": [],
            "benefits": [],
            "overview": [],
        }

        current_targets: list[str] = ["overview"]
        lines = text.splitlines()

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            matched_targets = self._detect_section_header(line_clean)
            if matched_targets:
                current_targets = matched_targets
            else:
                for tgt in current_targets:
                    if tgt in sections:
                        sections[tgt].append(line_clean)

        return {k: "\n".join(v) for k, v in sections.items()}

    def _detect_section_header(self, line: str) -> list[str]:
        """Check if a line functions as a structural section header."""
        if not line or len(line) > 60:
            return []
        # Cannot start with a bullet point
        if re.match(r"^[-*•·\d.]+\s*", line) and not re.match(r"^\d+\.\s+[A-Z]", line):
            return []
        # Exclude metadata key-value lines
        if re.match(r"^(?:company|location|date|department|employment\s+type|email|phone|ctc|salary|experience\s+required)[:\s]", line, re.I):
            return []

        norm = re.sub(r"^[#*\-\s•·]+|[ :]+$", "", line).strip().lower()
        matched = []
        for sec_key, synonyms in self.headings.items():
            for syn in synonyms:
                if norm == syn or norm.startswith(syn + ":") or norm.startswith(syn + " -"):
                    matched.append(sec_key)
                    break
                elif len(syn) >= 8 and syn in norm:
                    matched.append(sec_key)
                    break

        # Explicit Compound Intent: headers expressing both requirements/skills AND qualifications/education
        has_req_intent = any(w in norm for w in ("requirement", "requirements", "skills", "must have", "what you need"))
        has_qual_intent = any(w in norm for w in ("qualification", "qualifications", "education", "degree", "academic"))
        if has_req_intent and has_qual_intent:
            if "requirements" not in matched:
                matched.append("requirements")
            if "qualifications" not in matched:
                matched.append("qualifications")

        return list(set(matched))

    def _clean_skill_phrase(self, phrase: str) -> str:
        """Strip lead-in filler words, unclosed parentheticals, and trailing noise."""
        p = phrase.strip()
        p = re.sub(r"Meta\s*\([^)]*\)\s*Ads", "Meta Ads", p, flags=re.I)
        p = re.sub(r"\(.*?\)", "", p).strip()
        for pat in LEAD_IN_PATTERNS:
            p = re.sub(pat, "", p, flags=re.IGNORECASE).strip()
        for pat in TRAILING_NOISE_PATTERNS:
            p = re.sub(pat, "", p, flags=re.IGNORECASE).strip()
        p = re.sub(r"^[(\[{]+|[)\]}]+$", "", p).strip()
        p = re.sub(r"^(?:or|and|such\s+as|including)\s+", "", p, flags=re.I).strip()
        p = re.sub(r"\s+(?:or|and)$", "", p, flags=re.I).strip()
        if p.count("(") != p.count(")"):
            p = re.sub(r"\(.*$", "", p).strip()
            p = re.sub(r"^.*\)", "", p).strip()
        return p.strip("()[]{} ,-.")

    def _extract_skills_from_section(self, section_text: str) -> tuple[list[str], list[str]]:
        """
        Extract normalized skills and uncatalogued technical terms from section text:
        - Strips lead-ins and trailing noise
        - Splits compound requirement clauses (e.g. 'core Java: OOP', 'SQL and data preprocessing')
        - Captures open-vocabulary skills across all domains (Tech, Marketing, Design, Data)
        - Eliminates generic non-skill phrases to uncatalogued terms
        """
        if not section_text or not section_text.strip():
            return [], []

        accepted_skills = set()
        uncatalogued_terms = set()

        # 1. Extract cataloged skills directly
        catalog_matches = self.skill_matcher.extract_skills(section_text)
        for s in catalog_matches:
            accepted_skills.add(s)

        # 2. Line-by-line open-vocabulary extraction and normalization
        lines = section_text.splitlines()
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue

            # Strip leading bullet tokens
            content = re.sub(r"^[-*•·\d.]+\s*", "", line_strip).strip()

            # Handle parenthetical skill mentions e.g. "AWS (SageMaker)", "computer vision (OpenCV, YOLO)"
            parens = re.findall(r"\(([^)]+)\)", content)
            for p_content in parens:
                # If parenthetical is an alternative like Facebook/Instagram, handled by Meta Ads
                if "facebook" in p_content.lower() or "instagram" in p_content.lower():
                    continue
                sub_chunks = re.split(r"[,;/]|\band\b|\bor\b", p_content)
                for sc in sub_chunks:
                    c_clean = self._clean_skill_phrase(sc)
                    canon = self.skill_matcher.canonical_map.get(c_clean.lower())
                    if canon:
                        accepted_skills.add(canon)
                    elif len(c_clean) >= 2 and c_clean.lower() not in JUNK_WORDS_STOPLIST:
                        if bool(re.search(r"^[A-Z][a-zA-Z0-9+#.-]*(?:\s+[A-Z][a-zA-Z0-9+#.-]*)*$", c_clean)):
                            accepted_skills.add(c_clean)
                            uncatalogued_terms.add(c_clean)

            # Mask parentheticals when splitting main compound clauses
            # Since parenthetical contents were already extracted above, mask them to avoid splitting inside brackets
            main_content = re.sub(r"\([^)]*\)", "", content)
            chunks = re.split(r"[:;,]|\band\b|(?<!\w)/(?!\w)", main_content)
            for raw_chunk in chunks:
                chunk = self._clean_skill_phrase(raw_chunk)
                if not chunk or len(chunk) < 2 or len(chunk) > 40:
                    continue

                chunk_lower = chunk.lower()

                # Discard degree/academic terms
                if re.search(r"\b(?:b\.?tech|b\.?e\.?|m\.?tech|b\.?sc|m\.?sc|bca|mca|mba|ph\.?d|bachelor|master|degree|diploma|related\s+field)\b", chunk_lower):
                    continue

                # Check if in discard list
                if chunk_lower in GENERIC_DISCARD_PHRASES:
                    uncatalogued_terms.add(chunk)
                    continue

                # If all words are junk stopwords
                words = chunk.split()
                if all(w.lower() in JUNK_WORDS_STOPLIST for w in words):
                    continue

                # 1. In taxonomy -> Canonical skill
                if chunk_lower in self.skill_matcher.canonical_map:
                    accepted_skills.add(self.skill_matcher.canonical_map[chunk_lower])
                    continue

                # 2. Acronym / UpperCase / CamelCase (e.g. SEO, SEM, GA4, MLflow, Airflow, CI/CD, A/B, KPI)
                is_acronym_or_tool = (
                    bool(re.search(r"\b[A-Z]{2,}\b", chunk))
                    or bool(re.search(r"[A-Z][a-z]+[A-Z]", chunk))
                    or chunk_lower in ("seo", "sem", "cro", "crm", "ga4", "eda")
                )

                # 3. Capitalized Noun Phrases (e.g. Google Ads, Meta Ads, Keyword Research, Content Writing, Copywriting, Social Media Marketing, Email Marketing, Mailchimp, React Testing Library)
                is_capitalized_skill = (
                    bool(re.search(r"^[A-Z][a-zA-Z0-9+#.-]*(?:\s+[A-Z][a-zA-Z0-9+#.-]*)*$", chunk))
                    and len(words) <= 4
                )

                # 4. Recognized domain methodology terms (statistics, hypothesis testing, experiment design, responsive design)
                is_methodology = chunk_lower in (
                    "statistics", "hypothesis testing", "experiment design",
                    "responsive design", "a/b testing", "data analysis",
                    "exploratory data analysis", "video editing", "unit testing"
                )

                if is_acronym_or_tool or is_capitalized_skill or is_methodology:
                    clean_cand = chunk.strip("()[]{} .,-")
                    if len(clean_cand) >= 2 and clean_cand.lower() not in JUNK_WORDS_STOPLIST:
                        # Normalize common aliases
                        if clean_cand.lower() == "meta ads":
                            accepted_skills.add("Meta Ads")
                        elif clean_cand.lower() == "google ads":
                            accepted_skills.add("Google Ads")
                        else:
                            accepted_skills.add(clean_cand)
                        uncatalogued_terms.add(clean_cand)

        # Discard malformed tokens with unbalanced brackets or isolated conjunctions/stop-words
        clean_skills = set()
        for s in accepted_skills:
            if s.count("(") != s.count(")"):
                continue
            if s.lower() in ("orms", "orm", "or", "and", "plus"):
                continue
            clean_skills.add(s)

        return sorted(list(clean_skills)), sorted(list(uncatalogued_terms))

    def _extract_primary_skills(
        self,
        title: str,
        required_skills: list[str],
        full_text: str,
        or_groups: list[list[str]] | None = None,
    ) -> list[str]:
        """
        Dynamically identify core role primary skills from Title, frequency, and first requirements.
        Prevents secondary parenthetical alternatives inside OR groups from diluting primary requirements.
        """
        primary = set()
        title_lower = (title or "").lower()

        # 1. Direct Title Token & Canonical Skill Alignment
        for skill in required_skills:
            s_lower = skill.lower()
            if re.search(r"\b" + re.escape(s_lower) + r"\b", title_lower):
                primary.add(skill)
            elif s_lower == "machine learning" and ("ai" in title_lower or "data science" in title_lower):
                primary.add(skill)
            elif s_lower == "ai" and "ai" in title_lower:
                primary.add(skill)

        # 2. Key Role Primary Skill Mappings derived from Role Title
        if "python" in title_lower:
            for s in required_skills:
                if s.lower() in ("python", "django", "fastapi", "flask"):
                    primary.add(s)
        elif "java" in title_lower and "javascript" not in title_lower:
            for s in required_skills:
                if s.lower() in ("java", "spring boot", "spring", "microservices"):
                    primary.add(s)
        elif "react" in title_lower or "frontend" in title_lower:
            for s in required_skills:
                if s.lower() in ("react", "javascript", "typescript", "redux", "next.js"):
                    primary.add(s)
        elif "data scientist" in title_lower or "data science" in title_lower:
            for s in required_skills:
                if s.lower() in ("python", "machine learning", "statistics", "pandas", "scikit-learn"):
                    primary.add(s)
        elif "marketing" in title_lower:
            for s in required_skills:
                if s.lower() in ("digital marketing", "seo", "google ads", "meta ads", "keyword research", "content writing"):
                    primary.add(s)
        elif "ai" in title_lower:
            for s in required_skills:
                if s.lower() in ("pytorch", "tensorflow", "deep learning", "large language models", "python", "nlp", "langchain"):
                    primary.add(s)

        # 3. Fallback: Top frequency skills across the JD text (excluding ubiquitous generic tools)
        if not primary and required_skills:
            counts = {}
            text_lower = full_text.lower()
            for s in required_skills:
                if s.lower() in ("git", "docker", "sql", "linux", "ci/cd", "agile", "rest apis"):
                    continue
                cnt = len(re.findall(r"\b" + re.escape(s.lower()) + r"\b", text_lower))
                counts[s] = cnt
            sorted_by_freq = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            if sorted_by_freq and sorted_by_freq[0][1] >= 2:
                primary.add(sorted_by_freq[0][0])
                if len(sorted_by_freq) > 1 and sorted_by_freq[1][1] >= 2:
                    primary.add(sorted_by_freq[1][0])

        # Filter secondary alternatives out of primary skills if an OR-group contains an anchor
        if or_groups:
            filtered_primary = set(primary)
            text_lower = full_text.lower()
            for grp in or_groups:
                grp_lower = {m.lower() for m in grp}
                matching_primary = [p for p in primary if p.lower() in grp_lower]
                if len(matching_primary) > 1:
                    first_found = None
                    min_pos = 999999
                    for p in matching_primary:
                        pos = text_lower.find(p.lower())
                        if 0 <= pos < min_pos:
                            min_pos = pos
                            first_found = p
                    for p in matching_primary:
                        if p != first_found:
                            filtered_primary.discard(p)
            primary = filtered_primary

        return sorted(list(primary))

    def _extract_or_groups(self, text: str) -> list[list[str]]:
        """
        Extract alternative skill requirement groups connected by 'or', '/', or comma.
        Strict sentence boundaries, parenthetical isolation, no multi-group overlap, multi-word preserved.
        """
        or_groups = []
        lines = text.splitlines()

        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue

            # 1. Preceding token + parenthetical alternatives: e.g. "FastAPI (or Flask/Django)", "PostgreSQL (or MySQL)"
            paren_matches = re.finditer(r"([A-Za-z0-9+#.-]+)\s*\((?:or\s+)?([^)]+?(?:\s+or\s+|\s*/\s*)[^)]+?)\)", line_strip, re.I)
            for pm in paren_matches:
                lead_tool = pm.group(1).strip()
                inner = pm.group(2).strip()
                if "facebook" in inner.lower() or "instagram" in inner.lower():
                    continue
                parts = [lead_tool] + re.split(r"\s+or\s+|\s*/\s*", inner, flags=re.I)
                cleaned_parts = [self.skill_matcher.canonical_map.get(self._clean_skill_phrase(p).lower(), self._clean_skill_phrase(p)) for p in parts]
                cleaned_parts = [p for p in cleaned_parts if p and len(p) >= 2 and p.lower() not in JUNK_WORDS_STOPLIST]
                if len(cleaned_parts) >= 2:
                    or_groups.append(sorted(list(set(cleaned_parts))))

            # 2. Standalone parenthetical alternatives: e.g. (MySQL / PostgreSQL)
            paren_alts = re.findall(r"\(([^)]+?(?:\s+or\s+|\s*/\s*)[^)]+?)\)", line_strip)
            for pa in paren_alts:
                if "facebook" in pa.lower() or "instagram" in pa.lower():
                    continue
                parts = re.split(r"\s+or\s+|\s*/\s*", pa, flags=re.I)
                cleaned_parts = [self.skill_matcher.canonical_map.get(self._clean_skill_phrase(p).lower(), self._clean_skill_phrase(p)) for p in parts]
                cleaned_parts = [p for p in cleaned_parts if p and len(p) >= 2 and p.lower() not in JUNK_WORDS_STOPLIST]
                if len(cleaned_parts) >= 2:
                    or_groups.append(sorted(list(set(cleaned_parts))))
                cleaned_parts = [p for p in cleaned_parts if p and len(p) >= 2 and p.lower() not in JUNK_WORDS_STOPLIST]
                if len(cleaned_parts) >= 2:
                    or_groups.append(sorted(list(set(cleaned_parts))))

            # 2. Main sentence OR patterns (outside parentheticals)
            masked = re.sub(r"\([^)]*\)", "", line_strip)
            if re.search(r"\b(?:or)\b", masked, re.I):
                # Clean leading bullets and lead-in prefixes
                clean_l = re.sub(r"^[-*•·\d.]+\s*", "", masked).strip()
                for pat in LEAD_IN_PATTERNS:
                    clean_l = re.sub(pat, "", clean_l, flags=re.I).strip()
                # Clean trailing prepositions/contexts
                clean_l = re.sub(r"\s+(?:for\s+[a-zA-Z0-9\s-]+|cloud\s+environments?|environments?|workflows?|pipelines?)[.,;:]*$", "", clean_l, flags=re.I).strip()
                
                parts = [p.strip() for p in re.split(r",|\bor\b", clean_l, flags=re.I) if p.strip()]
                cleaned_parts = []
                for p in parts:
                    c = self._clean_skill_phrase(p)
                    canon = self.skill_matcher.canonical_map.get(c.lower(), c)
                    if canon and len(canon) >= 2 and canon.lower() not in JUNK_WORDS_STOPLIST:
                        if canon not in cleaned_parts:
                            cleaned_parts.append(canon)
                if len(cleaned_parts) >= 2:
                    or_groups.append(sorted(list(set(cleaned_parts))))

        # Deduplicate and remove subsets (e.g. keep [AWS, GCP, Azure] over [GCP, Azure])
        unique_groups = []
        for g in or_groups:
            is_sub = any(set(g).issubset(set(other)) and set(g) != set(other) for other in or_groups)
            if not is_sub and g not in unique_groups:
                unique_groups.append(g)

        return unique_groups

    def _extract_qualifications(self, text: str) -> list[str]:
        """Extract degree and educational requirements."""
        qualifications: list[str] = []
        deg_pattern = r"\b(?:b\.?tech|b\.?e\.?|m\.?tech|b\.?sc|m\.?sc|bca|mca|mba|ph\.?d|bachelor|master|degree|diploma)\b"

        for line in text.splitlines():
            line_clean = line.strip()
            if not line_clean:
                continue
            if re.search(deg_pattern, line_clean, re.IGNORECASE):
                if len(line_clean) <= 150 and line_clean not in qualifications:
                    qualifications.append(line_clean)

        return qualifications[:4]

    def _extract_responsibilities(self, text: str) -> list[str]:
        """Extract key responsibility bullet points."""
        responsibilities: list[str] = []
        for line in text.splitlines():
            line_clean = line.strip()
            if not line_clean:
                continue
            if re.match(r"^[-*•·]\s*", line_clean) or re.match(r"^\d+\.\s*", line_clean):
                bullet_content = re.sub(r"^[-*•·\d.]+\s*", "", line_clean).strip()
                if len(bullet_content) >= 15:
                    responsibilities.append(bullet_content)

        return responsibilities[:6]
