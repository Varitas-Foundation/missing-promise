# The Missing Promise: Measuring Commitment Avoidance in Privacy Policies

Artifacts for the paper **"The Missing Promise: Measuring Commitment Avoidance in Privacy Policies"** (Thomas Brackin, 2026; arXiv ID pending).

This repository contains the three-class commitment classification pipeline, the raw per-statement classification outputs (including individual judge labels), the per-company practice-to-commitment ratio data, the validation reference set and its evaluation results, and the analysis code behind the paper's tables. Scripts resolve every path relative to the repository root; the repository is self-contained.

## Repository layout

| Path | Contents |
|------|----------|
| `scripts/classify_commitments.py` | Three-LLM judge panel that classifies each statement as Company_Commitment, Practice, or User_Control. |
| `scripts/classify_commitment_prompt.md` | The full classification prompt, unmodified from the runs (reproduced in the paper's appendix). |
| `scripts/analyze_ratios.py` | Practice-to-commitment ratio analysis, including the contradiction-status comparison against the companion paper's results. |
| `scripts/classify_industries.py` | Industry sector assignment and per-sector ratio analysis. |
| `scripts/extract_strategies.py` | Rule-based linguistic feature extraction (regex patterns grounded in speech act theory) and strategy taxonomy analysis. |
| `scripts/commitment_classifier.py` | The rule-based classifier prototype described in the paper's classifier section; the final labels come exclusively from the LLM panel. |
| `scripts/calculate_per_class_agreement.py` | Per-class judge agreement rates reported in the validation section. |
| `data/*_commitment_classifications.json` | Raw per-statement classification outputs for both corpora, including each judge's individual label and reasoning. |
| `data/phase3_ratio_analysis.json` | Per-company practice-to-commitment ratios for both corpora. |
| `data/industry_analysis.json` | Per-sector ratio analysis. |
| `data/strategy_taxonomy.json` | Linguistic strategy taxonomy and per-class feature prevalence. |
| `data/gold_standard_200.json`, `data/gold_evaluation_results.json` | The 200-statement stratified reference set and the panel's evaluation against it. |
| `data/paper1_contradiction_audit.json` | The commitment reclassification audit of the companion paper's confirmed contradictions, used for the contradiction-status comparison. |
| `data/companies.json` | The list of companies in both corpora (123 OPPT, 115 OPP-115). |
| `data/inputs/` | The classified statements' source files: byte-identical copies of `statements.json` and `statement_judge_results.json` from the companion paper's primary runs. |

## Relationship to the companion paper

Statement extraction is not performed in this repository. The input statements in `data/inputs/` were extracted by the pipeline of the companion paper, "Privacy Washing: Detecting Internal Contradictions in Privacy Policies," whose artifacts are released at [Varitas-Foundation/privacy-washing](https://github.com/Varitas-Foundation/privacy-washing); the files here are byte-identical copies from its `oppt_experiment_enhanced_20260131/` and `opp115_experiment_annotation_guided_20260203/` run directories. Readers requiring full methodological detail for the extraction step should consult that paper and repository.

## Reproducing

The analysis stages are deterministic and require no API access:

```bash
python scripts/analyze_ratios.py
python scripts/classify_industries.py
python scripts/extract_strategies.py
python scripts/calculate_per_class_agreement.py
```

Re-running the classification itself requires an OpenRouter API key:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OpenRouter API key
python scripts/classify_commitments.py --corpus oppt
python scripts/classify_commitments.py --corpus opp115
```

The judge panel comprises `anthropic/claude-haiku-4.5`, `openai/gpt-5-mini`, and `google/gemini-3-flash-preview`, accessed January–February 2026 via OpenRouter at temperature 0.0. Model versions may not remain available, and requests were not pinned to a specific backend provider; the released raw outputs enable verification without re-running the classification.

## Interpreting the outputs

Per-company ratios are classifier outputs computed over publicly available policy documents; they are not allegations of legal violation, and a high ratio is not evidence of wrongdoing (the observed pattern is consistent with genre-wide drafting conventions). Reference labels for the validation set were assigned by a single annotator, so reported accuracy is agreement with one informed rater, not multi-annotator ground truth. See the paper's Limitations and Ethics sections.

## Licensing

- Code and scripts: MIT (see `LICENSE`).
- Classification outputs and derived data: CC-BY-4.0.
- The underlying policy texts come from the OPPT corpus (CC-BY-4.0, [Hugging Face](https://huggingface.co/datasets/OpenPrivacyPolicyTaxonomy/oppt-privacy-policies)) and the OPP-115 corpus (obtain from its [original source](https://usableprivacy.org/data)).

## Citation

```bibtex
@article{brackin2026missingpromise,
  title={The Missing Promise: Measuring Commitment Avoidance in Privacy Policies},
  author={Brackin, Thomas},
  year={2026},
  note={arXiv preprint, ID pending}
}
```
