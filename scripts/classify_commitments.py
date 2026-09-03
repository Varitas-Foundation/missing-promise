"""
3-LLM-Judge Commitment Classifier

Classifies privacy policy statements into three categories using speech act theory:
  - COMPANY_COMMITMENT: Self-binding promises/limitations by the company
  - PRACTICE: Descriptive statements about what the company does
  - USER_CONTROL: Descriptions of user capabilities/rights

Architecture:
  - 3 LLMs via OpenRouter (same panel as Paper 1)
  - ThreadPoolExecutor parallel execution per statement
  - Majority-vote consensus with agreement metrics
  - Incremental save for long-running jobs

Input:  statements.json (from Paper 1 extraction)
Output: commitment_classifications.json with per-statement verdicts + agreement metrics

Usage:
    python classify_commitments.py --corpus oppt
    python classify_commitments.py --corpus opp115
    python classify_commitments.py --corpus oppt --resume
    python classify_commitments.py --corpus oppt --companies meta uber airbnb
    python classify_commitments.py --corpus oppt --sample 100
"""

import json
import os
import sys
import time
import random
import hashlib
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths & environment
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

JUDGE_MODELS = [
    os.environ.get("MULTIMODEL_1", ""),
    os.environ.get("MULTIMODEL_2", ""),
    os.environ.get("MULTIMODEL_3", ""),
]
JUDGE_MODELS = [m.strip().strip('"').strip("'") for m in JUDGE_MODELS]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
VALID_CLASSIFICATIONS = {"COMPANY_COMMITMENT", "PRACTICE", "USER_CONTROL"}

SCRIPT_DIR = Path(__file__).parent
PROMPT_FILE = SCRIPT_DIR / "classify_commitment_prompt.md"

# Corpus paths
CORPUS_PATHS = {
    "oppt": REPO_ROOT / "data" / "inputs" / "oppt_statements.json",
    "opp115": REPO_ROOT / "data" / "inputs" / "opp115_statements.json",
}

OUTPUT_DIR = REPO_ROOT / "data"


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
def load_prompt_template() -> str:
    """Load classification prompt template."""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt file not found: {PROMPT_FILE}")
    return PROMPT_FILE.read_text(encoding="utf-8")


def build_prompt(statement_text: str, company: str, template: str) -> str:
    """Insert statement data into prompt template."""
    return template.format(
        statement_text=statement_text,
        company=company,
    )


# ---------------------------------------------------------------------------
# OpenRouter client (adapted from Paper 1 judge_contradictions.py)
# ---------------------------------------------------------------------------
class OpenRouterClient:
    """Client for OpenRouter API supporting multiple model providers."""

    def __init__(self, api_key: str, timeout: float = 90.0):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = OPENROUTER_BASE_URL

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/dark-patterns-research",
            "X-Title": "Empty Promise Commitment Classifier",
        }

    def classify(self, prompt: str, model: str, judge_id: str) -> dict:
        """Send classification request to OpenRouter."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            # 4096 (was 512): reasoning models (e.g. glm-5.3-flash) consume
            # completion budget on reasoning tokens before emitting content;
            # at 512 they can return empty content (same failure mode as the
            # privacy washing stability judge stage, commit 1c20938). Observed
            # completions for this task run ~200-600 tokens including
            # reasoning; 4096 gives ample headroom while halving OpenRouter's
            # per-request credit pre-authorization vs 8192 (concurrent 8192
            # reservations triggered HTTP 402 on a low-balance account).
            "max_tokens": 4096,
            "temperature": 0,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()

                data = response.json()
                raw = (data["choices"][0]["message"].get("content") or "").strip()
                usage = data.get("usage", {})

                # Empty content despite HTTP 200: transient provider failure
                # (observed with reasoning models); retry like a rate limit.
                # Same fix as the privacy washing stability judge stage.
                if not raw:
                    return {
                        "classification": None,
                        "reasoning": "",
                        "raw_response": "",
                        "valid": False,
                        "judge_id": judge_id,
                        "model": model,
                        "provider": model.split("/")[0] if "/" in model else "unknown",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": "EMPTY_CONTENT",
                        "retry": True,
                    }

                parsed = _parse_response(raw)

                return {
                    "classification": parsed.get("classification"),
                    "reasoning": parsed.get("reasoning", ""),
                    "raw_response": raw,
                    "valid": parsed.get("classification") in VALID_CLASSIFICATIONS,
                    "judge_id": judge_id,
                    "model": model,
                    "provider": model.split("/")[0] if "/" in model else "unknown",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "usage": usage,
                }

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429 or status == 402 or status >= 500:
                # Retryable: rate limit, credit pre-authorization collision
                # (402 under concurrent reservations), or transient 5xx.
                return {
                    "classification": None,
                    "reasoning": "",
                    "raw_response": str(e),
                    "valid": False,
                    "judge_id": judge_id,
                    "model": model,
                    "provider": model.split("/")[0] if "/" in model else "unknown",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": f"RETRYABLE (HTTP {status})",
                    "retry": True,
                }
            return {
                "classification": None,
                "reasoning": "",
                "raw_response": str(e),
                "valid": False,
                "judge_id": judge_id,
                "model": model,
                "provider": model.split("/")[0] if "/" in model else "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"HTTP {status}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {
                "classification": None,
                "reasoning": "",
                "raw_response": str(e),
                "valid": False,
                "judge_id": judge_id,
                "model": model,
                "provider": model.split("/")[0] if "/" in model else "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }


def _parse_response(raw: str) -> dict:
    """Extract classification JSON from LLM response."""
    import re
    text = raw.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object from surrounding text
        match = re.search(r'\{[^{}]*"classification"[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                return {"classification": None}
        else:
            # Last resort: look for classification value in text
            for cls in VALID_CLASSIFICATIONS:
                if cls in text.upper():
                    return {"classification": cls, "reasoning": text[:200]}
            return {"classification": None}

    # Normalize
    classification = parsed.get("classification", "")
    if isinstance(classification, str):
        classification = classification.strip().upper()
    parsed["classification"] = classification if classification in VALID_CLASSIFICATIONS else None

    return parsed


# ---------------------------------------------------------------------------
# 3-Judge classification
# ---------------------------------------------------------------------------
def classify_statement_three_models(
    client: OpenRouterClient,
    statement: dict,
    models: list[str],
    template: str,
    max_workers: int = 3,
    max_retries: int = 2,
) -> dict:
    """
    Classify a single statement with 3 models in parallel.
    Returns per-judge classifications, consensus, and metadata.
    """
    judge_ids = ["judge_1", "judge_2", "judge_3"]
    prompt = build_prompt(statement["text"], statement["company"], template)
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(client.classify, prompt, model, jid): (jid, model)
            for jid, model in zip(judge_ids, models)
        }

        for future in as_completed(futures):
            jid, model = futures[future]
            try:
                results[jid] = future.result()
            except Exception as e:
                results[jid] = {
                    "classification": None,
                    "reasoning": "",
                    "raw_response": str(e),
                    "valid": False,
                    "judge_id": jid,
                    "model": model,
                    "error": str(e),
                }

    # Retry rate-limited judges
    for jid in judge_ids:
        if results[jid].get("retry"):
            for attempt in range(max_retries):
                time.sleep(2 ** (attempt + 1))
                model = results[jid]["model"]
                results[jid] = client.classify(prompt, model, jid)
                if results[jid]["valid"] or not results[jid].get("retry"):
                    break

    # -- Consensus analysis --
    valid_classifications = [
        results[jid]["classification"]
        for jid in judge_ids
        if results[jid]["valid"]
    ]

    cls_counts = Counter(valid_classifications)

    if len(valid_classifications) < 2:
        consensus_type = "insufficient_valid"
        final_classification = None
        needs_review = True
    elif len(cls_counts) == 1:
        consensus_type = "unanimous"
        final_classification = valid_classifications[0]
        needs_review = False
    elif cls_counts.most_common(1)[0][1] >= 2:
        consensus_type = "majority"
        final_classification = cls_counts.most_common(1)[0][0]
        needs_review = False
    else:
        consensus_type = "split"
        final_classification = None
        needs_review = True

    # Pairwise agreement
    pairwise = {}
    for i, jid1 in enumerate(judge_ids):
        for jid2 in judge_ids[i + 1:]:
            key = f"{jid1}_vs_{jid2}"
            if results[jid1]["valid"] and results[jid2]["valid"]:
                pairwise[key] = results[jid1]["classification"] == results[jid2]["classification"]
            else:
                pairwise[key] = None

    return {
        "statement_id": statement["statement_id"],
        "company": statement["company"],
        "text": statement["text"],
        "original_type": statement.get("type"),
        "judge_1": results["judge_1"],
        "judge_2": results["judge_2"],
        "judge_3": results["judge_3"],
        "consensus_type": consensus_type,
        "final_classification": final_classification,
        "classification_distribution": dict(cls_counts),
        "pairwise_agreement": pairwise,
        "needs_review": needs_review,
    }


# ---------------------------------------------------------------------------
# Agreement metrics
# ---------------------------------------------------------------------------
def compute_fleiss_kappa(judgments: list[list[str]], categories: list[str]) -> float:
    """Compute Fleiss' kappa for 3 raters."""
    n = len(judgments)
    k = len(categories)
    if n == 0:
        return 0.0

    cat_idx = {c: i for i, c in enumerate(categories)}
    num_raters = len(judgments[0])

    # Build rating matrix
    matrix = []
    for item_votes in judgments:
        row = [0] * k
        for vote in item_votes:
            if vote in cat_idx:
                row[cat_idx[vote]] += 1
        matrix.append(row)

    # P_i for each item
    p_items = []
    for row in matrix:
        n_j = sum(row)
        if n_j < 2:
            continue
        p_i = (sum(x * x for x in row) - n_j) / (n_j * (n_j - 1))
        p_items.append(p_i)

    if not p_items:
        return 0.0

    P_bar = sum(p_items) / len(p_items)

    # P_e
    col_sums = [0] * k
    total_votes = 0
    for row in matrix:
        for j in range(k):
            col_sums[j] += row[j]
        total_votes += sum(row)

    P_e = sum((col_sums[j] / total_votes) ** 2 for j in range(k)) if total_votes > 0 else 0

    if P_e == 1.0:
        return 1.0

    return (P_bar - P_e) / (1 - P_e)


def compute_agreement_metrics(results: list[dict]) -> dict:
    """Compute agreement metrics across all classified statements."""
    categories = sorted(VALID_CLASSIFICATIONS)
    judge_ids = ["judge_1", "judge_2", "judge_3"]

    # Build judgment matrix for Fleiss' kappa
    judgments = []
    consensus_counts = Counter()
    total_valid = 0

    for r in results:
        votes = []
        for jid in judge_ids:
            if r[jid]["valid"]:
                votes.append(r[jid]["classification"])
        if len(votes) >= 2:
            judgments.append(votes)
            total_valid += 1

        consensus_counts[r["consensus_type"]] += 1

    # Fleiss' kappa
    fleiss = compute_fleiss_kappa(judgments, categories)

    # Pairwise agreement rates
    pairwise_agree = {}
    for pair_key in ["judge_1_vs_judge_2", "judge_1_vs_judge_3", "judge_2_vs_judge_3"]:
        agreements = [r["pairwise_agreement"].get(pair_key) for r in results if r["pairwise_agreement"].get(pair_key) is not None]
        if agreements:
            pairwise_agree[pair_key] = sum(agreements) / len(agreements)
        else:
            pairwise_agree[pair_key] = None

    return {
        "total_statements": len(results),
        "valid_for_kappa": total_valid,
        "fleiss_kappa": round(fleiss, 4),
        "consensus_counts": dict(consensus_counts),
        "unanimous_rate": round(consensus_counts.get("unanimous", 0) / max(len(results), 1), 4),
        "majority_rate": round(consensus_counts.get("majority", 0) / max(len(results), 1), 4),
        "split_rate": round(consensus_counts.get("split", 0) / max(len(results), 1), 4),
        "pairwise_agreement_rates": pairwise_agree,
        "classification_distribution": dict(Counter(
            r["final_classification"] for r in results if r["final_classification"]
        )),
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="3-LLM Commitment Classifier")
    parser.add_argument("--corpus", choices=["oppt", "opp115"], required=True)
    parser.add_argument("--models", nargs=3, default=None, help="Override judge models")
    parser.add_argument("--rate-limit", type=float, default=0.0, help="Seconds between statements (sequential mode only)")
    parser.add_argument("--concurrency", type=int, default=3, help="Max parallel judge calls per statement")
    parser.add_argument("--parallel", type=int, default=10, help="Number of statements to classify in parallel")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run")
    parser.add_argument("--companies", nargs="*", help="Only classify these companies")
    parser.add_argument("--sample", type=int, default=None, help="Random sample of N statements")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    parser.add_argument("--output-suffix", default=None,
                        help="Write to {corpus}_commitment_classifications_{suffix}.json "
                             "instead of overwriting the primary output")
    parser.add_argument("--judge-panel", action="store_true",
                        help="Use JUDGE_MODEL_1/2/3 from .env (separated stability panel) "
                             "instead of the legacy MULTIMODEL_1/2/3 panel")
    parser.add_argument("--retry-insufficient", action="store_true",
                        help="With --resume: re-run statements whose stored result is "
                             "insufficient_valid (fewer than 2 valid judge responses, "
                             "e.g. after transient HTTP 402/5xx errors)")
    args = parser.parse_args()

    # Models
    if args.judge_panel and not args.models:
        panel = [os.environ.get(f"JUDGE_MODEL_{i}", "").strip().strip('"').strip("'") for i in (1, 2, 3)]
        models = panel
    else:
        models = args.models or JUDGE_MODELS
    if not all(models):
        print("ERROR: Set MULTIMODEL_1/2/3 in .env or use --models flag")
        sys.exit(1)
    print(f"Models: {models}")

    # API key
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("ERROR: Set OPENROUTER_API_KEY in .env")
        sys.exit(1)

    # Load data
    corpus_path = CORPUS_PATHS[args.corpus]
    print(f"Loading {args.corpus} statements from {corpus_path}")
    with open(corpus_path) as f:
        data = json.load(f)

    statements = data["statements"]
    print(f"  Total statements: {len(statements)}")

    # Filter by companies
    if args.companies:
        companies_lower = [c.lower() for c in args.companies]
        statements = [s for s in statements if s["company"].lower() in companies_lower]
        print(f"  After company filter: {len(statements)}")

    # Sample
    if args.sample:
        random.seed(args.seed)
        statements = random.sample(statements, min(args.sample, len(statements)))
        print(f"  Sampled: {len(statements)}")

    # Output path
    if args.output_suffix:
        output_path = OUTPUT_DIR / f"{args.corpus}_commitment_classifications_{args.output_suffix}.json"
    else:
        output_path = OUTPUT_DIR / f"{args.corpus}_commitment_classifications.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Resume support
    completed_ids = set()
    existing_results = []
    if args.resume and output_path.exists():
        with open(output_path) as f:
            existing = json.load(f)
        existing_results = existing.get("results", [])
        if args.retry_insufficient:
            dropped = [r for r in existing_results if r.get("consensus_type") == "insufficient_valid"]
            existing_results = [r for r in existing_results if r.get("consensus_type") != "insufficient_valid"]
            if dropped:
                print(f"  Retrying {len(dropped)} insufficient_valid statements")
        completed_ids = {r["statement_id"] for r in existing_results}
        print(f"  Resuming: {len(completed_ids)} already classified")

    remaining = [s for s in statements if s["statement_id"] not in completed_ids]
    print(f"  To classify: {len(remaining)}")

    if not remaining:
        print("Nothing to classify.")
        return

    # Load prompt
    template = load_prompt_template()
    prompt_hash = hashlib.md5(template.encode()).hexdigest()[:8]

    # Classify
    client = OpenRouterClient(api_key)
    results = list(existing_results)
    errors = 0
    save_interval = 50

    total_usage = {m: {"prompt_tokens": 0, "completion_tokens": 0} for m in models}
    started_at = datetime.now(timezone.utc).isoformat()

    import threading
    results_lock = threading.Lock()

    def _classify_one(idx_stmt):
        """Classify a single statement (for parallel execution)."""
        idx, stmt = idx_stmt
        return idx, classify_statement_three_models(
            client, stmt, models, template,
            max_workers=args.concurrency,
        )

    parallel = args.parallel
    if parallel > 1:
        # Sliding window: one executor over all statements, so a single slow
        # judge call delays only its own statement, not a whole batch.
        print(f"  Running {parallel} statements in parallel ({parallel * 3} concurrent API calls)")

        completed = 0
        with ThreadPoolExecutor(max_workers=parallel) as batch_executor:
            futures = {batch_executor.submit(_classify_one, item): item
                       for item in enumerate(remaining)}
            for future in as_completed(futures):
                idx, result = future.result()
                with results_lock:
                    results.append(result)

                    # Track usage
                    for jid in ["judge_1", "judge_2", "judge_3"]:
                        judge_result = result[jid]
                        model_name = judge_result.get("model", "")
                        usage = judge_result.get("usage", {})
                        if model_name in total_usage:
                            total_usage[model_name]["prompt_tokens"] += usage.get("prompt_tokens", 0)
                            total_usage[model_name]["completion_tokens"] += usage.get("completion_tokens", 0)

                    if not result["final_classification"]:
                        errors += 1

                    completed += 1
                    cls = result["final_classification"] or "SPLIT"
                    consensus = result["consensus_type"]
                    print(f"  [{completed}/{len(remaining)}] {result['company']}: {cls} ({consensus})", flush=True)

                    if completed % save_interval == 0:
                        _save_results(output_path, results, models, args.corpus, prompt_hash,
                                      started_at, total_usage)
    else:
        # Sequential mode (original behavior)
        for i, stmt in enumerate(remaining):
            result = classify_statement_three_models(
                client, stmt, models, template,
                max_workers=args.concurrency,
            )
            results.append(result)

            for jid in ["judge_1", "judge_2", "judge_3"]:
                judge_result = result[jid]
                model_name = judge_result.get("model", "")
                usage = judge_result.get("usage", {})
                if model_name in total_usage:
                    total_usage[model_name]["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    total_usage[model_name]["completion_tokens"] += usage.get("completion_tokens", 0)

            if not result["final_classification"]:
                errors += 1

            cls = result["final_classification"] or "SPLIT"
            consensus = result["consensus_type"]
            print(f"  [{i+1}/{len(remaining)}] {stmt['company']}: {cls} ({consensus})")

            if (i + 1) % save_interval == 0:
                _save_results(output_path, results, models, args.corpus, prompt_hash,
                             started_at, total_usage)

            if args.rate_limit > 0:
                time.sleep(args.rate_limit)

    # Final save
    _save_results(output_path, results, models, args.corpus, prompt_hash,
                 started_at, total_usage)

    # Summary
    metrics = compute_agreement_metrics(results)
    print(f"\n{'=' * 60}")
    print(f"CLASSIFICATION COMPLETE: {args.corpus.upper()}")
    print(f"{'=' * 60}")
    print(f"  Total classified: {len(results)}")
    print(f"  Errors/splits: {errors}")
    print(f"  Distribution: {metrics['classification_distribution']}")
    print(f"  Fleiss' kappa: {metrics['fleiss_kappa']}")
    print(f"  Unanimous: {metrics['unanimous_rate']:.1%}")
    print(f"  Majority: {metrics['majority_rate']:.1%}")
    print(f"  Split: {metrics['split_rate']:.1%}")
    print(f"  Output: {output_path}")


def _save_results(output_path, results, models, corpus, prompt_hash, started_at, total_usage):
    """Save current results to disk."""
    metrics = compute_agreement_metrics(results)

    output = {
        "metadata": {
            "methodology": "three_llm_judge_consensus",
            "classifier_version": "2.0",
            "models": models,
            "prompt_file": str(PROMPT_FILE),
            "prompt_hash": prompt_hash,
            "corpus": corpus.upper(),
            "started_at": started_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_classified": len(results),
            "total_usage": total_usage,
        },
        "agreement_metrics": metrics,
        "results": results,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
