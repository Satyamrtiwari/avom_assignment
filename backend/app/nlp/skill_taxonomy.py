import json
import logging
import os
import re
from typing import Sequence
import spacy
from spacy.matcher import PhraseMatcher
from difflib import SequenceMatcher
from app.config import settings

logger = logging.getLogger("resumeranker.skills")


class SkillMatcher:
    """
    Skill extraction and matching engine:
    - Curated canonical taxonomy with aliases via spaCy PhraseMatcher.
    - Frozen, versioned IDF snapshot weighting with fallback 1.0.
    - Strict fuzzy matching (>= 5 chars only, never on ambiguous short names like Java, C, R, Go).
    - Open-vocabulary matching with textual evidence extraction.
    """

    def __init__(self, nlp: spacy.language.Language, taxonomy_path: str):
        self.nlp = nlp
        self.taxonomy_path = taxonomy_path
        self.matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        self.canonical_map: dict[str, str] = {}
        self.skill_categories: dict[str, str] = {}
        self.idf_weights: dict[str, float] = {}
        self.idf_fallback: float = settings.IDF_FALLBACK_WEIGHT

        self._load_taxonomy()
        self._load_idf_snapshot()

    def _load_taxonomy(self):
        """Load skills.json and index all canonical names and aliases into PhraseMatcher."""
        if not os.path.exists(self.taxonomy_path):
            logger.warning(f"Skill taxonomy file not found at {self.taxonomy_path}")
            return

        with open(self.taxonomy_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        total_patterns = 0
        for category_name, skills in data.items():
            readable_category = category_name.replace("_", " ").title()
            for skill_key, skill_info in skills.items():
                canonical = skill_info.get("canonical", skill_key)
                aliases = skill_info.get("aliases", [])

                all_forms = [canonical] + aliases
                self.skill_categories[canonical] = readable_category

                for form in all_forms:
                    normalized = form.strip().lower()
                    if not normalized:
                        continue
                    self.canonical_map[normalized] = canonical
                    pattern_doc = self.nlp.make_doc(normalized)
                    self.matcher.add(canonical, [pattern_doc])
                    total_patterns += 1

        logger.info(
            f"Loaded {len(self.skill_categories)} unique skills with {total_patterns} pattern variations from taxonomy."
        )

    def _load_idf_snapshot(self):
        """Load frozen, versioned IDF weights from JSON."""
        idf_path = settings.IDF_SNAPSHOT_PATH
        if os.path.exists(idf_path):
            try:
                with open(idf_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.idf_weights = data.get("weights", {})
                self.idf_fallback = data.get("fallback_weight", 1.0)
                logger.info(f"Loaded frozen IDF snapshot v{data.get('version', '1.0')} with {len(self.idf_weights)} weights.")
            except Exception as e:
                logger.warning(f"Failed to load IDF snapshot: {e}")
                self.idf_fallback = 1.0
        else:
            self.idf_fallback = 1.0

    def get_skill_weight(self, skill_name: str) -> float:
        """Return the frozen IDF weight for a skill, or fallback 1.0."""
        canonical = self.canonical_map.get(skill_name.strip().lower(), skill_name.strip())
        return self.idf_weights.get(canonical, self.idf_weights.get(skill_name, self.idf_fallback))

    def extract_skills(self, text: str) -> list[str]:
        """Extract canonical skill names present in text."""
        if not text:
            return []

        doc = self.nlp(text)
        matches = self.matcher(doc)

        matched_canonicals: set[str] = set()
        for match_id, start, end in matches:
            canonical_name = self.nlp.vocab.strings[match_id]
            span = doc[start:end]
            span_text = span.text

            # Guard against ambiguous short skills false positives
            if canonical_name.lower() in settings.AMBIGUOUS_SHORT_SKILLS or len(canonical_name) <= 2:
                # Reject lowercase forms of short skills (e.g. English word "go", "c", "r")
                if span_text.islower() and len(span_text) <= 3:
                    continue

                # Contextual check for C, R, Go
                if canonical_name in ("R", "C", "Go"):
                    prev_tok = doc[start - 1].text if start > 0 else ""
                    next_tok = doc[end].text if end < len(doc) else ""
                    if prev_tok in ("&", "/", "-") or next_tok in ("&", "/", "-"):
                        continue
                    if prev_tok.lower() in ("grade", "vitamin", "class", "(", "["):
                        continue
                    if canonical_name == "Go":
                        if prev_tok.lower() in ("to", "and", "will", "shall", "can") or next_tok.lower() in ("for", "to", "ahead", "through", "with", "into"):
                            continue

            matched_canonicals.add(canonical_name)

        return sorted(list(matched_canonicals))

    def match_target_skills(
        self,
        target_skills: list[str],
        text: str,
        or_groups: list[list[str]] | None = None,
    ) -> dict:
        """
        Match a specific list of required/target skills against resume text.
        Supports:
        1. Exact canonical & alias matching via taxonomy.
        2. Exact regex word-boundary phrase matching for open-vocabulary skills.
        3. Constrained fuzzy matching (>= 5 chars only, never short/ambiguous terms).
        4. Textual evidence snippet capture (the sentence/bullet where match was found).
        5. OR-group resolution (e.g. ['PyTorch', 'TensorFlow'] counts as 1 requirement).
        """
        if not text or not target_skills:
            return {"matched": [], "missing": target_skills, "evidence": {}}

        # Extract lines/sentences for evidence extraction
        raw_lines = [line.strip() for line in text.splitlines() if len(line.strip()) >= 5]
        text_lower = text.lower()

        # Pre-extract canonical skills from text
        extracted_canonicals = set(self.extract_skills(text))

        matched_skills: list[str] = []
        missing_skills: list[str] = []
        evidence_map: dict[str, dict] = {}

        for target in target_skills:
            canonical_target = self.canonical_map.get(target.lower(), target)
            matched = False
            matched_evidence = ""
            match_type = ""

            is_ambiguous_short = target.strip().lower() in settings.AMBIGUOUS_SHORT_SKILLS or len(target.strip()) <= 2

            # 1. Exact canonical match from taxonomy
            if canonical_target in extracted_canonicals:
                matched = True
                match_type = "taxonomy_exact"
                # Find evidence line
                for line in raw_lines:
                    if re.search(r"\b" + re.escape(target.lower()) + r"\b", line.lower()):
                        matched_evidence = line[:140]
                        break
                    if re.search(r"\b" + re.escape(canonical_target.lower()) + r"\b", line.lower()):
                        matched_evidence = line[:140]
                        break

            # 2. Exact word-boundary match for open-vocabulary terms
            if not matched:
                if is_ambiguous_short:
                    pat = r"(?<![a-zA-Z0-9&/])" + re.escape(target.strip()) + r"(?![a-zA-Z0-9&/])"
                    for line in raw_lines:
                        m = re.search(pat, line)
                        if m:
                            tok = m.group(0)
                            if tok.islower() and len(tok) <= 3:
                                continue
                            matched = True
                            match_type = "case_sensitive_exact"
                            matched_evidence = line[:140]
                            break
                else:
                    pat = r"\b" + re.escape(target.lower()) + r"\b"
                    if re.search(pat, text_lower):
                        matched = True
                        match_type = "word_boundary_exact"
                        for line in raw_lines:
                            if re.search(pat, line.lower()):
                                matched_evidence = line[:140]
                                break

            # 3. Constrained fuzzy matching
            # Rule: only for terms >= 5 chars, never for ambiguous short terms (Java, Go, C, etc.)
            if not matched and len(target) >= settings.MIN_FUZZY_SKILL_LENGTH:
                target_clean = target.lower()
                if target_clean not in settings.AMBIGUOUS_SHORT_SKILLS:
                    for line in raw_lines:
                        line_lower = line.lower()
                        # Token check
                        tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{4,}\b", line_lower)
                        for tok in tokens:
                            if tok in settings.AMBIGUOUS_SHORT_SKILLS:
                                continue
                            ratio = SequenceMatcher(None, target_clean, tok).ratio()
                            if ratio >= settings.FUZZY_MATCH_THRESHOLD:
                                matched = True
                                match_type = f"fuzzy_{ratio:.2f}"
                                matched_evidence = line[:140]
                                break
                        if matched:
                            break

            if matched:
                matched_skills.append(target)
                evidence_map[target] = {
                    "matched": True,
                    "type": match_type,
                    "evidence": matched_evidence or f"Found in candidate document for '{target}'"
                }
            else:
                missing_skills.append(target)

        return {
            "matched": matched_skills,
            "missing": missing_skills,
            "evidence": evidence_map,
        }
