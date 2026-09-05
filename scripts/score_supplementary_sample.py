"""Score the 60-statement supplementary reference sample of marker-free statements.

The sample (data/supplementary_sample_60_blind.csv) was drawn on 2026-09-04 with seed
20260904 from three strata, 10 statements per stratum per corpus:
  A  marker-free statements both panels label COMPANY_COMMITMENT
  B  marker-free statements the primary panel labels COMPANY_COMMITMENT and the
     separated panel labels PRACTICE (the contested set)
  C  marker-free statements both panels label PRACTICE, drawn through a filter for
     protective vocabulary that was not preserved; its rate is reported within the
     sample only and is not weighted to a pool
Statements already in the 200-statement reference set were excluded, and at most two
statements per company were drawn. Candidate labels and one-line rationales were
proposed by Claude Fable 5.1 (claude-fable-5-1, 2026-09-05) from the labeling file,
the paper's taxonomy and validation sections, the classification prompt, and the
reference set with its adjudicated labels, without the panel labels or strata; the
author reviewed all 60 and approved them without change. This script joins the labels
to the key and reports, per stratum, agreement with each panel, the implied precision
of each panel on marker-free commitments, the commitment count and proportion each
corpus would have under the adjudicated rates (the marked commitments are taken as
correct and stratum C adds nothing back), and the sensitivity of the precision figure
to the alternative readings recorded in the rationales.

Usage:
    python score_supplementary_sample.py [--file data/supplementary_sample_60_labeling.md]
"""
import argparse, csv, json, math, re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
NORM = {"CC": "COMPANY_COMMITMENT", "COMPANY_COMMITMENT": "COMPANY_COMMITMENT",
        "P": "PRACTICE", "PRACTICE": "PRACTICE", "UC": "USER_CONTROL", "USER_CONTROL": "USER_CONTROL"}
CC, P = "COMPANY_COMMITMENT", "PRACTICE"

# Marker set of the paper's boundary analysis (identical to stability_comparison.py).
NEG = re.compile(r"\b(do(es)? not|will not|won't|never|cannot|can't|no longer)\b", re.I)
MODAL = re.compile(r"\b(will|shall|must|committed|commits?|guarantees?|ensures?|pledges?|promises?)\b", re.I)
LIMITER = re.compile(r"\bonly\b", re.I)
def marker_free(text):
    return not (NEG.search(text) or MODAL.search(text) or LIMITER.search(text))

# Fallback pool sizes (OPPT + OPP-115) if the classification files are absent.
POOL_FALLBACK = {"A": 253 + 154, "B": 245 + 143}
CORPORA = (("OPPT", "oppt_commitment_classifications.json", "oppt_commitment_classifications_stability_20260901.json"),
           ("OPP-115", "opp115_commitment_classifications.json", "opp115_commitment_classifications_stability_20260901.json"))
# A rationale records an alternative reading when it says how the label would be reversed.
REVERSAL = re.compile(r"relabel|would call it|paired with", re.I)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def read_labels(path):
    labels, notes = {}, {}
    if path.endswith(".md"):
        text = Path(path).read_text()
        for block in re.split(r"^### \d+\.", text, flags=re.M)[1:]:
            sid = re.search(r"<!-- id: (\S+) -->", block)
            lab = re.search(r"^LABEL:[ \t]*(\S*)[ \t]*$", block, flags=re.M)
            note = re.search(r"^NOTES:[ \t]*(.*)$", block, flags=re.M)
            if sid and lab and lab.group(1):
                labels[sid.group(1)] = NORM.get(lab.group(1).strip().upper(), lab.group(1).strip().upper())
                notes[sid.group(1)] = note.group(1).strip() if note else ""
    else:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                raw = (row.get("your_label (CC / P / UC)") or "").strip().upper()
                if raw:
                    labels[row["statement_id"]] = NORM.get(raw, raw)
                    notes[row["statement_id"]] = (row.get("notes") or "").strip()
    return labels, notes


def corpus_pools():
    """Per-corpus primary-panel counts and marker-free strata pools, from the released classifications."""
    out = {}
    for corpus, primary, separated in CORPORA:
        try:
            prim = json.load(open(DATA / primary))["results"]
            sep = {r["statement_id"]: r.get("final_classification") for r in json.load(open(DATA / separated))["results"]}
        except FileNotFoundError:
            return None
        n_cc = n_labeled = A = B = other = 0
        for r in prim:
            lab = r.get("final_classification")
            if lab not in NORM.values():
                continue
            n_labeled += 1
            if lab != CC:
                continue
            n_cc += 1
            if not marker_free(r["text"]):
                continue
            s = sep.get(r["statement_id"])
            if s == CC: A += 1
            elif s == P: B += 1
            else: other += 1  # separated panel user control, split, or unlabeled
        out[corpus] = {"labeled": n_labeled, "cc": n_cc, "A": A, "B": B, "other_marker_free_cc": other}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DATA / "supplementary_sample_60_labeling.md"),
                    help="labeled Markdown file (default) or the blind CSV")
    args = ap.parse_args()
    key = {r["statement_id"]: r for r in json.load(open(DATA / "supplementary_sample_60_key.json"))}
    labels, notes = read_labels(args.file)
    if not labels:
        print("No labels filled in yet."); return
    print(f"labeled: {len(labels)} of {len(key)}\n")
    by = defaultdict(list)
    for sid, lab in labels.items():
        by[key[sid]["stratum"]].append((key[sid], lab, notes.get(sid, "")))
    rate = {}
    for stratum, desc in (("A", "both panels CC"), ("B", "primary CC, separated P"), ("C", "both panels P, protective vocabulary")):
        rows = by.get(stratum, [])
        if not rows: continue
        n = len(rows); cc = sum(1 for _, l, _ in rows if l == CC)
        lo, hi = wilson(cc, n); rate[stratum] = (cc, n)
        prim_agree = sum(1 for k, l, _ in rows if l == k["primary"]); sep_agree = sum(1 for k, l, _ in rows if l == k["separated"])
        print(f"stratum {stratum} ({desc}): n={n}  adjudicated CC={cc} ({100*cc/n:.0f}%; Wilson 95% {100*lo:.0f}-{100*hi:.0f}%)  "
              f"agree with primary {prim_agree}/{n}  with separated {sep_agree}/{n}")
        for corpus in ("OPPT", "OPP-115"):
            sub = [(k, l) for k, l, _ in rows if k["corpus"] == corpus]
            if sub: print(f"    {corpus:8} n={len(sub)} CC={sum(1 for _, l in sub if l == CC)}")
    if "A" not in rate or "B" not in rate:
        return
    pools = corpus_pools()
    pool = ({s: sum(c[s] for c in pools.values()) for s in "AB"} if pools else POOL_FALLBACK)
    pa = rate["A"][0] / rate["A"][1]; pb = rate["B"][0] / rate["B"][1]
    w = (pa * pool["A"] + pb * pool["B"]) / (pool["A"] + pool["B"])
    print(f"\npools (marker-free, both corpora): A={pool['A']} B={pool['B']}"
          + ("" if pools else "  [fallback constants; classification files not found]"))
    print(f"primary-panel precision on marker-free commitments, pool-weighted: {100*w:.1f}%  (A {100*pa:.0f}%, B {100*pb:.0f}%)")
    print(f"separated-panel precision on A alone: {100*pa:.0f}%; separated-panel recall loss implied by B: {100*pb:.0f}% of B are true commitments it dropped")
    if "C" in rate:
        pc = rate["C"][0] / rate["C"][1]
        print(f"stratum C: {100*pc:.0f}% of protective statements both panels call practices are adjudicated commitments (a recall signal for both panels; not pool-weighted)")
    # Implied commitment counts: marked commitments and the marker-free commitments outside strata A and B
    # are taken as correct; strata A and B are scaled by their adjudicated rates; stratum C adds nothing back.
    if pools:
        k = rate["A"][0] + rate["B"][0]; n = rate["A"][1] + rate["B"][1]
        plo, phi = wilson(k, n)
        print(f"\nimplied commitment counts (point estimate; interval from the unstratified Wilson interval on the pooled {k}/{n}: {100*plo:.0f}-{100*phi:.0f}%):")
        for corpus, c in pools.items():
            base = c["cc"] - c["A"] - c["B"]
            point = base + pa * c["A"] + pb * c["B"]
            lo = base + plo * (c["A"] + c["B"]); hi = base + phi * (c["A"] + c["B"])
            print(f"  {corpus:8} primary CC={c['cc']} of {c['labeled']} ({100*c['cc']/c['labeled']:.1f}%); A={c['A']} B={c['B']} other marker-free CC={c['other_marker_free_cc']}; "
                  f"implied CC~{point:.0f} ({100*point/c['labeled']:.1f}%), interval {100*lo/c['labeled']:.1f}-{100*hi/c['labeled']:.1f}%")
    # Sensitivity to the alternative readings recorded in the rationales.
    rev = {s: [(l, k) for k, l, note in by.get(s, []) if REVERSAL.search(note)] for s in "ABC"}
    if any(rev.values()):
        print("\nreading sensitivity (rationales recording an alternative reading: "
              + ", ".join(f"{s} {sum(1 for l,_ in rev[s] if l==CC)} CC / {sum(1 for l,_ in rev[s] if l!=CC)} P" for s in "ABC") + "):")
        for direction, sign in (("all reversals toward practice", -1), ("all reversals toward commitment", +1)):
            adj = {}
            for s in "AB":
                cc, n = rate[s]
                delta = sum(1 for l, _ in rev[s] if (l == CC) == (sign < 0))
                adj[s] = (cc + sign * delta) / n
            ww = (adj["A"] * pool["A"] + adj["B"] * pool["B"]) / (pool["A"] + pool["B"])
            print(f"  {direction:34} A {100*adj['A']:.0f}%  B {100*adj['B']:.0f}%  pool-weighted {100*ww:.0f}%")


if __name__ == "__main__":
    main()
