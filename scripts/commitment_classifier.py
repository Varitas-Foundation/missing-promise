"""
Commitment Classifier for Privacy Policy Statements

Classifies privacy policy statements into three categories based on speech act theory:
1. PRACTICE - Descriptive statements about what the company does
2. COMPANY_COMMITMENT - Self-binding promises/limitations by the company
3. USER_CONTROL - Descriptions of user capabilities/rights

This classifier implements the refined taxonomy from Task 1 audit, which found that
only 12% of statements labeled "COMMITMENT" in Paper 1 represent true company
self-binding commitments.

Usage:
    from commitment_classifier import CommitmentClassifier

    classifier = CommitmentClassifier()
    result = classifier.classify("We do not sell your personal information.")
    # Returns: {'class': 'COMPANY_COMMITMENT', 'confidence': 0.95, 'markers': [...]}
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class StatementClass(Enum):
    PRACTICE = "PRACTICE"
    COMPANY_COMMITMENT = "COMPANY_COMMITMENT"
    USER_CONTROL = "USER_CONTROL"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class ClassificationResult:
    statement_class: StatementClass
    confidence: float
    markers: list[str]
    rule_triggered: str
    features: dict


# ---------------------------------------------------------------------------
# Linguistic Patterns (grounded in speech act theory)
# ---------------------------------------------------------------------------

# COMPANY_COMMITMENT patterns - self-binding promises
COMPANY_COMMITMENT_PATTERNS = {
    # Strong negation patterns (highest confidence)
    "company_negation_strong": [
        r"\b(we|the company|our company)\s+(do not|does not|don'?t|will not|won'?t|shall not|cannot|never)\s+\w+",
        r"\b(we|the company)\s+\w+\s+(do not|does not|don'?t|will not|won'?t|never)\b",
    ],
    # Explicit commitment language
    "explicit_commitment": [
        r"\bwe\s+(promise|guarantee|ensure|commit|pledge|warrant)\b",
        r"\b(our|the)\s+commitment\s+to\b",
        r"\bwe\s+are\s+committed\s+to\b",
    ],
    # Protective action patterns
    "company_protection": [
        r"\bwe\s+(protect|safeguard|secure|limit|restrict|prevent)\s+",
        r"\b(the company|we)\s+\w*\s*(protect|safeguard|secure)s?\s+your\b",
    ],
    # Prohibition patterns
    "prohibition": [
        r"\b(prohibited|forbidden|not\s+permitted|not\s+allowed)\b.*\b(to|from)\b",
        r"\bwe\s+prohibit\b",
    ],
    # "Only" restrictions (limiting scope)
    "scope_limitation": [
        r"\bwe\s+only\s+(use|collect|share|disclose|process)\b",
        r"\b(limited|restricted)\s+to\b",
    ],
}

# USER_CONTROL patterns - user capabilities/rights
USER_CONTROL_PATTERNS = {
    # User capability patterns (highest confidence)
    "user_capability": [
        r"\b(users?|customers?|you|individuals?|consumers?|members?)\s+(can|may|are able to|have the (right|ability|option) to)\b",
        r"\b(you|users?)\s+have\s+(the\s+)?(right|ability|option|choice)\s+to\b",
        r"\b(users?|customers?|you)\s+(are\s+)?(able|entitled|permitted)\s+to\b",
    ],
    # User action patterns (expanded)
    "user_action": [
        r"\b(users?|you|customers?)\s+(can|may)\s+(opt[- ]?out|unsubscribe|delete|remove|access|correct|update|modify|request|withdraw|revoke|disable|enable|change|review|download|export)\b",
        r"\b(opt[- ]?out|unsubscribe|delete|access|correct|update|download|export)\s+(your|their|the)\b",
        r"\b(you|users?)\s+(can|may)\s+\w+\s+(your|their)\s+(account|data|information|preferences?|settings?)\b",
        r"\bto\s+(opt[- ]?out|unsubscribe|delete|access|correct|modify)\b",
    ],
    # Rights language (expanded)
    "user_rights": [
        r"\b(you|users?)\s+(are\s+)?(entitled|able)\s+to\b",
        r"\b(your|the|their)\s+(right|rights)\s+to\s+(access|delete|correct|port|object|restrict|know|request|opt[- ]?out)\b",
        r"\b(GDPR|CCPA|privacy|consumer|data\s+subject)\s+rights?\b",
        r"\bright\s+to\s+(be\s+forgotten|erasure|deletion|access|portability|rectification)\b",
    ],
    # Choice/control language with user subject (expanded)
    "user_choice": [
        r"\b(you|users?|customers?)\s+(can\s+)?(choose|control|decide|manage|determine)\b",
        r"\b(your|user)\s+(choice|control|preference)s?\b",
        r"\b(at\s+any\s+time|anytime)\b.*\b(you|users?)\s+(can|may)\b",
        r"\b(you|users?)\s+(can|may)\s+\w+\s+(at\s+any\s+time|anytime)\b",
    ],
    # Account/settings control
    "account_control": [
        r"\b(account\s+settings?|privacy\s+settings?|preference\s+settings?)\b",
        r"\b(manage|update|change|modify)\s+(your|their)\s+(account|profile|settings?|preferences?)\b",
        r"\b(you|users?)\s+(can|may)\s+(log\s+in|sign\s+in|register|create\s+an?\s+account)\b",
    ],
}

# PRACTICE patterns - descriptive statements
PRACTICE_PATTERNS = {
    # Collection patterns (expanded)
    "collection": [
        r"\b(we|the company|company)\s+(collect|collects|gather|gathers|obtain|obtains|receive|receives|acquire|acquires)\s+",
        r"\binformation\s+(is\s+|we\s+)?(collected|gathered|obtained)\b",
        r"\b(collect|collecting)\s+(your|user|personal|data|information)\b",
        r"\bdata\s+(we\s+)?collect\b",
    ],
    # Use patterns (expanded)
    "use": [
        r"\b(we|the company|company)\s+(use|uses|utilize|utilizes|employ|employs|process|processes|analyze|analyzes)\s+",
        r"\b(data|information)\s+(is\s+|we\s+)?(used|utilized|processed|analyzed)\b",
        r"\b(use|using)\s+(your|user|personal|this|the)\s+(data|information)\b",
        r"\bfor\s+(the\s+)?(purpose|purposes)\s+of\b",
    ],
    # Sharing patterns (expanded)
    "sharing": [
        r"\b(we|the company|company)\s+(share|shares|disclose|discloses|provide|provides|transfer|transfers|transmit|transmits)\s+",
        r"\b(data|information)\s+(is\s+|may\s+be\s+|we\s+)?(shared|disclosed|provided|transferred)\b",
        r"\bshared?\s+with\s+(third parties|partners|affiliates|vendors|advertisers|service providers)\b",
        r"\b(share|sharing)\s+(your|user|personal)\b",
    ],
    # Storage/retention (expanded)
    "storage": [
        r"\b(we|the company)\s+(store|stores|retain|retains|keep|keeps|maintain|maintains)\s+",
        r"\b(data|information)\s+(is\s+)?(stored|retained|kept|maintained)\b",
        r"\bretention\s+(period|policy|practices?)\b",
        r"\b(stored|kept)\s+(for|on|in)\b",
    ],
    # Epistemic hedging (indicates practice, not commitment)
    "epistemic_hedge": [
        r"\b(we|the company)\s+may\s+(collect|use|share|disclose|transfer|process|provide|store)\b",
        r"\b(we|the company)\s+might\s+(collect|use|share|disclose)\b",
        r"\b(may|might|could)\s+be\s+(collected|used|shared|disclosed|transferred)\b",
        r"\b(we|the company)\s+can\s+(collect|use|share|access)\b",
    ],
    # General descriptive patterns
    "descriptive": [
        r"\b(types?\s+of\s+)?(data|information)\s+(we\s+)?(collect|use|process|share)\b",
        r"\b(we|the company)\s+(also\s+)?(collect|use|share|process|receive)\b",
        r"\b(personal|user)\s+(data|information)\s+(is|includes?|such as)\b",
        r"\b(includes?|such as|like|e\.?g\.?)\s+.*(data|information|address|name|email)\b",
    ],
}

# Negation scope - patterns that negate practices (-> commitment)
NEGATION_CUES = [
    r"\bdo not\b", r"\bdoes not\b", r"\bdon'?t\b", r"\bdoesn'?t\b",
    r"\bwill not\b", r"\bwon'?t\b", r"\bshall not\b", r"\bshan'?t\b",
    r"\bnever\b", r"\bcannot\b", r"\bcan'?t\b",
    r"\bprohibit\b", r"\bforbid\b", r"\bprevent\b",
]

# Subject detection
COMPANY_SUBJECTS = [
    r"\bwe\b", r"\bour\b", r"\bthe company\b", r"\bcompany\b",
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",  # Company names (capitalized)
]

USER_SUBJECTS = [
    r"\byou\b", r"\byour\b", r"\busers?\b", r"\bcustomers?\b",
    r"\bindividuals?\b", r"\bconsumers?\b", r"\bvisitors?\b",
]


class CommitmentClassifier:
    """
    Rule-based classifier for privacy policy statements.

    Uses linguistic patterns derived from speech act theory to distinguish:
    - PRACTICE: Assertive speech acts (describing what company does)
    - COMPANY_COMMITMENT: Commissive speech acts (binding the company)
    - USER_CONTROL: Descriptions of user capabilities
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        # Compile patterns for efficiency
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self.compiled = {
            "commitment": {k: [re.compile(p, re.IGNORECASE) for p in v]
                          for k, v in COMPANY_COMMITMENT_PATTERNS.items()},
            "user_control": {k: [re.compile(p, re.IGNORECASE) for p in v]
                            for k, v in USER_CONTROL_PATTERNS.items()},
            "practice": {k: [re.compile(p, re.IGNORECASE) for p in v]
                        for k, v in PRACTICE_PATTERNS.items()},
            "negation": [re.compile(p, re.IGNORECASE) for p in NEGATION_CUES],
            "company_subject": [re.compile(p, re.IGNORECASE) for p in COMPANY_SUBJECTS],
            "user_subject": [re.compile(p, re.IGNORECASE) for p in USER_SUBJECTS],
        }

    def _count_matches(self, text: str, patterns: list) -> tuple[int, list[str]]:
        """Count pattern matches and return matched strings."""
        count = 0
        matches = []
        for pattern in patterns:
            found = pattern.findall(text)
            if found:
                count += len(found)
                matches.extend([str(m) if isinstance(m, str) else str(m[0]) for m in found])
        return count, matches

    def _has_negation(self, text: str) -> bool:
        """Check if text contains negation cues."""
        for pattern in self.compiled["negation"]:
            if pattern.search(text):
                return True
        return False

    def _detect_subject(self, text: str) -> str:
        """Detect primary subject (company, user, or unclear)."""
        company_count = sum(1 for p in self.compiled["company_subject"] if p.search(text))
        user_count = sum(1 for p in self.compiled["user_subject"] if p.search(text))

        # Check position - who comes first?
        company_pos = float('inf')
        user_pos = float('inf')

        for p in self.compiled["company_subject"]:
            match = p.search(text)
            if match:
                company_pos = min(company_pos, match.start())

        for p in self.compiled["user_subject"]:
            match = p.search(text)
            if match:
                user_pos = min(user_pos, match.start())

        if company_pos < user_pos:
            return "company"
        elif user_pos < company_pos:
            return "user"
        elif company_count > user_count:
            return "company"
        elif user_count > company_count:
            return "user"
        return "unclear"

    def extract_features(self, text: str) -> dict:
        """Extract all linguistic features from text."""
        features = {
            "has_negation": self._has_negation(text),
            "primary_subject": self._detect_subject(text),
            "commitment_markers": {},
            "user_control_markers": {},
            "practice_markers": {},
        }

        # Count commitment markers
        for category, patterns in self.compiled["commitment"].items():
            count, matches = self._count_matches(text, patterns)
            if count > 0:
                features["commitment_markers"][category] = {
                    "count": count,
                    "matches": matches
                }

        # Count user control markers
        for category, patterns in self.compiled["user_control"].items():
            count, matches = self._count_matches(text, patterns)
            if count > 0:
                features["user_control_markers"][category] = {
                    "count": count,
                    "matches": matches
                }

        # Count practice markers
        for category, patterns in self.compiled["practice"].items():
            count, matches = self._count_matches(text, patterns)
            if count > 0:
                features["practice_markers"][category] = {
                    "count": count,
                    "matches": matches
                }

        # Aggregate scores
        features["commitment_score"] = sum(
            v["count"] for v in features["commitment_markers"].values()
        )
        features["user_control_score"] = sum(
            v["count"] for v in features["user_control_markers"].values()
        )
        features["practice_score"] = sum(
            v["count"] for v in features["practice_markers"].values()
        )

        return features

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify a statement into PRACTICE, COMPANY_COMMITMENT, or USER_CONTROL.

        Classification logic:
        1. If user subject + capability verbs -> USER_CONTROL
        2. If company subject + negation + practice verb -> COMPANY_COMMITMENT
        3. If explicit commitment language -> COMPANY_COMMITMENT
        4. If company subject + practice verb (no negation) -> PRACTICE
        5. If epistemic hedging -> PRACTICE
        6. If ambiguous -> AMBIGUOUS
        """
        features = self.extract_features(text)
        markers = []
        rule_triggered = "default"

        # Rule 1: User control (user subject + capability)
        if features["user_control_score"] > 0 and features["primary_subject"] == "user":
            confidence = min(0.95, 0.7 + 0.1 * features["user_control_score"])
            for cat, data in features["user_control_markers"].items():
                markers.extend(data["matches"])
            return ClassificationResult(
                statement_class=StatementClass.USER_CONTROL,
                confidence=confidence,
                markers=markers,
                rule_triggered="user_capability",
                features=features
            )

        # Rule 2: Company commitment (negation pattern)
        if features["has_negation"] and features["primary_subject"] == "company":
            # Check if negation applies to a practice (-> commitment)
            if "company_negation_strong" in features["commitment_markers"]:
                confidence = 0.95
                for cat, data in features["commitment_markers"].items():
                    markers.extend(data["matches"])
                return ClassificationResult(
                    statement_class=StatementClass.COMPANY_COMMITMENT,
                    confidence=confidence,
                    markers=markers,
                    rule_triggered="company_negation",
                    features=features
                )

        # Rule 3: Explicit commitment language
        if features["commitment_score"] > 0:
            if "explicit_commitment" in features["commitment_markers"]:
                confidence = 0.90
                for cat, data in features["commitment_markers"].items():
                    markers.extend(data["matches"])
                return ClassificationResult(
                    statement_class=StatementClass.COMPANY_COMMITMENT,
                    confidence=confidence,
                    markers=markers,
                    rule_triggered="explicit_commitment",
                    features=features
                )

            # Protection language
            if "company_protection" in features["commitment_markers"]:
                confidence = 0.80
                for cat, data in features["commitment_markers"].items():
                    markers.extend(data["matches"])
                return ClassificationResult(
                    statement_class=StatementClass.COMPANY_COMMITMENT,
                    confidence=confidence,
                    markers=markers,
                    rule_triggered="company_protection",
                    features=features
                )

        # Rule 4: User control (even without clear user subject)
        if features["user_control_score"] >= 2:
            confidence = min(0.85, 0.6 + 0.1 * features["user_control_score"])
            for cat, data in features["user_control_markers"].items():
                markers.extend(data["matches"])
            return ClassificationResult(
                statement_class=StatementClass.USER_CONTROL,
                confidence=confidence,
                markers=markers,
                rule_triggered="user_control_strong",
                features=features
            )

        # Rule 5: Practice patterns (descriptive)
        if features["practice_score"] > 0:
            # Epistemic hedging is strong practice signal
            if "epistemic_hedge" in features["practice_markers"]:
                confidence = 0.90
            else:
                confidence = min(0.85, 0.6 + 0.1 * features["practice_score"])

            for cat, data in features["practice_markers"].items():
                markers.extend(data["matches"])
            return ClassificationResult(
                statement_class=StatementClass.PRACTICE,
                confidence=confidence,
                markers=markers,
                rule_triggered="practice_pattern",
                features=features
            )

        # Rule 6: Fallback based on scores
        scores = {
            StatementClass.COMPANY_COMMITMENT: features["commitment_score"],
            StatementClass.USER_CONTROL: features["user_control_score"],
            StatementClass.PRACTICE: features["practice_score"],
        }

        if max(scores.values()) > 0:
            best_class = max(scores, key=scores.get)
            return ClassificationResult(
                statement_class=best_class,
                confidence=0.5,
                markers=markers,
                rule_triggered="score_fallback",
                features=features
            )

        # Ambiguous - no clear signals
        return ClassificationResult(
            statement_class=StatementClass.AMBIGUOUS,
            confidence=0.3,
            markers=[],
            rule_triggered="no_match",
            features=features
        )

    def classify_batch(self, statements: list[str]) -> list[ClassificationResult]:
        """Classify a batch of statements."""
        return [self.classify(text) for text in statements]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def classify_statements_file(input_path: str, output_path: str):
    """
    Classify statements from a JSON file and write results.

    Expected input format:
    {
        "statements": [
            {"statement_id": "...", "text": "...", ...},
            ...
        ]
    }
    """
    import json
    from pathlib import Path
    from datetime import datetime, timezone

    with open(input_path) as f:
        data = json.load(f)

    classifier = CommitmentClassifier()

    results = []
    class_counts = {c.value: 0 for c in StatementClass}

    for stmt in data["statements"]:
        result = classifier.classify(stmt["text"])
        class_counts[result.statement_class.value] += 1

        results.append({
            "statement_id": stmt["statement_id"],
            "text": stmt["text"],
            "original_type": stmt.get("type"),
            "classified_type": result.statement_class.value,
            "confidence": result.confidence,
            "rule_triggered": result.rule_triggered,
            "markers": result.markers,
        })

    output = {
        "metadata": {
            "classifier_version": "1.0",
            "classification_date": datetime.now(timezone.utc).isoformat(),
            "input_file": str(input_path),
            "total_statements": len(results),
        },
        "summary": {
            "class_distribution": class_counts,
            "high_confidence": len([r for r in results if r["confidence"] >= 0.8]),
            "low_confidence": len([r for r in results if r["confidence"] < 0.5]),
        },
        "results": results,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Classified {len(results)} statements")
    print(f"Distribution: {class_counts}")
    print(f"Output: {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # File mode
        input_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else "classified_statements.json"
        classify_statements_file(input_path, output_path)
    else:
        # Demo mode
        classifier = CommitmentClassifier()

        test_cases = [
            # COMPANY_COMMITMENT examples
            "We do not sell your personal information.",
            "The company will never share your genetic data with insurers.",
            "We guarantee the security of your data.",
            "We protect your personal information using encryption.",

            # USER_CONTROL examples
            "Users can opt out of promotional emails at any time.",
            "You have the right to delete your account.",
            "Customers may request access to their personal data.",
            "You can choose whether to participate in research.",

            # PRACTICE examples
            "We collect your email address when you register.",
            "We may share data with advertising partners.",
            "The company uses cookies to improve your experience.",
            "Information is stored on secure servers.",

            # Ambiguous examples
            "Research activities are overseen by an ethics board.",
            "Participation is voluntary.",
        ]

        print("=" * 70)
        print("COMMITMENT CLASSIFIER DEMO")
        print("=" * 70)

        for text in test_cases:
            result = classifier.classify(text)
            print(f"\nText: {text}")
            print(f"  Class: {result.statement_class.value}")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"  Rule: {result.rule_triggered}")
            if result.markers:
                print(f"  Markers: {result.markers[:3]}")
