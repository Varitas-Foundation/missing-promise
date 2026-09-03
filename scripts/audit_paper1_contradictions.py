"""
Paper 1 Contradiction Audit

Runs the 3-judge commitment classifier on all commitment-side statements
from Paper 1's panel-verified contradictions to check whether any were
actually USER_CONTROL statements (mislabeled as COMMITMENT).

This audit determines whether Paper 1's results need correction before publication.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Reuse the classifier infrastructure
sys.path.insert(0, str(Path(__file__).parent))
from classify_commitments import (
    OpenRouterClient,
    classify_statement_three_models,
    compute_agreement_metrics,
    load_prompt_template,
    VALID_CLASSIFICATIONS,
)

import os
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

JUDGE_MODELS = [
    os.environ.get("MULTIMODEL_1", "").strip().strip('"').strip("'"),
    os.environ.get("MULTIMODEL_2", "").strip().strip('"').strip("'"),
    os.environ.get("MULTIMODEL_3", "").strip().strip('"').strip("'"),
]

JUDGE_RESULTS_PATHS = {
    "oppt": REPO_ROOT / "data" / "inputs" / "oppt_statement_judge_results.json",
    "opp115": REPO_ROOT / "data" / "inputs" / "opp115_statement_judge_results.json",
}

OUTPUT_PATH = REPO_ROOT / "data" / "paper1_contradiction_audit.json"


def extract_commitment_statements(judge_results_path: Path) -> list[dict]:
    """Extract unique commitment-side statements from panel-verified contradictions."""
    with open(judge_results_path) as f:
        data = json.load(f)

    verified = [a for a in data["annotations"] if a.get("final_verdict") == "CONTRADICTION"]

    seen = set()
    statements = []
    for v in verified:
        sid = v["commitment_statement_id"]
        if sid not in seen:
            seen.add(sid)
            statements.append({
                "statement_id": sid,
                "company": v["company"],
                "text": v["commitment_text"],
                "category": v.get("commitment_category", ""),
                "num_contradictions_in": sum(
                    1 for vv in verified if vv["commitment_statement_id"] == sid
                ),
            })
    return statements


def main():
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key or not all(JUDGE_MODELS):
        print("ERROR: Set OPENROUTER_API_KEY and MULTIMODEL_1/2/3 in .env")
        sys.exit(1)

    template = load_prompt_template()
    client = OpenRouterClient(api_key)

    all_results = {}
    audit_summary = {}

    for corpus, path in JUDGE_RESULTS_PATHS.items():
        print(f"\n{'='*60}")
        print(f"AUDITING {corpus.upper()} CONTRADICTIONS")
        print(f"{'='*60}")

        statements = extract_commitment_statements(path)
        print(f"  Unique commitment statements to classify: {len(statements)}")

        results = []
        for i, stmt in enumerate(statements):
            result = classify_statement_three_models(
                client, stmt, JUDGE_MODELS, template, max_workers=3
            )
            results.append(result)

            cls = result["final_classification"] or "SPLIT"
            consensus = result["consensus_type"]
            original_label = "COMMITMENT"  # All were labeled COMMITMENT in Paper 1

            flag = ""
            if cls != "COMPANY_COMMITMENT":
                flag = " *** MISLABELED ***"

            print(f"  [{i+1}/{len(statements)}] {stmt['company']}: {original_label} -> {cls} ({consensus}){flag}")

            time.sleep(0.3)

        # Analyze results
        reclassified = [r for r in results if r["final_classification"] != "COMPANY_COMMITMENT"]
        user_control = [r for r in results if r["final_classification"] == "USER_CONTROL"]
        practice = [r for r in results if r["final_classification"] == "PRACTICE"]

        # Count affected contradictions
        stmt_to_cls = {r["statement_id"]: r["final_classification"] for r in results}
        affected_contradictions = sum(
            s["num_contradictions_in"] for s in statements
            if stmt_to_cls.get(s["statement_id"]) != "COMPANY_COMMITMENT"
        )
        total_contradictions = sum(s["num_contradictions_in"] for s in statements)

        corpus_summary = {
            "total_commitment_statements": len(statements),
            "correctly_labeled": len(statements) - len(reclassified),
            "reclassified_total": len(reclassified),
            "reclassified_to_user_control": len(user_control),
            "reclassified_to_practice": len(practice),
            "total_contradictions": total_contradictions,
            "affected_contradictions": affected_contradictions,
            "unaffected_contradictions": total_contradictions - affected_contradictions,
            "affected_rate": round(affected_contradictions / max(total_contradictions, 1), 4),
        }

        print(f"\n  SUMMARY for {corpus.upper()}:")
        print(f"    Correctly labeled COMPANY_COMMITMENT: {corpus_summary['correctly_labeled']}/{len(statements)}")
        print(f"    Reclassified to USER_CONTROL: {len(user_control)}")
        print(f"    Reclassified to PRACTICE: {len(practice)}")
        print(f"    Affected contradictions: {affected_contradictions}/{total_contradictions} ({corpus_summary['affected_rate']:.1%})")

        if reclassified:
            print(f"\n  RECLASSIFIED STATEMENTS:")
            for r in reclassified:
                matching = [s for s in statements if s["statement_id"] == r["statement_id"]][0]
                print(f"    [{r['company']}] {r['final_classification']} (was COMMITMENT) x{matching['num_contradictions_in']}:")
                text = r["text"]
                print(f'      "{text[:150]}..."' if len(text) > 150 else f'      "{text}"')

        all_results[corpus] = results
        audit_summary[corpus] = corpus_summary

    # Save full results
    output = {
        "metadata": {
            "purpose": "Audit Paper 1 panel-verified contradictions for commitment label accuracy",
            "methodology": "three_llm_judge_reclassification",
            "models": JUDGE_MODELS,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "summary": audit_summary,
        "results": {
            corpus: [
                {
                    "statement_id": r["statement_id"],
                    "company": r["company"],
                    "text": r["text"],
                    "original_label": "COMMITMENT",
                    "reclassified_as": r["final_classification"],
                    "consensus_type": r["consensus_type"],
                    "judge_1_classification": r["judge_1"]["classification"],
                    "judge_2_classification": r["judge_2"]["classification"],
                    "judge_3_classification": r["judge_3"]["classification"],
                }
                for r in results
            ]
            for corpus, results in all_results.items()
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"AUDIT COMPLETE")
    print(f"{'='*60}")
    print(f"Results saved to: {OUTPUT_PATH}")

    # Overall impact
    total_affected = sum(s["affected_contradictions"] for s in audit_summary.values())
    total_all = sum(s["total_contradictions"] for s in audit_summary.values())
    print(f"\nOVERALL IMPACT:")
    print(f"  Total contradictions across both corpora: {total_all}")
    print(f"  Contradictions with mislabeled commitment: {total_affected} ({total_affected/max(total_all,1):.1%})")
    print(f"  Contradictions with correct commitment: {total_all - total_affected} ({(total_all - total_affected)/max(total_all,1):.1%})")


if __name__ == "__main__":
    main()
