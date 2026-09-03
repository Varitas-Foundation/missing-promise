"""
Stability Comparison: Separated Judge Panel vs. Primary Panel

Compares the September 2026 stability classification run (separated judge
panel: DeepSeek V4 Flash 0731, GLM-5.3-Flash, Kimi K3) against the primary
January-February 2026 run (Claude Haiku 4.5, GPT-5-mini, Gemini 3 Flash) on
the metrics the paper reports:

  1. Three-class distribution and commitment proportion
  2. Per-company practice-to-commitment ratios (mean, median, zero-commitment)
  3. Per-category ratios (regulatory gradient)
  4. 200-statement reference set accuracy (gold_standard_200.json)
  5. Fleiss' kappa / consensus rates
  6. Contradiction cross-reference (Mann-Whitney, primary verified subset)
  7. Commitment-boundary composition in the security category
  8. Label churn between panels

The primary run's statements are the unit of comparison throughout: the
stability run classifies the identical extracted statements, so differences
isolate the judge panel (unlike the privacy washing stability run, which
changed extraction too).

Usage:
    python stability_comparison.py [--suffix stability_20260901]
"""

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

from scipy import stats as scipy_stats

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
INPUTS_DIR = DATA_DIR / "inputs"

STATEMENT_PATHS = {
    "oppt": INPUTS_DIR / "oppt_statements.json",
    "opp115": INPUTS_DIR / "opp115_statements.json",
}

JUDGE_IDS = ["judge_1", "judge_2", "judge_3"]


def load_classifications(path):
    with open(path) as f:
        data = json.load(f)
    return data


def final_labels(results):
    """statement_id -> final_classification (only consensus-labeled)."""
    return {r["statement_id"]: r["final_classification"]
            for r in results if r.get("final_classification")}


def company_of(results):
    return {r["statement_id"]: r["company"] for r in results}


def per_company_ratios(labels, companies):
    per = {}
    for sid, cls in labels.items():
        c = companies[sid]
        per.setdefault(c, Counter())[cls] += 1
    rows = []
    for c, counts in per.items():
        p = counts.get("PRACTICE", 0)
        cc = counts.get("COMPANY_COMMITMENT", 0)
        uc = counts.get("USER_CONTROL", 0)
        rows.append({
            "company": c, "practices": p, "commitments": cc, "user_control": uc,
            "ratio": (p / cc) if cc > 0 else None,
        })
    return rows


def describe_ratios(rows):
    finite = [r["ratio"] for r in rows if r["ratio"] is not None]
    zero_cc = [r["company"] for r in rows if r["ratio"] is None]
    return {
        "n_companies": len(rows),
        "n_finite": len(finite),
        "zero_commitment_companies": sorted(zero_cc),
        "mean": round(statistics.mean(finite), 2),
        "median": round(statistics.median(finite), 2),
        "std": round(statistics.stdev(finite), 2),
        "range": [round(min(finite), 2), round(max(finite), 2)],
    }


def distribution(labels):
    counts = Counter(labels.values())
    total = sum(counts.values())
    return {
        "total": total,
        "practice": counts.get("PRACTICE", 0),
        "commitment": counts.get("COMPANY_COMMITMENT", 0),
        "user_control": counts.get("USER_CONTROL", 0),
        "practice_pct": round(100 * counts.get("PRACTICE", 0) / total, 1),
        "commitment_pct": round(100 * counts.get("COMPANY_COMMITMENT", 0) / total, 1),
        "user_control_pct": round(100 * counts.get("USER_CONTROL", 0) / total, 1),
    }


def per_category(labels, categories):
    cats = {}
    for sid, cls in labels.items():
        cat = categories.get(sid, "UNKNOWN")
        cats.setdefault(cat, Counter())[cls] += 1
    out = {}
    for cat, counts in sorted(cats.items()):
        p = counts.get("PRACTICE", 0)
        cc = counts.get("COMPANY_COMMITMENT", 0)
        uc = counts.get("USER_CONTROL", 0)
        out[cat] = {
            "practices": p, "commitments": cc, "user_control": uc,
            "ratio": round(p / cc, 2) if cc else None,
        }
    return out


def gold_eval(labels):
    """Score final labels against the 200-statement reference set."""
    gold = json.load(open(DATA_DIR / "gold_standard_200.json"))["statements"]
    # The paper's evaluation excludes two statements with unresolvable
    # reference labels; those carry gold_label null/UNRESOLVED in the file.
    rows = [(g["statement_id"], g["gold_label"]) for g in gold
            if g.get("gold_label") in {"COMPANY_COMMITMENT", "PRACTICE", "USER_CONTROL"}]
    matched = [(sid, gl, labels.get(sid)) for sid, gl in rows]
    scored = [(sid, gl, pred) for sid, gl, pred in matched if pred]
    correct = sum(1 for _, gl, pred in scored if gl == pred)
    per_class = {}
    for cls in ["COMPANY_COMMITMENT", "PRACTICE", "USER_CONTROL"]:
        tp = sum(1 for _, gl, pr in scored if gl == cls and pr == cls)
        fp = sum(1 for _, gl, pr in scored if gl != cls and pr == cls)
        fn = sum(1 for _, gl, pr in scored if gl == cls and pr != cls)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[cls] = {"precision": round(prec, 3), "recall": round(rec, 3),
                          "f1": round(f1, 3), "n": tp + fn}
    confusion = Counter((gl, pr) for _, gl, pr in scored)
    return {
        "gold_n": len(rows),
        "scored_n": len(scored),
        "unscored_no_consensus": len(matched) - len(scored),
        "accuracy": round(correct / len(scored), 4) if scored else None,
        "per_class": per_class,
        "confusion": {f"{gl}->{pr}": n for (gl, pr), n in sorted(confusion.items())},
    }


def contradiction_crossref(rows, phase3_corpus):
    """Primary verified-subset Mann-Whitney with stability ratios."""
    contra = {r["company"]: r["contradiction_count"]
              for r in phase3_corpus["company_ratios"]}
    zero, has = [], []
    for r in rows:
        if r["ratio"] is None:
            continue
        c = contra.get(r["company"])
        if c is None:
            continue  # untested in companion panel
        (has if c > 0 else zero).append(r["ratio"])
    if not zero or not has:
        return None
    U, p1 = scipy_stats.mannwhitneyu(zero, has, alternative="greater")
    r_rb = 1 - 2 * U / (len(zero) * len(has))
    return {
        "n_zero": len(zero), "n_has": len(has),
        "median_zero": round(statistics.median(zero), 2),
        "median_has": round(statistics.median(has), 2),
        "U": U, "p_one_sided_greater": round(p1, 4),
        "rank_biserial_r": round(r_rb, 3),
    }


NEG = re.compile(r"\b(do(es)? not|will not|won't|never|cannot|can't|no longer)\b", re.I)
MODAL = re.compile(r"\b(will|shall|must|committed|commits?|guarantees?|ensures?|pledges?|promises?)\b", re.I)
LIMITER = re.compile(r"\bonly\b", re.I)


def security_boundary(labels, categories, texts):
    """Affirmative present-tense share of security commitments (boundary sensitivity)."""
    sec_cc = [sid for sid, cls in labels.items()
              if cls == "COMPANY_COMMITMENT" and categories.get(sid) == "SECURITY"]
    sec_p = [sid for sid, cls in labels.items()
             if cls == "PRACTICE" and categories.get(sid) == "SECURITY"]
    affirm = [sid for sid in sec_cc
              if not NEG.search(texts[sid]) and not MODAL.search(texts[sid])
              and not LIMITER.search(texts[sid])]
    n_cc, n_p, n_aff = len(sec_cc), len(sec_p), len(affirm)
    return {
        "security_practices": n_p,
        "security_commitments": n_cc,
        "ratio": round(n_p / n_cc, 2) if n_cc else None,
        "affirmative_present_tense_cc": n_aff,
        "affirmative_share_pct": round(100 * n_aff / n_cc, 1) if n_cc else None,
        "reclassified_ratio": round((n_p + n_aff) / (n_cc - n_aff), 2) if n_cc > n_aff else None,
    }


def churn(primary_labels, stability_labels):
    """Label agreement between the two panels on commonly-labeled statements."""
    common = set(primary_labels) & set(stability_labels)
    agree = sum(1 for sid in common if primary_labels[sid] == stability_labels[sid])
    moves = Counter((primary_labels[sid], stability_labels[sid])
                    for sid in common if primary_labels[sid] != stability_labels[sid])
    return {
        "common_labeled": len(common),
        "agree": agree,
        "agreement_pct": round(100 * agree / len(common), 1) if common else None,
        "moves": {f"{a}->{b}": n for (a, b), n in moves.most_common()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffix", default="stability_20260901")
    args = ap.parse_args()

    phase3 = json.load(open(DATA_DIR / "phase3_ratio_analysis.json"))
    report = {"suffix": args.suffix, "corpora": {}}

    for corpus in ["oppt", "opp115"]:
        primary = load_classifications(DATA_DIR / f"{corpus}_commitment_classifications.json")
        stability = load_classifications(DATA_DIR / f"{corpus}_commitment_classifications_{args.suffix}.json")

        stmts = json.load(open(STATEMENT_PATHS[corpus]))["statements"]
        categories = {s["statement_id"]: s.get("category", "UNKNOWN") for s in stmts}
        texts = {s["statement_id"]: s["text"] for s in stmts}

        p_labels = final_labels(primary["results"])
        s_labels = final_labels(stability["results"])
        s_companies = company_of(stability["results"])

        s_rows = per_company_ratios(s_labels, s_companies)

        report["corpora"][corpus] = {
            "stability_models": stability["metadata"]["models"],
            "distribution": {"primary": distribution(p_labels),
                             "stability": distribution(s_labels)},
            "company_ratios": {"stability": describe_ratios(s_rows)},
            "per_category": {"stability": per_category(s_labels, categories)},
            "agreement": {
                "primary": {k: primary["agreement_metrics"][k]
                            for k in ["fleiss_kappa", "unanimous_rate", "majority_rate", "split_rate"]},
                "stability": {k: stability["agreement_metrics"][k]
                              for k in ["fleiss_kappa", "unanimous_rate", "majority_rate", "split_rate"]},
            },
            "gold_eval": {"stability": gold_eval(s_labels)},
            "contradiction_crossref": {"stability": contradiction_crossref(
                s_rows, phase3[corpus])},
            "security_boundary": {"primary": security_boundary(p_labels, categories, texts),
                                  "stability": security_boundary(s_labels, categories, texts)},
            "panel_churn": churn(p_labels, s_labels),
        }

    out_path = DATA_DIR / f"stability_comparison_{args.suffix.replace('stability_', '')}.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
