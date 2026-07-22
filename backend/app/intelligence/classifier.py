"""
AURA Backend — Knowledge Classifier.

Module: app.intelligence.classifier
Purpose: Classifies any input into the correct knowledge type.
         Uses LLM for classification with rule-based fallback.

Knowledge Types:
    Knowledge   — Facts, definitions, concepts ("What is X?")
    Skill       — How-to, procedures, techniques ("How to do X?")
    Rule        — Constraints, policies, standards
    Workflow    — Step-by-step processes with conditions
    Pattern     — Recurring structures, templates, designs
    Template    — Reusable formats for documents/code
    Experience  — Decisions made, outcomes, lessons learned
    Reference   — Links, papers, external resources

The classifier also detects:
    - Category (Programming, Business, Science, etc.)
    - Subcategory (Python, Marketing, Biology, etc.)
    - Tags (comma-separated keywords)
    - Importance (0.0-1.0)
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# ── Knowledge type definitions ─────────────────────────────────────────────────
KNOWLEDGE_TYPES = {
    "Knowledge", "Skill", "Rule", "Workflow",
    "Pattern", "Template", "Experience", "Reference",
}

# ── Rule-based type detection patterns ────────────────────────────────────────
TYPE_PATTERNS = {
    "Skill": [
        r'\bhow to\b', r'\bstep by step\b', r'\btutorial\b', r'\blearn\b',
        r'\bguide\b', r'\bimplement\b', r'\bbuild\b', r'\bcreate\b',
        r'\bsetup\b', r'\bconfigure\b', r'\binstall\b', r'\bdeploy\b',
    ],
    "Rule": [
        r'\bmust\b', r'\bshould\b', r'\bpolicy\b', r'\bstandard\b',
        r'\bregulation\b', r'\brequirement\b', r'\bcompliance\b',
        r'\bnever\b', r'\balways\b', r'\bforbidden\b', r'\bmandate\b',
    ],
    "Workflow": [
        r'\bprocess\b', r'\bworkflow\b', r'\bprocedure\b', r'\bsop\b',
        r'\bstep \d\b', r'\bfirst.*then\b', r'\bsequence\b', r'\bpipeline\b',
        r'\bwhen.*then\b', r'\bif.*then\b', r'\bflow\b',
    ],
    "Pattern": [
        r'\bpattern\b', r'\barchitecture\b', r'\bdesign\b', r'\bstructure\b',
        r'\bconvention\b', r'\bstandard way\b', r'\bbest practice\b',
        r'\bapproach\b', r'\bparadigm\b',
    ],
    "Template": [
        r'\btemplate\b', r'\bformat\b', r'\bboilerplate\b', r'\bscaffold\b',
        r'\bexample code\b', r'\bsample\b', r'\bstarting point\b',
    ],
    "Experience": [
        r'\blearned\b', r'\bdecided\b', r'\bmistake\b', r'\blesson\b',
        r'\bexperience\b', r'\bretrospec\b', r'\bcase study\b',
        r'\bworked\b', r'\bfailed\b', r'\bsuccessful\b',
    ],
    "Reference": [
        r'\bhttp\b', r'\bhttps\b', r'\bdocumentation\b', r'\bpaper\b',
        r'\bresearch\b', r'\bsource\b', r'\blink\b', r'\breference\b',
        r'\bgithub\.com\b', r'\bdocs\.\b',
    ],
}

# ── Category detection ─────────────────────────────────────────────────────────
CATEGORY_PATTERNS = {
    "Programming": [
        r'\bpython\b', r'\bjavascript\b', r'\breact\b', r'\bapi\b',
        r'\bdatabase\b', r'\bsql\b', r'\bgit\b', r'\bcode\b', r'\bfunction\b',
        r'\bclass\b', r'\balgorithm\b', r'\bfastapi\b', r'\bnode\b',
    ],
    "Business": [
        r'\bbusiness\b', r'\bcompany\b', r'\bclient\b', r'\bsales\b',
        r'\bmarketing\b', r'\bfinance\b', r'\baccounting\b', r'\bhr\b',
        r'\brecruitment\b', r'\bemployee\b', r'\bstrategy\b',
    ],
    "Science": [
        r'\bscience\b', r'\bresearch\b', r'\bexperiment\b', r'\bdata\b',
        r'\bstatistics\b', r'\bml\b', r'\bai\b', r'\bmachine learning\b',
        r'\bneural\b', r'\banalysis\b',
    ],
    "Health": [
        r'\bhealth\b', r'\bmedical\b', r'\bdoctor\b', r'\bmedicine\b',
        r'\btreatment\b', r'\bdisease\b', r'\bsymptom\b',
    ],
    "Legal": [
        r'\blaw\b', r'\blegal\b', r'\bcontract\b', r'\bregulation\b',
        r'\bcompliance\b', r'\bvisa\b', r'\brights\b',
    ],
    "Technology": [
        r'\btech\b', r'\bsoftware\b', r'\bhardware\b', r'\bnetwork\b',
        r'\bcloud\b', r'\bserver\b', r'\bsecurity\b', r'\bcyber\b',
    ],
    "Education": [
        r'\blearn\b', r'\bteach\b', r'\bcourse\b', r'\btutor\b',
        r'\bstudent\b', r'\buniversity\b', r'\bschool\b',
    ],
    "General": [],
}


class KnowledgeClassifier:
    """
    Classifies knowledge into structured types.

    Two-stage classification:
    1. Rule-based (fast, no LLM needed)
    2. LLM-based (for ambiguous cases)

    Methods:
        classify: Full classification of content.
        detect_type: Detect knowledge type only.
        detect_category: Detect category only.
        extract_tags: Extract relevant tags.
    """

    def detect_type(self, text: str) -> str:
        """
        Detect knowledge type using rule-based patterns.

        Args:
            text: Content to classify.

        Returns:
            str: Knowledge type (Knowledge/Skill/Rule/etc.)
        """
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for type_name, patterns in TYPE_PATTERNS.items():
            score = sum(
                1 for p in patterns
                if re.search(p, text_lower, re.IGNORECASE)
            )
            if score > 0:
                scores[type_name] = score

        if scores:
            return max(scores, key=scores.get)
        return "Knowledge"  # Default

    def detect_category(self, text: str) -> tuple[str, str | None]:
        """
        Detect category and subcategory.

        Args:
            text: Content to categorize.

        Returns:
            tuple: (category, subcategory)
        """
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for cat, patterns in CATEGORY_PATTERNS.items():
            if not patterns:
                continue
            score = sum(
                1 for p in patterns
                if re.search(p, text_lower, re.IGNORECASE)
            )
            if score > 0:
                scores[cat] = score

        category = max(scores, key=scores.get) if scores else "General"

        # Detect subcategory
        subcategory = self._detect_subcategory(text_lower, category)

        return category, subcategory

    def _detect_subcategory(self, text: str, category: str) -> str | None:
        """Detect subcategory within a category."""
        subcats = {
            "Programming": {
                "Python": [r'\bpython\b', r'\bdjango\b', r'\bfastapi\b', r'\bflask\b'],
                "JavaScript": [r'\bjavascript\b', r'\bnode\b', r'\breact\b', r'\bvue\b'],
                "Database": [r'\bsql\b', r'\bdatabase\b', r'\bmongodb\b', r'\bpostgres\b'],
                "AI/ML": [r'\bmachine learning\b', r'\bneural\b', r'\bollama\b', r'\bllm\b'],
            },
            "Business": {
                "HR": [r'\bhr\b', r'\brecruitment\b', r'\bemployee\b', r'\bhiring\b'],
                "Finance": [r'\bfinance\b', r'\baccounting\b', r'\bbudget\b', r'\binvoice\b'],
                "Marketing": [r'\bmarketing\b', r'\bseo\b', r'\bcampaign\b', r'\bbrand\b'],
            },
        }

        if category not in subcats:
            return None

        for subcat, patterns in subcats[category].items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                return subcat

        return None

    def extract_tags(self, text: str, title: str = "") -> list[str]:
        """
        Extract relevant tags from content.

        Args:
            text: Content text.
            title: Optional title for additional signals.

        Returns:
            list[str]: List of relevant tags.
        """
        combined = (title + " " + text).lower()
        tags = set()

        # Tech tags
        tech_terms = [
            "python", "javascript", "react", "fastapi", "ollama", "chromadb",
            "sqlite", "docker", "git", "api", "llm", "ai", "ml", "sql",
            "node", "electron", "vite", "tailwind",
        ]
        for term in tech_terms:
            if term in combined:
                tags.add(term)

        # Business tags
        biz_terms = [
            "business", "finance", "hr", "marketing", "sales", "client",
            "accounting", "legal", "compliance",
        ]
        for term in biz_terms:
            if term in combined:
                tags.add(term)

        # Extract capitalized words as potential tags (concepts)
        capitalized = re.findall(r'\b[A-Z][a-z]{2,}\b', title + " " + text[:500])
        for word in capitalized[:5]:
            if len(word) > 3:
                tags.add(word.lower())

        return list(tags)[:10]

    def calculate_importance(
        self,
        knowledge_type: str,
        category: str,
        text: str,
    ) -> float:
        """
        Calculate importance score for a knowledge item.

        Args:
            knowledge_type: Classified type.
            category: Detected category.
            text: Content.

        Returns:
            float: Importance score 0.0-1.0.
        """
        base_scores = {
            "Rule": 0.85,
            "Workflow": 0.80,
            "Skill": 0.75,
            "Experience": 0.75,
            "Pattern": 0.70,
            "Knowledge": 0.65,
            "Template": 0.60,
            "Reference": 0.55,
        }
        score = base_scores.get(knowledge_type, 0.60)

        # Boost for explicitly confirmed items
        if any(w in text.lower() for w in ["important", "critical", "always", "never", "must"]):
            score = min(score + 0.1, 1.0)

        return round(score, 2)

    async def classify(
        self,
        title: str,
        content: str,
        source: str = "manual",
        use_llm: bool = True,
    ) -> dict:
        """
        Full classification pipeline.

        Stage 1: Rule-based classification (always runs)
        Stage 2: LLM enhancement (if use_llm=True and content > 200 chars)

        Args:
            title: Content title.
            content: Full content text.
            source: Where content came from.
            use_llm: Whether to use LLM for deeper classification.

        Returns:
            dict: Complete classification result with all metadata.
        """
        # Stage 1: Rule-based
        knowledge_type = self.detect_type(content + " " + title)
        category, subcategory = self.detect_category(content + " " + title)
        tags = self.extract_tags(content, title)
        importance = self.calculate_importance(knowledge_type, category, content)

        result = {
            "knowledge_type": knowledge_type,
            "category": category,
            "subcategory": subcategory,
            "tags": ",".join(tags),
            "importance": importance,
            "confidence": 0.70,
            "summary": content[:300] + "..." if len(content) > 300 else content,
            "rules_extracted": [],
            "concepts_extracted": [],
            "common_mistakes": [],
            "best_practices": [],
        }

        # Stage 2: LLM enhancement (only for substantial content)
        if use_llm and len(content) > 150:
            try:
                llm_result = await self._llm_classify(title, content[:2000])
                if llm_result:
                    result.update(llm_result)
            except Exception as e:
                logger.warning("LLM classification failed, using rule-based: %s", e)

        return result

    async def _llm_classify(self, title: str, content: str) -> dict | None:
        """Use LLM for deeper classification and extraction."""
        try:
            from app.services.ollama_service import ollama_service

            prompt = f"""Analyze this content and respond with ONLY valid JSON (no markdown, no explanation):

Title: {title}
Content: {content[:1500]}

Return this exact JSON structure:
{{
  "knowledge_type": "Knowledge|Skill|Rule|Workflow|Pattern|Template|Experience|Reference",
  "category": "Programming|Business|Science|Health|Legal|Technology|Education|General",
  "subcategory": "specific subcategory or null",
  "summary": "1-2 sentence summary",
  "tags": "tag1,tag2,tag3",
  "concepts_extracted": ["concept1", "concept2"],
  "rules_extracted": ["rule1", "rule2"],
  "best_practices": ["practice1", "practice2"],
  "common_mistakes": ["mistake1", "mistake2"],
  "confidence": 0.8
}}"""

            response = await ollama_service.chat(
                message=prompt,
                history=[],
                system_prompt=(
                    "You are a knowledge classifier. "
                    "Always respond with valid JSON only. "
                    "No markdown code blocks. No explanation. Just JSON."
                ),
            )

            # Clean response
            clean = response.strip()
            clean = re.sub(r'^```json\s*', '', clean)
            clean = re.sub(r'^```\s*', '', clean)
            clean = re.sub(r'\s*```$', '', clean)
            clean = clean.strip()

            # Find JSON object
            start = clean.find('{')
            end = clean.rfind('}')
            if start >= 0 and end > start:
                clean = clean[start:end+1]

            parsed = json.loads(clean)

            # Validate required fields
            if "knowledge_type" in parsed and parsed["knowledge_type"] in KNOWLEDGE_TYPES:
                return parsed

        except json.JSONDecodeError as e:
            logger.warning("LLM returned invalid JSON: %s", e)
        except Exception as e:
            logger.warning("LLM classify failed: %s", e)

        return None


# ── Singleton ─────────────────────────────────────────────────────────────────
knowledge_classifier = KnowledgeClassifier()