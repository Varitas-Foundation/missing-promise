#!/usr/bin/env python3
"""
Inferential statistics for "The Missing Promise".

Computes every inferential quantity reported in the paper that is not already
produced by analyze_ratios.py or stability_comparison.py:

  * commitment/practice elasticity (log-log regression), primary and stability panels
  * Spearman correlation of ratio and commitment share with policy length
  * chi-square homogeneity of commitment share across companies
  * chi-square of commitment/practice composition across categories
  * exact binomial per-company tests under Bonferroni correction
  * permutation test of per-company ratio variance
  * Kruskal-Wallis sector tests, combined corpora and OPPT only
  * rights-based user-control reclassification
  * commitment-boundary sensitivity by category
  * split-as-commitment robustness check
  * primary-versus-stability panel agreement, Cohen's kappa, per-class retention

Every figure printed here appears in the paper. Run from anywhere; paths are
resolved relative to this file.

Usage:
    python analyze_inferential.py [--json OUT.json]
"""

import argparse
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median, mean

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("WARNING: scipy not available; tests requiring it are skipped.", file=sys.stderr)


# ── Paths ──────────────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
INPUTS_DIR = DATA_DIR / "inputs"

CLASSIFICATIONS = {
    "oppt": DATA_DIR / "oppt_commitment_classifications.json",
    "opp115": DATA_DIR / "opp115_commitment_classifications.json",
}
STABILITY = {
    "oppt": DATA_DIR / "oppt_commitment_classifications_stability_20260901.json",
    "opp115": DATA_DIR / "opp115_commitment_classifications_stability_20260901.json",
}
STATEMENTS = {
    "oppt": INPUTS_DIR / "oppt_statements.json",
    "opp115": INPUTS_DIR / "opp115_statements.json",
}
RATIO_ANALYSIS = DATA_DIR / "phase3_ratio_analysis.json"
INDUSTRY_ANALYSIS = DATA_DIR / "industry_analysis.json"

PRACTICE = "PRACTICE"
COMMITMENT = "COMPANY_COMMITMENT"
USER_CONTROL = "USER_CONTROL"

SEED = 20260903


# ── Loading ────────────────────────────────────────────────────────────────────

def load_results(path):
    with open(path) as fh:
        payload = json.load(fh)
    return payload["results"] if isinstance(payload, dict) else payload


def per_company_counts(results, extra_commitment_ids=frozenset()):
    """Return {company: [n_practice, n_commitment, n_user_control]}."""
    counts = defaultdict(lambda: [0, 0, 0])
    for row in results:
        label = row.get("final_classification")
        company = row["company"]
        if label == PRACTICE:
            counts[company][0] += 1
        elif label == COMMITMENT:
            counts[company][1] += 1
        elif label == USER_CONTROL:
            if row["statement_id"] in extra_commitment_ids:
                counts[company][1] += 1
            else:
                counts[company][2] += 1
    return counts


def finite_ratios(counts):
    return [p / c for p, c, _ in counts.values() if c > 0]


# ── Statistics ─────────────────────────────────────────────────────────────────

def ols_loglog(counts):
    """Regress ln(commitments) on ln(practices) across companies."""
    xs, ys, names = [], [], []
    for company, (p, c, _) in counts.items():
        if p > 0 and c > 0:
            xs.append(math.log(p))
            ys.append(math.log(c))
            names.append(company)
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    sigma2 = sum(r * r for r in resid) / (n - 2)
    se = math.sqrt(sigma2 / sxx)
    syy = sum((y - my) ** 2 for y in ys)
    r2 = 1 - sum(r * r for r in resid) / syy
    tcrit = scipy_stats.t.ppf(0.975, n - 2) if HAS_SCIPY else 1.98
    t_vs_one = (slope - 1) / se
    p_vs_one = 2 * scipy_stats.t.sf(abs(t_vs_one), n - 2) if HAS_SCIPY else float("nan")
    resid_sd = math.sqrt(sigma2)
    scored = sorted(
        (
            {
                "company": name,
                "practices": int(round(math.exp(x))),
                "commitments": int(round(math.exp(y))),
                "predicted": math.exp(intercept + slope * x),
                "residual": r,
                "residual_sd_units": r / resid_sd,
            }
            for name, x, y, r in zip(names, xs, ys, resid)
        ),
        key=lambda d: d["residual"],
    )
    return {
        "slope": slope,
        "intercept": intercept,
        "ci_low": slope - tcrit * se,
        "ci_high": slope + tcrit * se,
        "r2": r2,
        "n": n,
        "p_vs_one": p_vs_one,
        "pct_increase_on_doubling": 100 * (2 ** slope - 1),
        "residual_sd": resid_sd,
        "most_negative_residuals": scored[:5],
        "most_positive_residuals": scored[-5:][::-1],
        "residuals_by_company": {d["company"]: d["residual_sd_units"] for d in scored},
    }


def length_correlations(counts):
    lengths_ratio, ratios = [], []
    lengths_all, shares = [], []
    for p, c, uc in counts.values():
        total = p + c + uc
        if c > 0:
            lengths_ratio.append(total)
            ratios.append(p / c)
        if p + c > 0:
            lengths_all.append(total)
            shares.append(c / (p + c))
    rho_ratio = scipy_stats.spearmanr(lengths_ratio, ratios)
    rho_share = scipy_stats.spearmanr(lengths_all, shares)
    return {
        "rho_ratio_vs_length": rho_ratio.statistic,
        "p_ratio": rho_ratio.pvalue,
        "n_ratio": len(ratios),
        "rho_share_vs_length": rho_share.statistic,
        "p_share": rho_share.pvalue,
        "n_share": len(shares),
    }


def homogeneity_across_companies(counts):
    """Chi-square test that commitment share is constant across companies."""
    rows = [(p, c) for p, c, _ in counts.values() if (p + c) > 0]
    total_p = sum(p for p, _ in rows)
    total_c = sum(c for _, c in rows)
    grand = total_p + total_c
    chi2 = 0.0
    for p, c in rows:
        n = p + c
        exp_p = n * total_p / grand
        exp_c = n * total_c / grand
        if exp_p > 0:
            chi2 += (p - exp_p) ** 2 / exp_p
        if exp_c > 0:
            chi2 += (c - exp_c) ** 2 / exp_c
    df = len(rows) - 1
    p_value = scipy_stats.chi2.sf(chi2, df) if HAS_SCIPY else float("nan")

    # Many companies have expected commitment counts below 5, so the asymptotic
    # reference distribution is not reliable. Re-test by Monte Carlo: resample
    # each company's commitments binomially at the pooled share, holding the
    # per-company statement total fixed.
    mc_p = float("nan")
    mc_iters = 10000
    if HAS_SCIPY:
        rng = random.Random(SEED)
        share = total_c / grand
        extreme = 0
        for _ in range(mc_iters):
            stat = 0.0
            for p_obs, c_obs in rows:
                n = p_obs + c_obs
                c_sim = sum(1 for _ in range(n) if rng.random() < share)
                p_sim = n - c_sim
                exp_p = n * (1 - share)
                exp_c = n * share
                if exp_p > 0:
                    stat += (p_sim - exp_p) ** 2 / exp_p
                if exp_c > 0:
                    stat += (c_sim - exp_c) ** 2 / exp_c
            if stat >= chi2:
                extreme += 1
        mc_p = (extreme + 1) / (mc_iters + 1)
    small_expected = sum(1 for p_obs, c_obs in rows
                         if (p_obs + c_obs) * (total_c / grand) < 5)
    return {
        "chi2": chi2,
        "df": df,
        "p": p_value,
        "n_companies": len(rows),
        "monte_carlo_p": mc_p,
        "monte_carlo_iterations": mc_iters,
        "companies_with_expected_cc_below_5": small_expected,
    }


def composition_across_categories(counts_by_category, categories):
    rows = [(counts_by_category[k][0], counts_by_category[k][1]) for k in categories]
    total_p = sum(p for p, _ in rows)
    total_c = sum(c for _, c in rows)
    grand = total_p + total_c
    chi2 = 0.0
    for p, c in rows:
        n = p + c
        for obs, tot in ((p, total_p), (c, total_c)):
            exp = n * tot / grand
            if exp > 0:
                chi2 += (obs - exp) ** 2 / exp
    df = len(rows) - 1
    p_value = scipy_stats.chi2.sf(chi2, df) if HAS_SCIPY else float("nan")
    return {"chi2": chi2, "df": df, "p": p_value, "k_categories": len(rows)}


def per_company_binomial(counts):
    """Exact binomial tests against the pooled commitment share, Bonferroni."""
    total_p = sum(p for p, _, _ in counts.values())
    total_c = sum(c for _, c, _ in counts.values())
    base = total_c / (total_p + total_c)
    n_companies = len(counts)
    alpha = 0.05 / n_companies
    survivors = []
    above = []
    for company, (p, c, _) in counts.items():
        n = p + c
        if n == 0:
            continue
        # two-sided exact binomial; both directions are reported
        result = scipy_stats.binomtest(c, n, base, alternative="two-sided")
        if result.pvalue < alpha:
            record = {"company": company, "commitments": c, "n": n, "p": result.pvalue}
            (survivors if c / n < base else above).append(record)
    survivors.sort(key=lambda d: d["p"])
    above.sort(key=lambda d: d["p"])
    return {
        "base_rate": base,
        "alpha": alpha,
        "n_companies": n_companies,
        "below_baseline": survivors,
        "above_baseline": above,
    }


def permutation_variance(counts, base_rates, iterations=10000, seed=SEED):
    """Permutation test of per-company ratio variance under random assignment."""
    rng = random.Random(seed)
    observed = finite_ratios(counts)
    obs_var = _variance(observed)
    totals = [p + c + uc for p, c, uc in counts.values()]
    p_rate, c_rate, uc_rate = base_rates
    cum = [p_rate, p_rate + c_rate, 1.0]
    null_vars = []
    for _ in range(iterations):
        ratios = []
        for n in totals:
            np_, nc = 0, 0
            for _ in range(n):
                u = rng.random()
                if u < cum[0]:
                    np_ += 1
                elif u < cum[1]:
                    nc += 1
            if nc > 0:
                ratios.append(np_ / nc)
        null_vars.append(_variance(ratios))
    extreme = sum(1 for v in null_vars if v >= obs_var)
    return {
        "observed_variance": obs_var,
        "null_mean": mean(null_vars),
        "p": (extreme + 1) / (iterations + 1),
        "iterations": iterations,
        "seed": seed,
    }


def _variance(values):
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def kruskal_sectors(company_ratios, sectors, min_n=5):
    groups = defaultdict(list)
    for company, ratio in company_ratios.items():
        sector = sectors.get(company)
        if sector and math.isfinite(ratio):
            groups[sector].append(ratio)
    kept = {k: v for k, v in groups.items() if len(v) >= min_n and k != "Other"}
    if len(kept) < 2:
        return None
    result = scipy_stats.kruskal(*kept.values())
    k = len(kept)
    n = sum(len(v) for v in kept.values())
    eps2 = (result.statistic - k + 1) / (n - k)
    return {"H": result.statistic, "p": result.pvalue, "epsilon_squared": eps2, "k": k, "N": n}


RIGHTS_MARKERS = re.compile(r"(right to|entitled to|have the right)", re.I)


def rights_reclassification(results):
    baseline = per_company_counts(results)
    uc = [r for r in results if r.get("final_classification") == USER_CONTROL]
    hits = {r["statement_id"] for r in uc if RIGHTS_MARKERS.search(r["text"])}
    shifted = per_company_counts(results, extra_commitment_ids=hits)
    m0, m1 = median(finite_ratios(baseline)), median(finite_ratios(shifted))
    return {
        "n_user_control": len(uc),
        "n_rights_based": len(hits),
        "pct_rights_based": 100 * len(hits) / len(uc),
        "median_before": m0,
        "median_after": m1,
        "pct_change": 100 * (m1 - m0) / m0,
    }


# Identical to the marker set in stability_comparison.py, so the boundary
# figures here match the ones reported in the paper.
NEG = re.compile(r"\b(do(es)? not|will not|won't|never|cannot|can't|no longer)\b", re.I)
MODAL = re.compile(r"\b(will|shall|must|committed|commits?|guarantees?|ensures?|pledges?|promises?)\b", re.I)
LIMITER = re.compile(r"\bonly\b", re.I)


def marker_free(text):
    return not (NEG.search(text) or MODAL.search(text) or LIMITER.search(text))


def boundary_sensitivity(results, categories):
    """Share of commitments that are marker-free, and the ratio if they were practices."""
    out = {}
    by_cat = defaultdict(lambda: {"p": 0, "cc": 0, "cc_marker_free": 0})
    for row in results:
        label = row.get("final_classification")
        cat = categories.get(row["statement_id"], "UNKNOWN")
        if label == PRACTICE:
            by_cat[cat]["p"] += 1
        elif label == COMMITMENT:
            by_cat[cat]["cc"] += 1
            if marker_free(row["text"]):
                by_cat[cat]["cc_marker_free"] += 1
    for cat, d in by_cat.items():
        if d["cc"] == 0:
            continue
        strict_cc = d["cc"] - d["cc_marker_free"]
        out[cat] = {
            "practices": d["p"],
            "commitments": d["cc"],
            "marker_free": d["cc_marker_free"],
            "pct_marker_free": 100 * d["cc_marker_free"] / d["cc"],
            "ratio": d["p"] / d["cc"],
            "ratio_if_reclassified": (d["p"] + d["cc_marker_free"]) / strict_cc if strict_cc else float("inf"),
        }
    return out


def split_as_commitment(results):
    counts = defaultdict(lambda: [0, 0])
    for row in results:
        label = row.get("final_classification")
        if label == PRACTICE:
            counts[row["company"]][0] += 1
        elif label == COMMITMENT or label is None:
            counts[row["company"]][1] += 1
    return median([p / c for p, c in counts.values() if c > 0])


def panel_comparison(primary, stability):
    p_labels = {r["statement_id"]: r.get("final_classification") for r in primary}
    s_labels = {r["statement_id"]: r.get("final_classification") for r in stability}
    shared = [i for i in p_labels if p_labels[i] and s_labels.get(i)]
    agree = sum(1 for i in shared if p_labels[i] == s_labels[i])
    labels = [PRACTICE, COMMITMENT, USER_CONTROL]
    matrix = {a: Counter() for a in labels}
    for i in shared:
        matrix[p_labels[i]][s_labels[i]] += 1
    n = len(shared)
    po = agree / n
    pe = sum(
        (sum(matrix[a].values()) / n) * (sum(matrix[b][a] for b in labels) / n)
        for a in labels
    )
    kappa = (po - pe) / (1 - pe)
    retention = {
        a: 100 * matrix[a][a] / sum(matrix[a].values()) for a in labels if sum(matrix[a].values())
    }
    return {
        "n_common": n,
        "agreement_pct": 100 * po,
        "cohens_kappa": kappa,
        "retention_pct": retention,
        "commitment_to_practice": matrix[COMMITMENT][PRACTICE],
        "practice_to_commitment": matrix[PRACTICE][COMMITMENT],
    }


# ── Driver ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, help="write all results to this JSON file")
    parser.add_argument("--iterations", type=int, default=10000, help="permutation test iterations")
    args = parser.parse_args()

    if not HAS_SCIPY:
        print("scipy is required for the full run; install it and re-run.", file=sys.stderr)
        return 1

    report = {}

    with open(RATIO_ANALYSIS) as fh:
        ratio_analysis = json.load(fh)
    sectors = {}
    if INDUSTRY_ANALYSIS.exists():
        with open(INDUSTRY_ANALYSIS) as fh:
            industry = json.load(fh)
        for corpus_key in ("oppt", "opp115"):
            sectors.update(industry.get(corpus_key, {}).get("company_mappings", {}))

    for corpus in ("oppt", "opp115"):
        print(f"\n{'=' * 72}\n{corpus.upper()}\n{'=' * 72}")
        results = load_results(CLASSIFICATIONS[corpus])
        counts = per_company_counts(results)
        section = {}

        ratios = finite_ratios(counts)
        section["median_ratio"] = median(ratios)
        section["n_finite"] = len(ratios)
        print(f"median ratio                 {median(ratios):.4f}  (n = {len(ratios)})")

        section["elasticity"] = ols_loglog(counts)
        e = section["elasticity"]
        print(f"elasticity ln(CC)~ln(P)      {e['slope']:.3f}  CI [{e['ci_low']:.3f}, {e['ci_high']:.3f}]  "
              f"R2 = {e['r2']:.2f}  n = {e['n']}  p(slope=1) = {e['p_vs_one']:.2e}")
        print(f"  doubling practices          +{e['pct_increase_on_doubling']:.0f}% commitments")

        section["length"] = length_correlations(counts)
        L = section["length"]
        print(f"Spearman ratio ~ length      rho = {L['rho_ratio_vs_length']:.4f}  p = {L['p_ratio']:.2e}")
        print(f"Spearman share ~ length      rho = {L['rho_share_vs_length']:.4f}  p = {L['p_share']:.2e}")

        section["homogeneity"] = homogeneity_across_companies(counts)
        H = section["homogeneity"]
        print(f"homogeneity across companies chi2 = {H['chi2']:.2f}  df = {H['df']}  p = {H['p']:.2e}")
        print(f"  Monte Carlo p = {H['monte_carlo_p']:.2e} "
              f"({H['monte_carlo_iterations']} draws); "
              f"{H['companies_with_expected_cc_below_5']} companies have expected CC < 5")

        section["binomial"] = per_company_binomial(counts)
        B = section["binomial"]
        print(f"exact binomial, Bonferroni   base = {B['base_rate']:.4f}  alpha = {B['alpha']:.2e}")
        for row in B["below_baseline"]:
            print(f"  below baseline: {row['company']:<20} {row['commitments']}/{row['n']}  p = {row['p']:.2e}")
        if not B["below_baseline"]:
            print("  no company below the threshold")
        for row in B["above_baseline"]:
            print(f"  above baseline: {row['company']:<20} {row['commitments']}/{row['n']}  p = {row['p']:.2e}")
        if not B["above_baseline"]:
            print("  no company above the threshold")
        print("length-adjusted residuals from the elasticity fit "
              f"(intercept {e['intercept']:.3f}, residual SD {e['residual_sd']:.3f}):")
        for row in e["most_negative_residuals"]:
            print(f"  fewest given length: {row['company']:<20} {row['commitments']}/"
                  f"{row['practices'] + row['commitments']}  predicted CC = {row['predicted']:.1f}  "
                  f"{row['residual_sd_units']:+.2f} SD")
        for row in e["most_positive_residuals"]:
            print(f"  most given length:   {row['company']:<20} {row['commitments']}/"
                  f"{row['practices'] + row['commitments']}  predicted CC = {row['predicted']:.1f}  "
                  f"{row['residual_sd_units']:+.2f} SD")
        for name in [r["company"] for r in B["below_baseline"]]:
            if name in e["residuals_by_company"]:
                print(f"  binomial outlier {name:<20} sits {e['residuals_by_company'][name]:+.2f} SD "
                      "from the length-adjusted expectation")

        total = [0, 0, 0]
        for p, c, uc in counts.values():
            total[0] += p
            total[1] += c
            total[2] += uc
        grand = sum(total)
        base_rates = tuple(v / grand for v in total)
        section["permutation"] = permutation_variance(counts, base_rates, iterations=args.iterations)
        P = section["permutation"]
        print(f"permutation variance test    observed = {P['observed_variance']:.2f}  "
              f"null mean = {P['null_mean']:.2f}  p = {P['p']:.3f}")

        section["rights_reclassification"] = rights_reclassification(results)
        R = section["rights_reclassification"]
        print(f"rights-based UC reclass      {R['n_rights_based']}/{R['n_user_control']} "
              f"({R['pct_rights_based']:.1f}%)  median {R['median_before']:.2f} -> {R['median_after']:.2f} "
              f"({R['pct_change']:+.1f}%)")

        section["split_as_commitment"] = split_as_commitment(results)
        print(f"split-as-commitment median   {section['split_as_commitment']:.4f}")

        if STATEMENTS[corpus].exists():
            with open(STATEMENTS[corpus]) as fh:
                statements = json.load(fh)["statements"]
            categories = {s["statement_id"]: s.get("category", "UNKNOWN") for s in statements}
            section["boundary_sensitivity"] = boundary_sensitivity(results, categories)
            print("boundary sensitivity by category:")
            for cat, d in sorted(section["boundary_sensitivity"].items(), key=lambda kv: kv[1]["ratio"]):
                if d["practices"] + d["commitments"] < 30:
                    continue
                print(f"  {cat:<22} ratio {d['ratio']:6.2f} -> {d['ratio_if_reclassified']:6.2f}  "
                      f"marker-free {d['pct_marker_free']:5.1f}% ({d['marker_free']}/{d['commitments']})")
            cat_counts = defaultdict(lambda: [0, 0])
            for row in results:
                label = row.get("final_classification")
                cat = categories.get(row["statement_id"], "UNKNOWN")
                if label == PRACTICE:
                    cat_counts[cat][0] += 1
                elif label == COMMITMENT:
                    cat_counts[cat][1] += 1
            major = ["SALE_SHARING", "RETENTION", "SECURITY", "FIRST_PARTY", "THIRD_PARTY", "TRACKING"]
            major = [c for c in major if c in cat_counts]
            section["category_composition"] = composition_across_categories(cat_counts, major)
            C = section["category_composition"]
            print(f"composition across categories chi2 = {C['chi2']:.2f}  df = {C['df']}  p = {C['p']:.2e}")
        else:
            print(f"  (statements file absent: {STATEMENTS[corpus]}; category analyses skipped)")

        if STABILITY[corpus].exists():
            stability = load_results(STABILITY[corpus])
            section["panel_comparison"] = panel_comparison(results, stability)
            PC = section["panel_comparison"]
            print(f"panel agreement              {PC['agreement_pct']:.1f}%  kappa = {PC['cohens_kappa']:.4f}")
            for label, pct in PC["retention_pct"].items():
                print(f"  retention {label:<20} {pct:.1f}%")
            print(f"  CC -> P {PC['commitment_to_practice']},  P -> CC {PC['practice_to_commitment']}")
            stab_counts = per_company_counts(stability)
            section["elasticity_stability"] = ols_loglog(stab_counts)
            es = section["elasticity_stability"]
            print(f"elasticity (stability panel) {es['slope']:.3f}  CI [{es['ci_low']:.3f}, {es['ci_high']:.3f}]  "
                  f"n = {es['n']}")
            section["median_ratio_stability"] = median(finite_ratios(stab_counts))
            print(f"median ratio (stability)     {section['median_ratio_stability']:.4f}")

        report[corpus] = section

    if sectors:
        print(f"\n{'=' * 72}\nSECTOR TESTS\n{'=' * 72}")
        combined, oppt_only = {}, {}
        for corpus in ("oppt", "opp115"):
            for row in ratio_analysis[corpus]["company_ratios"]:
                value = row["ratio"]
                r = float("inf") if value == "Infinity" else float(value)
                combined[row["company"]] = r
                if corpus == "oppt":
                    oppt_only[row["company"]] = r
        report["sector_combined"] = kruskal_sectors(combined, sectors)
        report["sector_oppt_only"] = kruskal_sectors(oppt_only, sectors)
        for name, key in (("combined corpora", "sector_combined"), ("OPPT only", "sector_oppt_only")):
            res = report[key]
            if res:
                print(f"Kruskal-Wallis, {name:<18} H = {res['H']:.2f}  p = {res['p']:.2e}  "
                      f"eps2 = {res['epsilon_squared']:.3f}  k = {res['k']}  N = {res['N']}")
    else:
        print(f"\n(industry file absent: {INDUSTRY_ANALYSIS}; sector tests skipped)")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"\nwrote {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
