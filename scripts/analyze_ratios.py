#!/usr/bin/env python3
"""
Phase 3: Practice-to-Commitment Ratio Analysis

Computes per-company P:C ratios, per-category breakdowns, cross-references
with Paper 1 contradictions (corrected via audit), and runs statistical tests.

Usage:
    python analyze_ratios.py [--output-dir DIR]
"""

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, stdev

# scipy for statistical tests
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("WARNING: scipy not available. Statistical tests will be skipped.", file=sys.stderr)


# ── Paths ──────────────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
INPUTS_DIR = DATA_DIR / "inputs"

OPPT_CLASSIFICATIONS = DATA_DIR / "oppt_commitment_classifications.json"
OPP115_CLASSIFICATIONS = DATA_DIR / "opp115_commitment_classifications.json"
OPPT_STATEMENTS = INPUTS_DIR / "oppt_statements.json"
OPP115_STATEMENTS = INPUTS_DIR / "opp115_statements.json"
OPPT_JUDGE_RESULTS = INPUTS_DIR / "oppt_statement_judge_results.json"
OPP115_JUDGE_RESULTS = INPUTS_DIR / "opp115_statement_judge_results.json"
AUDIT_FILE = DATA_DIR / "paper1_contradiction_audit.json"


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path) as f:
        return json.load(f)


def pc_ratio(practices, commitments):
    """Practice-to-commitment ratio. Returns float('inf') if 0 commitments."""
    if commitments == 0:
        return float('inf')
    return practices / commitments


def ratio_label(r):
    """Human-readable ratio string."""
    if r == float('inf'):
        return "∞ (no commitments)"
    return f"{r:.1f}:1"


def ratio_bin(r):
    """Bin a ratio into the outline's categories."""
    if r == float('inf'):
        return "∞ (zero commitments)"
    if r < 3:
        return "< 3:1"
    if r < 5:
        return "3:1 to 5:1"
    if r < 7:
        return "5:1 to 7:1"
    if r < 10:
        return "7:1 to 10:1"
    return "> 10:1"


BIN_ORDER = ["< 3:1", "3:1 to 5:1", "5:1 to 7:1", "7:1 to 10:1", "> 10:1", "∞ (zero commitments)"]


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_classifications(path):
    """Load classification results, return list of dicts."""
    data = load_json(path)
    return data['results'], data.get('agreement_metrics', {})


def load_statement_categories(path):
    """Load original statements for category info, return {statement_id: category}."""
    data = load_json(path)
    return {s['statement_id']: s.get('category', 'UNKNOWN') for s in data['statements']}


def load_paper1_contradictions(judge_path, audit_path, corpus_key):
    """
    Load Paper 1 contradictions and apply audit corrections.
    Returns dict: {company: corrected_contradiction_count}
    """
    judge_data = load_json(judge_path)
    audit_data = load_json(audit_path)

    # Get original contradictions per company
    original_contradictions = defaultdict(list)
    for annot in judge_data['annotations']:
        if annot['final_verdict'] == 'CONTRADICTION':
            original_contradictions[annot['company']].append(annot)

    # Get reclassified statement IDs from audit
    reclassified_ids = set()
    for item in audit_data['results'].get(corpus_key, []):
        if item['reclassified_as'] != 'COMPANY_COMMITMENT':
            reclassified_ids.add(item['statement_id'])

    # Calculate corrected counts: remove contradictions where commitment was reclassified
    corrected = {}
    all_companies_in_judge = set(a['company'] for a in judge_data['annotations'])

    for company in all_companies_in_judge:
        original = original_contradictions.get(company, [])
        kept = [c for c in original
                if c['commitment_statement_id'] not in reclassified_ids]
        corrected[company] = len(kept)

    return corrected, all_companies_in_judge


# ── Per-Company Ratio Computation ──────────────────────────────────────────────

def compute_company_ratios(classifications):
    """
    Compute per-company counts and P:C ratios.
    Returns list of dicts sorted by ratio descending.
    """
    company_counts = defaultdict(Counter)
    for r in classifications:
        company_counts[r['company']][r['final_classification']] += 1

    results = []
    for company, counts in sorted(company_counts.items()):
        practices = counts.get('PRACTICE', 0)
        commitments = counts.get('COMPANY_COMMITMENT', 0)
        user_control = counts.get('USER_CONTROL', 0)
        total = practices + commitments + user_control
        ratio = pc_ratio(practices, commitments)

        results.append({
            'company': company,
            'total_statements': total,
            'practices': practices,
            'commitments': commitments,
            'user_control': user_control,
            'ratio': ratio,
            'ratio_label': ratio_label(ratio),
            'ratio_bin': ratio_bin(ratio),
            'pct_practice': round(practices / total * 100, 1) if total else 0,
            'pct_commitment': round(commitments / total * 100, 1) if total else 0,
            'pct_user_control': round(user_control / total * 100, 1) if total else 0,
        })

    # Sort by ratio descending (inf first)
    results.sort(key=lambda x: (-x['ratio'] if x['ratio'] != float('inf') else -1e9, x['company']))
    # Put inf-ratio companies first
    inf_companies = [r for r in results if r['ratio'] == float('inf')]
    finite_companies = [r for r in results if r['ratio'] != float('inf')]
    finite_companies.sort(key=lambda x: -x['ratio'])
    return inf_companies + finite_companies


# ── Per-Category Breakdown ─────────────────────────────────────────────────────

def compute_category_ratios(classifications, category_map):
    """
    Compute ratios broken down by privacy policy category.
    """
    cat_counts = defaultdict(Counter)
    for r in classifications:
        cat = category_map.get(r['statement_id'], 'UNKNOWN')
        cat_counts[cat][r['final_classification']] += 1

    results = []
    for cat in sorted(cat_counts.keys()):
        counts = cat_counts[cat]
        practices = counts.get('PRACTICE', 0)
        commitments = counts.get('COMPANY_COMMITMENT', 0)
        user_control = counts.get('USER_CONTROL', 0)
        total = practices + commitments + user_control
        ratio = pc_ratio(practices, commitments)

        results.append({
            'category': cat,
            'total': total,
            'practices': practices,
            'commitments': commitments,
            'user_control': user_control,
            'ratio': ratio,
            'ratio_label': ratio_label(ratio),
        })

    results.sort(key=lambda x: -x['ratio'] if x['ratio'] != float('inf') else -1e9)
    return results


# ── Cross-Reference with Paper 1 ──────────────────────────────────────────────

def cross_reference_contradictions(company_ratios, corrected_contradictions, all_judged_companies):
    """
    Merge ratio data with corrected contradiction counts.
    Companies not in judge data get contradiction_count = None.
    """
    contra_map = corrected_contradictions

    for cr in company_ratios:
        company = cr['company']
        if company in contra_map:
            cr['contradiction_count'] = contra_map[company]
            cr['has_contradictions'] = contra_map[company] > 0
            cr['in_paper1'] = True
        elif company in all_judged_companies:
            cr['contradiction_count'] = 0
            cr['has_contradictions'] = False
            cr['in_paper1'] = True
        else:
            cr['contradiction_count'] = None
            cr['has_contradictions'] = None
            cr['in_paper1'] = False

    return company_ratios


# ── Statistical Tests ──────────────────────────────────────────────────────────

def run_statistical_tests(company_ratios):
    """
    Test whether zero-contradiction companies have higher P:C ratios.
    """
    if not HAS_SCIPY:
        return {'error': 'scipy not available'}

    # Only include companies that were in Paper 1 and have finite ratios
    in_paper1 = [cr for cr in company_ratios if cr['in_paper1'] and cr['ratio'] != float('inf')]

    zero_contra = [cr['ratio'] for cr in in_paper1 if not cr['has_contradictions']]
    has_contra = [cr['ratio'] for cr in in_paper1 if cr['has_contradictions']]

    if not zero_contra or not has_contra:
        return {'error': 'insufficient data for comparison'}

    # Mann-Whitney U test (non-parametric, doesn't assume normality)
    u_stat, u_pvalue = scipy_stats.mannwhitneyu(zero_contra, has_contra, alternative='greater')

    # Also Welch's t-test for comparison
    t_stat, t_pvalue = scipy_stats.ttest_ind(zero_contra, has_contra, equal_var=False)

    # Effect size: rank-biserial correlation from Mann-Whitney
    n1, n2 = len(zero_contra), len(has_contra)
    rank_biserial = 1 - (2 * u_stat) / (n1 * n2)

    # Point-biserial correlation (ratio vs binary contradiction status)
    all_ratios = zero_contra + has_contra
    all_labels = [0] * len(zero_contra) + [1] * len(has_contra)
    pb_corr, pb_pval = scipy_stats.pointbiserialr(all_labels, all_ratios)

    # Spearman correlation (ratio vs contradiction count, for companies with contradictions)
    companies_with_data = [cr for cr in in_paper1 if cr['contradiction_count'] is not None]
    if len(companies_with_data) >= 5:
        ratios = [cr['ratio'] for cr in companies_with_data]
        counts = [cr['contradiction_count'] for cr in companies_with_data]
        spearman_r, spearman_p = scipy_stats.spearmanr(ratios, counts)
    else:
        spearman_r, spearman_p = None, None

    return {
        'zero_contradiction_companies': {
            'n': len(zero_contra),
            'mean_ratio': round(mean(zero_contra), 2),
            'median_ratio': round(median(zero_contra), 2),
            'std_ratio': round(stdev(zero_contra), 2) if len(zero_contra) > 1 else None,
        },
        'has_contradiction_companies': {
            'n': len(has_contra),
            'mean_ratio': round(mean(has_contra), 2),
            'median_ratio': round(median(has_contra), 2),
            'std_ratio': round(stdev(has_contra), 2) if len(has_contra) > 1 else None,
        },
        'mann_whitney_u': {
            'U_statistic': round(u_stat, 2),
            'p_value': round(u_pvalue, 6),
            'alternative': 'greater (zero-contra > has-contra)',
            'rank_biserial_r': round(rank_biserial, 4),
            'significant_at_05': u_pvalue < 0.05,
            'significant_at_01': u_pvalue < 0.01,
        },
        'welch_t_test': {
            't_statistic': round(t_stat, 4),
            'p_value': round(t_pvalue, 6),
        },
        'point_biserial': {
            'correlation': round(pb_corr, 4),
            'p_value': round(pb_pval, 6),
        },
        'spearman_ratio_vs_count': {
            'rho': round(spearman_r, 4) if spearman_r is not None else None,
            'p_value': round(spearman_p, 6) if spearman_p is not None else None,
        },
        'note': 'Excludes companies with zero commitments (infinite ratio) from parametric/rank tests',
    }


# ── Distribution Summary ──────────────────────────────────────────────────────

def compute_distribution(company_ratios):
    """Compute ratio distribution bins and descriptive stats."""
    all_ratios = [cr['ratio'] for cr in company_ratios]
    finite_ratios = [r for r in all_ratios if r != float('inf')]

    # Bin counts
    bins = Counter(cr['ratio_bin'] for cr in company_ratios)
    bin_table = []
    for b in BIN_ORDER:
        count = bins.get(b, 0)
        pct = round(count / len(all_ratios) * 100, 1) if all_ratios else 0
        bin_table.append({'bin': b, 'count': count, 'pct': pct})

    descriptive = {
        'n_companies': len(all_ratios),
        'n_infinite_ratio': sum(1 for r in all_ratios if r == float('inf')),
        'n_finite_ratio': len(finite_ratios),
    }

    if finite_ratios:
        descriptive.update({
            'mean': round(mean(finite_ratios), 2),
            'median': round(median(finite_ratios), 2),
            'std': round(stdev(finite_ratios), 2) if len(finite_ratios) > 1 else None,
            'min': round(min(finite_ratios), 2),
            'max': round(max(finite_ratios), 2),
            'q25': round(sorted(finite_ratios)[len(finite_ratios) // 4], 2),
            'q75': round(sorted(finite_ratios)[3 * len(finite_ratios) // 4], 2),
        })

    return {'bins': bin_table, 'descriptive': descriptive}


# ── Formatted Output ───────────────────────────────────────────────────────────

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_table(headers, rows, widths=None):
    """Print a formatted table."""
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


def format_results(corpus_name, company_ratios, category_ratios, distribution,
                   stat_tests, agreement_metrics):
    """Print formatted results for one corpus."""
    print_section(f"{corpus_name} RESULTS")

    # ── Agreement metrics
    print(f"\n  Classifier Agreement:")
    am = agreement_metrics
    print(f"    Fleiss' kappa: {am.get('fleiss_kappa', 'N/A')}")
    print(f"    Unanimous: {am.get('unanimous_rate', 'N/A'):.1%}")
    dist = am.get('classification_distribution', {})
    total = sum(dist.values())
    for cls, cnt in sorted(dist.items()):
        print(f"    {cls}: {cnt} ({cnt/total:.1%})")

    # ── Distribution
    print(f"\n  Ratio Distribution ({distribution['descriptive']['n_companies']} companies):")
    desc = distribution['descriptive']
    if 'mean' in desc:
        print(f"    Mean: {desc['mean']:.1f}:1  |  Median: {desc['median']:.1f}:1  |  "
              f"Std: {desc.get('std', 'N/A')}  |  Range: [{desc['min']:.1f}, {desc['max']:.1f}]")
    print()
    headers = ["Ratio Range", "Count", "%"]
    rows = [(b['bin'], b['count'], f"{b['pct']}%") for b in distribution['bins']]
    print_table(headers, rows, [25, 8, 8])

    # ── Top 10 highest ratio
    print(f"\n  Top 10 Highest P:C Ratio (commitment avoidance):")
    headers = ["Company", "Practices", "Commits", "User Ctrl", "Total", "Ratio"]
    top10 = company_ratios[:10]
    rows = [(cr['company'], cr['practices'], cr['commitments'], cr['user_control'],
             cr['total_statements'], cr['ratio_label']) for cr in top10]
    print_table(headers, rows, [25, 10, 10, 10, 8, 20])

    # ── Top 10 lowest ratio (most commitments relative to practices)
    finite = [cr for cr in company_ratios if cr['ratio'] != float('inf')]
    bottom10 = sorted(finite, key=lambda x: x['ratio'])[:10]
    print(f"\n  Top 10 Lowest P:C Ratio (most commitment-dense):")
    rows = [(cr['company'], cr['practices'], cr['commitments'], cr['user_control'],
             cr['total_statements'], cr['ratio_label']) for cr in bottom10]
    print_table(headers, rows, [25, 10, 10, 10, 8, 20])

    # ── Per-category breakdown
    print(f"\n  Per-Category P:C Ratios:")
    headers = ["Category", "Practices", "Commits", "User Ctrl", "Total", "Ratio"]
    rows = [(cr['category'], cr['practices'], cr['commitments'], cr['user_control'],
             cr['total'], cr['ratio_label']) for cr in category_ratios]
    print_table(headers, rows, [22, 10, 10, 10, 8, 15])

    # ── Contradiction cross-reference
    if stat_tests and 'error' not in stat_tests:
        print(f"\n  Contradiction Cross-Reference (Paper 1):")
        zc = stat_tests['zero_contradiction_companies']
        hc = stat_tests['has_contradiction_companies']
        print(f"    Zero contradictions:  n={zc['n']}, mean ratio={zc['mean_ratio']:.1f}:1, "
              f"median={zc['median_ratio']:.1f}:1")
        print(f"    Has contradictions:   n={hc['n']}, mean ratio={hc['mean_ratio']:.1f}:1, "
              f"median={hc['median_ratio']:.1f}:1")
        mw = stat_tests['mann_whitney_u']
        print(f"\n    Mann-Whitney U test (zero-contra > has-contra):")
        print(f"      U = {mw['U_statistic']}, p = {mw['p_value']:.6f}")
        print(f"      Rank-biserial r = {mw['rank_biserial_r']:.4f}")
        sig = "***" if mw['significant_at_01'] else ("*" if mw['significant_at_05'] else "n.s.")
        print(f"      Significance: {sig}")

        sp = stat_tests.get('spearman_ratio_vs_count', {})
        if sp.get('rho') is not None:
            print(f"\n    Spearman (ratio vs contradiction count):")
            print(f"      rho = {sp['rho']:.4f}, p = {sp['p_value']:.6f}")


# ── Main ───────────────────────────────────────────────────────────────────────

def analyze_corpus(corpus_name, cls_path, stmt_path, judge_path, audit_path, audit_key):
    """Full analysis for one corpus."""
    print(f"\n  Loading {corpus_name} data...")
    classifications, agreement = load_classifications(cls_path)
    category_map = load_statement_categories(stmt_path)
    corrected_contra, all_judged = load_paper1_contradictions(judge_path, audit_path, audit_key)

    print(f"  Computing per-company ratios...")
    company_ratios = compute_company_ratios(classifications)

    print(f"  Computing per-category ratios...")
    category_ratios = compute_category_ratios(classifications, category_map)

    print(f"  Cross-referencing with Paper 1 contradictions...")
    company_ratios = cross_reference_contradictions(company_ratios, corrected_contra, all_judged)

    print(f"  Running statistical tests...")
    stat_tests = run_statistical_tests(company_ratios)

    distribution = compute_distribution(company_ratios)

    # Format output
    format_results(corpus_name, company_ratios, category_ratios, distribution,
                   stat_tests, agreement)

    return {
        'company_ratios': company_ratios,
        'category_ratios': category_ratios,
        'distribution': distribution,
        'statistical_tests': stat_tests,
        'agreement_metrics': agreement,
    }


def compare_corpora(oppt_results, opp115_results):
    """Print cross-corpus comparison."""
    print_section("OPPT vs OPP-115 COMPARISON")

    oppt_d = oppt_results['distribution']['descriptive']
    opp_d = opp115_results['distribution']['descriptive']

    headers = ["Metric", "OPPT", "OPP-115"]
    rows = [
        ("Companies", oppt_d['n_companies'], opp_d['n_companies']),
        ("Mean ratio", f"{oppt_d.get('mean', 'N/A')}:1", f"{opp_d.get('mean', 'N/A')}:1"),
        ("Median ratio", f"{oppt_d.get('median', 'N/A')}:1", f"{opp_d.get('median', 'N/A')}:1"),
        ("Std dev", oppt_d.get('std', 'N/A'), opp_d.get('std', 'N/A')),
        ("Min ratio", f"{oppt_d.get('min', 'N/A')}:1", f"{opp_d.get('min', 'N/A')}:1"),
        ("Max ratio", f"{oppt_d.get('max', 'N/A')}:1", f"{opp_d.get('max', 'N/A')}:1"),
        ("Zero-commitment companies", oppt_d.get('n_infinite_ratio', 0), opp_d.get('n_infinite_ratio', 0)),
    ]
    print()
    print_table(headers, rows, [30, 18, 18])

    # Compare bins
    print(f"\n  Distribution Comparison:")
    headers = ["Ratio Range", "OPPT", "OPPT %", "OPP-115", "OPP-115 %"]
    oppt_bins = {b['bin']: b for b in oppt_results['distribution']['bins']}
    opp_bins = {b['bin']: b for b in opp115_results['distribution']['bins']}
    rows = []
    for b in BIN_ORDER:
        ob = oppt_bins.get(b, {'count': 0, 'pct': 0})
        op = opp_bins.get(b, {'count': 0, 'pct': 0})
        rows.append((b, ob['count'], f"{ob['pct']}%", op['count'], f"{op['pct']}%"))
    print_table(headers, rows, [25, 8, 10, 8, 10])

    # Mann-Whitney U between corpora
    if HAS_SCIPY:
        oppt_finite = [cr['ratio'] for cr in oppt_results['company_ratios'] if cr['ratio'] != float('inf')]
        opp_finite = [cr['ratio'] for cr in opp115_results['company_ratios'] if cr['ratio'] != float('inf')]
        u, p = scipy_stats.mannwhitneyu(oppt_finite, opp_finite, alternative='two-sided')
        print(f"\n  Cross-corpus Mann-Whitney U (two-sided):")
        print(f"    U = {u:.1f}, p = {p:.6f}")
        print(f"    {'Significant' if p < 0.05 else 'Not significant'} at α=0.05")


def main():
    parser = argparse.ArgumentParser(description="Phase 3: P:C Ratio Analysis")
    parser.add_argument("--output-dir", type=str, default=str(DATA_DIR),
                        help="Directory for output files")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    print("=" * 70)
    print("  PHASE 3: PRACTICE-TO-COMMITMENT RATIO ANALYSIS")
    print("=" * 70)

    # ── OPPT ──
    oppt_results = analyze_corpus(
        "OPPT", OPPT_CLASSIFICATIONS, OPPT_STATEMENTS,
        OPPT_JUDGE_RESULTS, AUDIT_FILE, "oppt"
    )

    # ── OPP-115 ──
    opp115_results = analyze_corpus(
        "OPP-115", OPP115_CLASSIFICATIONS, OPP115_STATEMENTS,
        OPP115_JUDGE_RESULTS, AUDIT_FILE, "opp115"
    )

    # ── Cross-corpus comparison ──
    compare_corpora(oppt_results, opp115_results)

    # ── Save full results ──
    def make_serializable(obj):
        """Convert inf/nan/numpy types to JSON-safe values."""
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, (int, float)):
            if isinstance(obj, float) and math.isinf(obj):
                return "Infinity"
            if isinstance(obj, float) and math.isnan(obj):
                return "NaN"
            return obj
        # Handle numpy bool_ and other numpy types
        try:
            import numpy as np
            if isinstance(obj, (np.bool_, np.integer, np.floating)):
                return obj.item()
        except ImportError:
            pass
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [make_serializable(v) for v in obj]
        return obj

    output = {
        'metadata': {
            'analysis': 'Phase 3: Practice-to-Commitment Ratio Analysis',
            'oppt_source': str(OPPT_CLASSIFICATIONS.relative_to(BASE)),
            'opp115_source': str(OPP115_CLASSIFICATIONS.relative_to(BASE)),
        },
        'oppt': make_serializable(oppt_results),
        'opp115': make_serializable(opp115_results),
    }

    output_path = output_dir / "phase3_ratio_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n\n  Results saved to: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
