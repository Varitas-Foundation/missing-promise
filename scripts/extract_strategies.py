#!/usr/bin/env python3
"""
Linguistic Strategy Taxonomy Extraction

Analyzes the highest-ratio companies in OPPT to identify dominant commitment
avoidance strategies through linguistic feature analysis. Classifies companies
into a taxonomy of avoidance strategies and computes prevalence across the
full corpus.

Usage:
    python extract_strategies.py
"""

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, stdev

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"

OPPT_CLASSIFICATIONS = DATA_DIR / "oppt_commitment_classifications.json"
OPP115_CLASSIFICATIONS = DATA_DIR / "opp115_commitment_classifications.json"

OUTPUT_PATH = DATA_DIR / "strategy_taxonomy.json"

# ── Linguistic Feature Definitions ─────────────────────────────────────────────

# Modal verbs
PERMISSIVE_MODALS = ["may", "might", "could", "can"]
BINDING_MODALS = ["will", "shall", "must"]
NEGATION_PATTERNS = ["do not", "does not", "will not", "never", "cannot"]

# Hedging language
CONDITIONAL_HEDGES = [
    "depending on", "if ", "when ", "as applicable", "as necessary",
    "as needed", "where "
]
GENERALIZING_HEDGES = [
    "generally", "typically", "usually", "in most cases", "primarily"
]
APPROXIMATING_HEDGES = [
    "some ", "certain ", "various", "multiple", "particular"
]

# Scope qualifiers
NARROW_SCOPE = [
    "only when", "limited to", "except", "unless", "solely", "specifically"
]
EXCEPTION_CLAUSES = [
    "except as", "other than", "excluding", "apart from"
]

# Action verbs
EXPANSIVE_VERBS = [
    "collect", "use", "share", "disclose", "process", "transfer", "sell",
    "provide"
]
PROTECTIVE_VERBS = [
    "protect", "secure", "limit", "restrict", "prevent", "safeguard",
    "encrypt"
]

# Strategy definitions for output
STRATEGY_DEFINITIONS = {
    "Modal Hedging": (
        "High use of 'may/might/could', few binding commitments. "
        "Company describes what it *may* do rather than what it *does* or *won't* do."
    ),
    "Minimal Commitment Density": (
        "Very few total commitment statements (< 5) despite lengthy policy. "
        "Company simply omits commitments."
    ),
    "Narrow Scope Qualifiers": (
        "Commitments exist but heavily qualified with 'only when', 'limited to', "
        "'except'. Technically commits but practically unlimited."
    ),
    "Conditional Exceptions": (
        "Commitments followed by broad exceptions ('except as described', "
        "'unless required by law'). Commitment immediately undermined."
    ),
    "Practice Saturation": (
        "Overwhelming volume of practice statements drowns out any commitments. "
        "Not necessarily hedging, just massive disclosure."
    ),
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path) as f:
        return json.load(f)


def pc_ratio(practices, commitments):
    """Practice-to-commitment ratio. Returns float('inf') if 0 commitments."""
    if commitments == 0:
        return float("inf")
    return practices / commitments


def ratio_label(r):
    if r == float("inf"):
        return "inf (no commitments)"
    return f"{r:.1f}:1"


def count_pattern(text, patterns):
    """Count occurrences of patterns in text (case-insensitive)."""
    text_lower = text.lower()
    total = 0
    for p in patterns:
        # Use word-boundary-aware matching for single words
        if " " not in p.strip():
            # Word-boundary regex for single words
            total += len(re.findall(r'\b' + re.escape(p.strip()) + r'\b', text_lower))
        else:
            total += text_lower.count(p.lower())
    return total


def count_pattern_per_statement(statements, patterns):
    """Count how many statements contain at least one pattern occurrence."""
    count = 0
    for s in statements:
        if count_pattern(s["text"], patterns) > 0:
            count += 1
    return count


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_classifications(path):
    data = load_json(path)
    return data["results"], data.get("agreement_metrics", {})


def compute_company_ratios(classifications):
    """Compute per-company counts and P:C ratios."""
    company_counts = defaultdict(Counter)
    for r in classifications:
        if r["final_classification"] is None:
            continue
        company_counts[r["company"]][r["final_classification"]] += 1

    results = []
    for company, counts in sorted(company_counts.items()):
        practices = counts.get("PRACTICE", 0)
        commitments = counts.get("COMPANY_COMMITMENT", 0)
        user_control = counts.get("USER_CONTROL", 0)
        total = practices + commitments + user_control
        ratio = pc_ratio(practices, commitments)

        results.append({
            "company": company,
            "total_statements": total,
            "practices": practices,
            "commitments": commitments,
            "user_control": user_control,
            "ratio": ratio,
            "ratio_label": ratio_label(ratio),
        })

    # Sort: infinite ratios first, then by ratio descending
    inf_companies = [r for r in results if r["ratio"] == float("inf")]
    finite_companies = [r for r in results if r["ratio"] != float("inf")]
    inf_companies.sort(key=lambda x: (-x["practices"], x["company"]))
    finite_companies.sort(key=lambda x: -x["ratio"])
    return inf_companies + finite_companies


def group_statements_by_company(classifications):
    """Group statements by company and classification."""
    grouped = defaultdict(lambda: defaultdict(list))
    for r in classifications:
        if r["final_classification"] is None:
            continue
        grouped[r["company"]][r["final_classification"]].append(r)
    return grouped


# ── Linguistic Feature Analysis ────────────────────────────────────────────────

def compute_linguistic_features(statements):
    """
    Compute linguistic feature scores for a list of statements.
    Returns a dict with raw counts and normalized rates.
    """
    if not statements:
        return {
            "n_statements": 0,
            "modal_permissive": 0, "modal_binding": 0, "modal_negation": 0,
            "hedge_conditional": 0, "hedge_generalizing": 0, "hedge_approximating": 0,
            "scope_narrow": 0, "scope_exception": 0,
            "verb_expansive": 0, "verb_protective": 0,
            "permissive_rate": 0.0, "binding_rate": 0.0, "negation_rate": 0.0,
            "conditional_rate": 0.0, "generalizing_rate": 0.0, "approximating_rate": 0.0,
            "narrow_scope_rate": 0.0, "exception_rate": 0.0,
            "expansive_rate": 0.0, "protective_rate": 0.0,
        }

    n = len(statements)

    # Count statements containing each pattern type
    modal_permissive = count_pattern_per_statement(statements, PERMISSIVE_MODALS)
    modal_binding = count_pattern_per_statement(statements, BINDING_MODALS)
    modal_negation = count_pattern_per_statement(statements, NEGATION_PATTERNS)
    hedge_conditional = count_pattern_per_statement(statements, CONDITIONAL_HEDGES)
    hedge_generalizing = count_pattern_per_statement(statements, GENERALIZING_HEDGES)
    hedge_approximating = count_pattern_per_statement(statements, APPROXIMATING_HEDGES)
    scope_narrow = count_pattern_per_statement(statements, NARROW_SCOPE)
    scope_exception = count_pattern_per_statement(statements, EXCEPTION_CLAUSES)
    verb_expansive = count_pattern_per_statement(statements, EXPANSIVE_VERBS)
    verb_protective = count_pattern_per_statement(statements, PROTECTIVE_VERBS)

    return {
        "n_statements": n,
        "modal_permissive": modal_permissive,
        "modal_binding": modal_binding,
        "modal_negation": modal_negation,
        "hedge_conditional": hedge_conditional,
        "hedge_generalizing": hedge_generalizing,
        "hedge_approximating": hedge_approximating,
        "scope_narrow": scope_narrow,
        "scope_exception": scope_exception,
        "verb_expansive": verb_expansive,
        "verb_protective": verb_protective,
        # Rates: fraction of statements containing each feature
        "permissive_rate": round(modal_permissive / n, 4),
        "binding_rate": round(modal_binding / n, 4),
        "negation_rate": round(modal_negation / n, 4),
        "conditional_rate": round(hedge_conditional / n, 4),
        "generalizing_rate": round(hedge_generalizing / n, 4),
        "approximating_rate": round(hedge_approximating / n, 4),
        "narrow_scope_rate": round(scope_narrow / n, 4),
        "exception_rate": round(scope_exception / n, 4),
        "expansive_rate": round(verb_expansive / n, 4),
        "protective_rate": round(verb_protective / n, 4),
    }


def classify_dominant_strategy(company_info, features, all_features_by_class):
    """
    Classify a company into its dominant avoidance strategy based on
    linguistic features and structural characteristics.

    Returns (strategy_name, confidence_score, reasoning).
    """
    commitments = company_info["commitments"]
    practices = company_info["practices"]
    total = company_info["total_statements"]
    ratio = company_info["ratio"]

    scores = {}

    # ── Strategy 1: Modal Hedging ──
    # High permissive modals in PRACTICE statements, low binding modals
    perm_rate = features["permissive_rate"]
    bind_rate = features["binding_rate"]
    neg_rate = features["negation_rate"]

    # Score: permissive rate relative to binding + negation
    commitment_modal_rate = bind_rate + neg_rate
    if commitment_modal_rate > 0:
        modal_imbalance = perm_rate / commitment_modal_rate
    else:
        modal_imbalance = perm_rate * 10 if perm_rate > 0 else 0

    scores["Modal Hedging"] = min(1.0, perm_rate * 2 + modal_imbalance * 0.3)

    # ── Strategy 2: Minimal Commitment Density ──
    # Few total commitments despite policy length
    if commitments < 5 and total >= 10:
        density_score = 1.0 - (commitments / 5.0)
        # Boost if total is large
        size_bonus = min(0.3, (total - 10) / 100)
        scores["Minimal Commitment Density"] = min(1.0, density_score + size_bonus)
    elif commitments < 3:
        scores["Minimal Commitment Density"] = 0.8
    else:
        scores["Minimal Commitment Density"] = max(0.0, 0.5 - commitments * 0.05)

    # ── Strategy 3: Narrow Scope Qualifiers ──
    # Commitments exist but are qualified
    scope_rate = features["narrow_scope_rate"]
    # Look specifically at commitment statements for scope qualifiers
    commit_features = all_features_by_class.get("COMPANY_COMMITMENT", {})
    commit_scope_rate = commit_features.get("narrow_scope_rate", 0)

    if commitments >= 3:
        scores["Narrow Scope Qualifiers"] = min(1.0, commit_scope_rate * 3 + scope_rate)
    else:
        scores["Narrow Scope Qualifiers"] = min(0.4, scope_rate * 1.5)

    # ── Strategy 4: Conditional Exceptions ──
    # Commitments with exception clauses
    exception_rate = features["exception_rate"]
    conditional_rate = features["conditional_rate"]
    commit_exception_rate = commit_features.get("exception_rate", 0)
    commit_conditional_rate = commit_features.get("conditional_rate", 0)

    if commitments >= 3:
        scores["Conditional Exceptions"] = min(
            1.0,
            (commit_exception_rate + commit_conditional_rate) * 2 + exception_rate * 0.5
        )
    else:
        scores["Conditional Exceptions"] = min(0.4, (exception_rate + conditional_rate) * 0.5)

    # ── Strategy 5: Practice Saturation ──
    # Overwhelming practice volume
    practice_pct = practices / total if total > 0 else 0
    scores["Practice Saturation"] = min(
        1.0,
        practice_pct * 0.8 + (practices / 50) * 0.2  # boost for sheer volume
    )

    # Determine dominant strategy
    dominant = max(scores, key=scores.get)
    confidence = scores[dominant]

    # Build reasoning
    top_two = sorted(scores.items(), key=lambda x: -x[1])[:2]
    reasoning = (
        f"Primary: {top_two[0][0]} ({top_two[0][1]:.2f}), "
        f"Secondary: {top_two[1][0]} ({top_two[1][1]:.2f})"
    )

    return dominant, round(confidence, 3), reasoning, scores


def find_exemplar_quotes(statements_by_class, strategy):
    """
    Find 2-3 exemplar quotes that best illustrate the given strategy.
    Returns list of (text, classification, reason) tuples.
    """
    exemplars = []

    all_statements = []
    for cls, stmts in statements_by_class.items():
        for s in stmts:
            all_statements.append((s["text"], cls))

    if strategy == "Modal Hedging":
        # Find statements with most permissive modals
        scored = []
        for text, cls in all_statements:
            perm_count = count_pattern(text, PERMISSIVE_MODALS)
            bind_count = count_pattern(text, BINDING_MODALS + NEGATION_PATTERNS)
            if perm_count > 0 and bind_count == 0:
                scored.append((perm_count, text, cls, "Uses permissive modal without binding language"))
        scored.sort(reverse=True)
        for _, text, cls, reason in scored[:3]:
            exemplars.append((text, cls, reason))

    elif strategy == "Minimal Commitment Density":
        # Show practice statements from a company with few/no commitments
        practices = [(s["text"], "PRACTICE") for s in statements_by_class.get("PRACTICE", [])]
        commitments = statements_by_class.get("COMPANY_COMMITMENT", [])
        # Show practice statements (they're the dominant thing)
        for text, cls in practices[:2]:
            exemplars.append((text, cls, "Practice statement with no corresponding commitment"))
        # If any commitments exist, show them
        if commitments:
            exemplars.append((
                commitments[0]["text"], "COMPANY_COMMITMENT",
                "One of very few commitment statements in policy"
            ))

    elif strategy == "Narrow Scope Qualifiers":
        # Find commitment statements with scope qualifiers
        commits = statements_by_class.get("COMPANY_COMMITMENT", [])
        scored = []
        for s in commits:
            scope_count = count_pattern(s["text"], NARROW_SCOPE)
            if scope_count > 0:
                scored.append((scope_count, s["text"], "COMPANY_COMMITMENT",
                               "Commitment narrowed by scope qualifier"))
        scored.sort(reverse=True)
        for _, text, cls, reason in scored[:3]:
            exemplars.append((text, cls, reason))
        # If not enough from commitments, check practices
        if len(exemplars) < 2:
            for text, cls in all_statements:
                if count_pattern(text, NARROW_SCOPE) > 0 and cls == "PRACTICE":
                    exemplars.append((text, cls, "Practice with scope narrowing"))
                    if len(exemplars) >= 3:
                        break

    elif strategy == "Conditional Exceptions":
        # Find statements with exception clauses
        scored = []
        for text, cls in all_statements:
            exc_count = count_pattern(text, EXCEPTION_CLAUSES)
            cond_count = count_pattern(text, CONDITIONAL_HEDGES)
            if exc_count > 0 or (cond_count > 0 and cls == "COMPANY_COMMITMENT"):
                scored.append((exc_count + cond_count, text, cls,
                               "Contains exception/conditional clause"))
        scored.sort(reverse=True)
        for _, text, cls, reason in scored[:3]:
            exemplars.append((text, cls, reason))

    elif strategy == "Practice Saturation":
        # Show the sheer volume - pick diverse practice statements
        practices = statements_by_class.get("PRACTICE", [])
        if len(practices) >= 3:
            # Pick from beginning, middle, end
            indices = [0, len(practices) // 2, len(practices) - 1]
            for i in indices:
                exemplars.append((
                    practices[i]["text"], "PRACTICE",
                    f"Practice statement {i+1} of {len(practices)}"
                ))
        else:
            for s in practices:
                exemplars.append((s["text"], "PRACTICE", "Practice statement"))

    # Truncate long quotes
    result = []
    for text, cls, reason in exemplars[:3]:
        if len(text) > 200:
            text = text[:197] + "..."
        result.append({"text": text, "classification": cls, "reason": reason})
    return result


# ── Printing ───────────────────────────────────────────────────────────────────

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def print_subsection(title):
    print(f"\n  {'─'*70}")
    print(f"  {title}")
    print(f"  {'─'*70}")


def print_table(headers, rows, widths=None):
    if widths is None:
        widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                  for i, h in enumerate(headers)]
    header_line = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    sep_line = "  ".join("-" * w for w in widths)
    print(f"  {header_line}")
    print(f"  {sep_line}")
    for row in rows:
        line = "  ".join(str(row[i]).ljust(w) for i, w in enumerate(widths))
        print(f"  {line}")


# ── Main Analysis ──────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("  LINGUISTIC STRATEGY TAXONOMY EXTRACTION")
    print("  Commitment Avoidance Strategies in Privacy Policies")
    print("=" * 80)

    # ── Load data ──
    print("\n  Loading OPPT classifications...")
    oppt_results, oppt_agreement = load_classifications(OPPT_CLASSIFICATIONS)
    print(f"    {len(oppt_results)} statements loaded")

    # ── Compute ratios ──
    print("  Computing per-company ratios...")
    company_ratios = compute_company_ratios(oppt_results)
    print(f"    {len(company_ratios)} companies analyzed")

    # ── Identify top 15 highest-ratio companies ──
    top15 = company_ratios[:15]

    print_section("TOP 15 HIGHEST P:C RATIO COMPANIES (OPPT)")
    headers = ["#", "Company", "P", "C", "UC", "Total", "Ratio"]
    rows = []
    for i, cr in enumerate(top15, 1):
        rows.append((
            i, cr["company"], cr["practices"], cr["commitments"],
            cr["user_control"], cr["total_statements"], cr["ratio_label"]
        ))
    print_table(headers, rows, [4, 25, 6, 6, 6, 7, 25])

    # ── Group all statements by company ──
    grouped = group_statements_by_company(oppt_results)

    # ── Linguistic feature analysis for top 15 ──
    print_section("LINGUISTIC FEATURE ANALYSIS (TOP 15)")

    top15_profiles = []

    for cr in top15:
        company = cr["company"]
        stmts_by_class = grouped[company]
        all_stmts = []
        for cls_stmts in stmts_by_class.values():
            all_stmts.extend(cls_stmts)

        # Compute features for all statements combined
        features_all = compute_linguistic_features(all_stmts)

        # Compute features per classification
        features_by_class = {}
        for cls in ["PRACTICE", "COMPANY_COMMITMENT", "USER_CONTROL"]:
            features_by_class[cls] = compute_linguistic_features(
                stmts_by_class.get(cls, [])
            )

        # Classify dominant strategy
        strategy, confidence, reasoning, scores = classify_dominant_strategy(
            cr, features_all, features_by_class
        )

        # Find exemplar quotes
        exemplars = find_exemplar_quotes(stmts_by_class, strategy)

        profile = {
            "company": company,
            "ratio": cr["ratio"],
            "ratio_label": cr["ratio_label"],
            "practices": cr["practices"],
            "commitments": cr["commitments"],
            "user_control": cr["user_control"],
            "total_statements": cr["total_statements"],
            "dominant_strategy": strategy,
            "confidence": confidence,
            "reasoning": reasoning,
            "strategy_scores": {k: round(v, 3) for k, v in scores.items()},
            "linguistic_features": features_all,
            "features_by_class": features_by_class,
            "exemplar_quotes": exemplars,
        }
        top15_profiles.append(profile)

    # ── Print per-company profiles for top 15 ──
    for profile in top15_profiles:
        print_subsection(
            f"{profile['company'].upper()} "
            f"(P:C = {profile['ratio_label']}, "
            f"{profile['total_statements']} statements)"
        )
        print(f"    Dominant Strategy: {profile['dominant_strategy']} "
              f"(confidence: {profile['confidence']:.2f})")
        print(f"    {profile['reasoning']}")
        print()

        # Feature summary
        f = profile["linguistic_features"]
        print(f"    Modal Analysis:")
        print(f"      Permissive (may/might/could/can): {f['modal_permissive']} stmts "
              f"({f['permissive_rate']:.1%})")
        print(f"      Binding (will/shall/must):        {f['modal_binding']} stmts "
              f"({f['binding_rate']:.1%})")
        print(f"      Negation (do not/never/cannot):   {f['modal_negation']} stmts "
              f"({f['negation_rate']:.1%})")
        print()
        print(f"    Hedging Language:")
        print(f"      Conditional:   {f['hedge_conditional']} stmts "
              f"({f['conditional_rate']:.1%})")
        print(f"      Generalizing:  {f['hedge_generalizing']} stmts "
              f"({f['generalizing_rate']:.1%})")
        print(f"      Approximating: {f['hedge_approximating']} stmts "
              f"({f['approximating_rate']:.1%})")
        print()
        print(f"    Scope Qualifiers:")
        print(f"      Narrow scope:      {f['scope_narrow']} stmts "
              f"({f['narrow_scope_rate']:.1%})")
        print(f"      Exception clauses: {f['scope_exception']} stmts "
              f"({f['exception_rate']:.1%})")
        print()
        print(f"    Action Verbs:")
        print(f"      Expansive (collect/use/share...):  {f['verb_expansive']} stmts "
              f"({f['expansive_rate']:.1%})")
        print(f"      Protective (protect/secure/limit): {f['verb_protective']} stmts "
              f"({f['protective_rate']:.1%})")
        print()

        # Strategy scores
        print(f"    Strategy Scores:")
        for strat, score in sorted(profile["strategy_scores"].items(),
                                    key=lambda x: -x[1]):
            bar = "#" * int(score * 30)
            marker = " <-- dominant" if strat == profile["dominant_strategy"] else ""
            print(f"      {strat:30s} {score:.3f}  {bar}{marker}")
        print()

        # Exemplar quotes
        if profile["exemplar_quotes"]:
            print(f"    Exemplar Quotes:")
            for j, eq in enumerate(profile["exemplar_quotes"], 1):
                print(f'      {j}. [{eq["classification"]}] "{eq["text"]}"')
                print(f'         -> {eq["reason"]}')

    # ══════════════════════════════════════════════════════════════════════
    # ── Strategy prevalence across ALL companies in OPPT ──
    # ══════════════════════════════════════════════════════════════════════

    print_section("STRATEGY PREVALENCE ACROSS ALL OPPT COMPANIES")

    all_company_strategies = []

    for cr in company_ratios:
        company = cr["company"]
        stmts_by_class = grouped[company]
        all_stmts = []
        for cls_stmts in stmts_by_class.values():
            all_stmts.extend(cls_stmts)

        features_all = compute_linguistic_features(all_stmts)
        features_by_class = {}
        for cls in ["PRACTICE", "COMPANY_COMMITMENT", "USER_CONTROL"]:
            features_by_class[cls] = compute_linguistic_features(
                stmts_by_class.get(cls, [])
            )

        strategy, confidence, reasoning, scores = classify_dominant_strategy(
            cr, features_all, features_by_class
        )

        all_company_strategies.append({
            "company": company,
            "ratio": cr["ratio"],
            "ratio_label": cr["ratio_label"],
            "practices": cr["practices"],
            "commitments": cr["commitments"],
            "total_statements": cr["total_statements"],
            "dominant_strategy": strategy,
            "confidence": confidence,
            "strategy_scores": {k: round(v, 3) for k, v in scores.items()},
            "linguistic_features": features_all,
        })

    # ── Strategy distribution ──
    strategy_counts = Counter(cs["dominant_strategy"] for cs in all_company_strategies)
    total_companies = len(all_company_strategies)

    print(f"\n  Total companies: {total_companies}\n")
    headers = ["Strategy", "Count", "%"]
    rows = []
    for strat in ["Modal Hedging", "Minimal Commitment Density",
                   "Narrow Scope Qualifiers", "Conditional Exceptions",
                   "Practice Saturation"]:
        cnt = strategy_counts.get(strat, 0)
        pct = f"{cnt / total_companies * 100:.1f}%"
        rows.append((strat, cnt, pct))
    print_table(headers, rows, [30, 8, 8])

    # ── Cross-tabulation: mean ratio by dominant strategy ──
    print_subsection("MEAN P:C RATIO BY DOMINANT STRATEGY")

    strategy_ratios = defaultdict(list)
    for cs in all_company_strategies:
        r = cs["ratio"]
        strategy_ratios[cs["dominant_strategy"]].append(r)

    headers = ["Strategy", "N", "Mean Ratio", "Median Ratio",
               "Inf-Ratio Co.", "Finite Mean"]
    rows = []
    for strat in ["Modal Hedging", "Minimal Commitment Density",
                   "Narrow Scope Qualifiers", "Conditional Exceptions",
                   "Practice Saturation"]:
        ratios = strategy_ratios.get(strat, [])
        n = len(ratios)
        n_inf = sum(1 for r in ratios if r == float("inf"))
        finite = [r for r in ratios if r != float("inf")]
        if finite:
            finite_mean = f"{mean(finite):.1f}:1"
            finite_median = f"{median(finite):.1f}:1"
        else:
            finite_mean = "N/A"
            finite_median = "N/A"
        if n_inf > 0:
            mean_label = f"inf ({n_inf} co.)" if n_inf == n else finite_mean + f" (+{n_inf} inf)"
            med_label = finite_median + f" (+{n_inf} inf)" if finite else "inf"
        else:
            mean_label = finite_mean
            med_label = finite_median
        rows.append((strat, n, mean_label, med_label, n_inf, finite_mean))
    print_table(headers, rows, [30, 5, 18, 18, 14, 14])

    # ══════════════════════════════════════════════════════════════════════
    # ── Strategy Taxonomy Table ──
    # ══════════════════════════════════════════════════════════════════════

    print_section("STRATEGY TAXONOMY")

    for strat_name in ["Modal Hedging", "Minimal Commitment Density",
                        "Narrow Scope Qualifiers", "Conditional Exceptions",
                        "Practice Saturation"]:
        cnt = strategy_counts.get(strat_name, 0)
        pct = cnt / total_companies * 100

        # Find exemplar companies (top-ratio companies with this strategy)
        exemplar_companies = [
            cs for cs in all_company_strategies
            if cs["dominant_strategy"] == strat_name
        ]
        # Sort by ratio (inf first, then descending)
        exemplar_companies.sort(
            key=lambda x: (-1e9 if x["ratio"] == float("inf") else -x["ratio"])
        )
        top_exemplars = exemplar_companies[:3]

        print_subsection(f"{strat_name}")
        print(f"    Definition: {STRATEGY_DEFINITIONS[strat_name]}")
        print(f"    Prevalence: {cnt} companies ({pct:.1f}%)")
        print(f"    Exemplar Companies: {', '.join(c['company'] for c in top_exemplars)}")

        # Find best example quotes from top exemplar companies
        print(f"    Example Quotes:")
        quotes_shown = 0
        for ec in top_exemplars:
            if quotes_shown >= 3:
                break
            company = ec["company"]
            stmts_by_class = grouped[company]
            exemplars = find_exemplar_quotes(stmts_by_class, strat_name)
            for eq in exemplars:
                if quotes_shown >= 3:
                    break
                print(f'      - [{ec["company"]}] [{eq["classification"]}] '
                      f'"{eq["text"]}"')
                quotes_shown += 1
        print()

    # ══════════════════════════════════════════════════════════════════════
    # ── Aggregate linguistic feature comparison across classes ──
    # ══════════════════════════════════════════════════════════════════════

    print_section("AGGREGATE LINGUISTIC FEATURES BY CLASSIFICATION (ALL COMPANIES)")

    # Gather all statements across all companies by classification
    all_by_class = defaultdict(list)
    for r in oppt_results:
        if r["final_classification"] is not None:
            all_by_class[r["final_classification"]].append(r)

    class_features = {}
    for cls in ["PRACTICE", "COMPANY_COMMITMENT", "USER_CONTROL"]:
        class_features[cls] = compute_linguistic_features(all_by_class[cls])

    headers = ["Feature", "PRACTICE", "COMMITMENT", "USER_CONTROL"]
    # (label, rate_key, count_key)
    feature_labels = [
        ("Permissive modals", "permissive_rate", "modal_permissive"),
        ("Binding modals", "binding_rate", "modal_binding"),
        ("Negation patterns", "negation_rate", "modal_negation"),
        ("Conditional hedges", "conditional_rate", "hedge_conditional"),
        ("Generalizing hedges", "generalizing_rate", "hedge_generalizing"),
        ("Approximating hedges", "approximating_rate", "hedge_approximating"),
        ("Narrow scope", "narrow_scope_rate", "scope_narrow"),
        ("Exception clauses", "exception_rate", "scope_exception"),
        ("Expansive verbs", "expansive_rate", "verb_expansive"),
        ("Protective verbs", "protective_rate", "verb_protective"),
    ]
    rows = []
    for label, rate_key, count_key in feature_labels:
        p_rate = class_features["PRACTICE"][rate_key]
        c_rate = class_features["COMPANY_COMMITMENT"][rate_key]
        u_rate = class_features["USER_CONTROL"][rate_key]
        rows.append((
            label,
            f"{p_rate:.1%} ({class_features['PRACTICE'][count_key]}/{class_features['PRACTICE']['n_statements']})",
            f"{c_rate:.1%} ({class_features['COMPANY_COMMITMENT'][count_key]}/{class_features['COMPANY_COMMITMENT']['n_statements']})",
            f"{u_rate:.1%} ({class_features['USER_CONTROL'][count_key]}/{class_features['USER_CONTROL']['n_statements']})",
        ))
    print()
    print_table(headers, rows, [22, 22, 22, 22])

    # ══════════════════════════════════════════════════════════════════════
    # ── Save results ──
    # ══════════════════════════════════════════════════════════════════════

    def make_serializable(obj):
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, (int, float)):
            if isinstance(obj, float) and math.isinf(obj):
                return "Infinity"
            if isinstance(obj, float) and math.isnan(obj):
                return "NaN"
            return obj
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [make_serializable(v) for v in obj]
        return obj

    output = {
        "metadata": {
            "analysis": "Linguistic Strategy Taxonomy Extraction",
            "corpus": "OPPT",
            "source": str(OPPT_CLASSIFICATIONS.relative_to(BASE)),
            "total_companies": total_companies,
            "top_n": 15,
        },
        "strategy_definitions": STRATEGY_DEFINITIONS,
        "top15_profiles": make_serializable(top15_profiles),
        "all_company_strategies": make_serializable(all_company_strategies),
        "strategy_prevalence": {
            strat: {
                "count": strategy_counts.get(strat, 0),
                "pct": round(strategy_counts.get(strat, 0) / total_companies * 100, 1),
            }
            for strat in STRATEGY_DEFINITIONS
        },
        "strategy_ratio_crosstab": make_serializable({
            strat: {
                "n": len(strategy_ratios.get(strat, [])),
                "n_infinite": sum(1 for r in strategy_ratios.get(strat, []) if r == float("inf")),
                "finite_ratios": [r for r in strategy_ratios.get(strat, []) if r != float("inf")],
                "finite_mean": round(mean([r for r in strategy_ratios.get(strat, []) if r != float("inf")]), 2) if [r for r in strategy_ratios.get(strat, []) if r != float("inf")] else None,
                "finite_median": round(median([r for r in strategy_ratios.get(strat, []) if r != float("inf")]), 2) if [r for r in strategy_ratios.get(strat, []) if r != float("inf")] else None,
            }
            for strat in STRATEGY_DEFINITIONS
        }),
        "aggregate_features_by_class": make_serializable(class_features),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n\n  Results saved to: {OUTPUT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()
