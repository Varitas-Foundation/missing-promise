"""No-name ablation: separated panel with company names masked vs. the same panel with names.

Compares two classification runs of the separated judge panel (DeepSeek V4 Flash,
GLM-5.3-Flash, Kimi K3) over the identical extracted statements and byte-identical
prompt template. The only difference is that the masked run replaced the company in
the prompt's COMPANY slot and every observed surface form of its name in the statement
text with "the company" (classify_commitments.py --mask-company). Differences therefore
isolate the effect of naming the company.

Reports, per corpus: three-class distribution and commitment proportion; per-company
ratio summaries; label churn with Cohen's kappa and per-class retention; per-category
ratios for the gradient anchors; reference-set accuracy; the elasticity slope; the
contradiction cross-reference; and the ratio shift for the companies the paper names.
It also tests whether the change in a company's commitment share is associated with
how often its name appeared in its own statements (a proxy for name salience).

Usage:
    python ablation_comparison.py [--named stability_20260901] [--masked noname_20260904]
"""
import argparse, json, math, statistics
from collections import Counter, defaultdict
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stability_comparison import (DATA_DIR, STATEMENT_PATHS, load_classifications, final_labels,
                                  company_of, per_company_ratios, describe_ratios, distribution,
                                  per_category, gold_eval, contradiction_crossref)
from scipy import stats as scipy_stats

FOCUS = ["meta", "t-mobile", "uber", "hilton", "pimeyes", "eyematch-ai", "kochava", "avast",
         "airbnb", "netflix", "google", "apple", "microsoft", "amazon"]
ANCHORS = ["SALE_SHARING", "SECURITY", "RETENTION", "TRACKING", "THIRD_PARTY", "FIRST_PARTY"]
LABELS = ["COMPANY_COMMITMENT", "PRACTICE", "USER_CONTROL"]


def cohens_kappa(a, b):
    common = [s for s in a if s in b]
    n = len(common)
    if not n:
        return None, 0
    po = sum(1 for s in common if a[s] == b[s]) / n
    ca, cb = Counter(a[s] for s in common), Counter(b[s] for s in common)
    pe = sum(ca[k] * cb[k] for k in LABELS) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else None, n


def retention(named, masked):
    out = {}
    for lab in LABELS:
        ids = [s for s, l in named.items() if l == lab and s in masked]
        kept = sum(1 for s in ids if masked[s] == lab)
        out[lab] = {"n": len(ids), "retained_pct": round(100 * kept / len(ids), 1) if ids else None}
    return out


def elasticity(rows):
    xs = [math.log(r["practices"]) for r in rows if r["practices"] > 0 and r["commitments"] > 0]
    ys = [math.log(r["commitments"]) for r in rows if r["practices"] > 0 and r["commitments"] > 0]
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs); sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx; icpt = my - slope * mx
    resid = [y - (icpt + slope * x) for x, y in zip(xs, ys)]
    se = math.sqrt(sum(r * r for r in resid) / (n - 2) / sxx)
    t = scipy_stats.t.ppf(0.975, n - 2)
    return {"slope": round(slope, 3), "ci": [round(slope - t * se, 3), round(slope + t * se, 3)], "n": n}


def name_salience(results_named):
    """Per company: how many of its own statements mention any surface form of its name."""
    forms = json.load(open(DATA_DIR / "company_name_forms.json"))
    import re
    hits = Counter(); tot = Counter()
    for r in results_named:
        co = r["company"]; tot[co] += 1
        stems = {f.rstrip(".").replace("'s", "") for f in forms.get(co, []) if len(f) >= 2}
        if any(re.search(r"(?<![A-Za-z0-9])" + re.escape(s) + r"(?![A-Za-z0-9])", r["text"]) for s in stems):
            hits[co] += 1
    return {co: hits[co] / tot[co] for co in tot}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--named", default="stability_20260901")
    ap.add_argument("--masked", default="noname_20260904")
    args = ap.parse_args()
    phase3 = json.load(open(DATA_DIR / "phase3_ratio_analysis.json"))
    report = {"named": args.named, "masked": args.masked, "corpora": {}}

    for corpus in ["oppt", "opp115"]:
        def path_for(suffix):
            return DATA_DIR / (f"{corpus}_commitment_classifications_{suffix}.json" if suffix
                               else f"{corpus}_commitment_classifications.json")
        named = load_classifications(path_for(args.named))
        masked = load_classifications(path_for(args.masked))
        stmts = json.load(open(STATEMENT_PATHS[corpus]))["statements"]
        categories = {s["statement_id"]: s.get("category", "UNKNOWN") for s in stmts}
        nl, ml = final_labels(named["results"]), final_labels(masked["results"])
        comp = company_of(named["results"])
        n_rows, m_rows = per_company_ratios(nl, comp), per_company_ratios(ml, {**comp, **company_of(masked["results"])})
        n_by = {r["company"]: r for r in n_rows}; m_by = {r["company"]: r for r in m_rows}
        kappa, n_common = cohens_kappa(nl, ml)
        agree = sum(1 for s in nl if s in ml and nl[s] == ml[s])
        moves = Counter((nl[s], ml[s]) for s in nl if s in ml and nl[s] != ml[s])

        focus = {}
        for co in FOCUS:
            if co in n_by and co in m_by:
                focus[co] = {"named": {k: n_by[co][k] for k in ("practices", "commitments", "ratio")},
                             "masked": {k: m_by[co][k] for k in ("practices", "commitments", "ratio")}}

        # name salience vs change in commitment share
        sal = name_salience(named["results"])
        xs, ys = [], []
        for co, nr in n_by.items():
            mr = m_by.get(co)
            if not mr: continue
            d_n = nr["practices"] + nr["commitments"]; d_m = mr["practices"] + mr["commitments"]
            if d_n and d_m:
                xs.append(sal.get(co, 0.0)); ys.append(mr["commitments"] / d_m - nr["commitments"] / d_n)
        rho, p = scipy_stats.spearmanr(xs, ys) if len(xs) > 5 else (None, None)
        hi = [y for x, y in zip(xs, ys) if x >= statistics.median(xs)]; lo = [y for x, y in zip(xs, ys) if x < statistics.median(xs)]

        cats_n, cats_m = per_category(nl, categories), per_category(ml, categories)
        report["corpora"][corpus] = {
            "masked_metadata": {k: masked["metadata"].get(k) for k in ("models", "prompt_hash", "company_masked", "total_classified")},
            "distribution": {"named": distribution(nl), "masked": distribution(ml)},
            "company_ratios": {"named": describe_ratios(n_rows), "masked": describe_ratios(m_rows)},
            "churn": {"common": n_common, "agreement_pct": round(100 * agree / n_common, 2), "cohens_kappa": round(kappa, 4),
                      "moves": {f"{a}->{b}": n for (a, b), n in moves.most_common()}, "retention": retention(nl, ml)},
            "per_category_anchors": {c: {"named": cats_n.get(c), "masked": cats_m.get(c)} for c in ANCHORS},
            "gold_eval": {"named": gold_eval(nl), "masked": gold_eval(ml)},
            "elasticity": {"named": elasticity(n_rows), "masked": elasticity(m_rows)},
            "contradiction_crossref": {"named": contradiction_crossref(n_rows, phase3[corpus]),
                                       "masked": contradiction_crossref(m_rows, phase3[corpus])},
            "focus_companies": focus,
            "name_salience": {"spearman_rho": round(rho, 3) if rho is not None else None, "p": round(p, 3) if p is not None else None,
                              "n": len(xs), "mean_share_change_high_salience": round(statistics.mean(hi), 4) if hi else None,
                              "mean_share_change_low_salience": round(statistics.mean(lo), 4) if lo else None},
            "agreement": {"named": {k: named["agreement_metrics"][k] for k in ("fleiss_kappa", "unanimous_rate", "split_rate")},
                          "masked": {k: masked["agreement_metrics"][k] for k in ("fleiss_kappa", "unanimous_rate", "split_rate")}},
        }
    out = DATA_DIR / f"ablation_comparison_{args.masked}.json"
    json.dump(report, open(out, "w"), indent=2)
    for corpus, r in report["corpora"].items():
        print(f"\n=== {corpus.upper()} ===")
        print(f"commitment proportion  named {r['distribution']['named']['commitment_pct']}%  masked {r['distribution']['masked']['commitment_pct']}%")
        print(f"median ratio           named {r['company_ratios']['named']['median']}  masked {r['company_ratios']['masked']['median']}")
        print(f"churn                  agreement {r['churn']['agreement_pct']}%  kappa {r['churn']['cohens_kappa']}  moves {r['churn']['moves']}")
        print(f"CC retention           {r['churn']['retention']['COMPANY_COMMITMENT']['retained_pct']}%")
        for c in ANCHORS:
            a = r["per_category_anchors"][c]
            print(f"  {c:13} ratio named {a['named'] and a['named']['ratio']}  masked {a['masked'] and a['masked']['ratio']}")
        print(f"reference accuracy     named {r['gold_eval']['named'].get('accuracy_pct')}  masked {r['gold_eval']['masked'].get('accuracy_pct')}")
        print(f"elasticity             named {r['elasticity']['named']['slope']}  masked {r['elasticity']['masked']['slope']}")
        print(f"name salience vs share change: rho {r['name_salience']['spearman_rho']} p {r['name_salience']['p']}  "
              f"high {r['name_salience']['mean_share_change_high_salience']}  low {r['name_salience']['mean_share_change_low_salience']}")
        for co, f in r["focus_companies"].items():
            print(f"  {co:12} named {f['named']['commitments']:3}/{f['named']['practices']:3} ratio {f['named']['ratio'] and round(f['named']['ratio'],1)}   masked {f['masked']['commitments']:3}/{f['masked']['practices']:3} ratio {f['masked']['ratio'] and round(f['masked']['ratio'],1)}")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
