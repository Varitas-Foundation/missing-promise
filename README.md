# The Missing Promise: Measuring Commitment Avoidance in Privacy Policies

Artifacts for the paper **"The Missing Promise: Measuring Commitment Avoidance in Privacy Policies"** (Thomas Brackin, 2026; arXiv ID pending).

This repository contains the three-class commitment classification pipeline, the raw per-statement classification outputs (including individual judge labels), the per-company practice-to-commitment ratio data, the validation reference set and its evaluation results, the supplementary sample of marker-free statements with its adjudicated labels, the separated-panel stability re-run and its comparison analysis, the no-name ablation of that panel, the inferential-statistics script behind every reported test, and the analysis code behind the paper's tables. Scripts resolve every path relative to the repository root; the repository is self-contained.

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
| `scripts/stability_comparison.py` | Compares the September 2026 separated-panel stability run against the primary run on every metric the paper reports: label distribution, per-company and per-category ratios, reference-set accuracy, Fleiss' kappa, the contradiction cross-reference, security-boundary composition, and inter-panel label churn. |
| `scripts/ablation_comparison.py` | Compares the no-name ablation (September 4, 2026: the separated panel re-run with the company slot set to "the company" and company names masked in statement text) against the named separated-panel run on the same metrics, producing `data/ablation_comparison_noname_20260904.json`. |
| `scripts/analyze_inferential.py` | Every inferential statistic the ratio and stability scripts do not produce: the elasticity regressions for both panels, length correlations, homogeneity and category-composition chi-square tests, exact binomial per-company tests in both directions, length-adjusted residuals, the permutation test, the Monte Carlo homogeneity check, Kruskal-Wallis sector tests, the rights-based reclassification, the boundary-sensitivity analysis, and the panel agreement statistics; `--json data/inferential_analysis.json` writes the released output. |
| `scripts/score_supplementary_sample.py` | Scores the 60-statement supplementary sample of marker-free statements against both panels and reproduces the pool-weighted precision, the implied commitment counts and proportions, and the reading-sensitivity bounds reported in the paper's validation section. |
| `scripts/audit_paper1_contradictions.py` | Re-classifies the commitment-side statements of the companion paper's panel-confirmed contradictions with the three-class panel, producing `data/paper1_contradiction_audit.json` (requires API access). |
| `data/*_commitment_classifications.json` | Raw per-statement classification outputs for both corpora, including each judge's individual label and reasoning. |
| `data/*_commitment_classifications_stability_20260901.json` | Raw per-statement outputs of the stability re-run (September 1, 2026): the identical statements classified with the byte-identical prompt by a fully separated judge panel (DeepSeek V4 Flash 0731, GLM-5.3-Flash, Kimi K3). |
| `data/stability_comparison_20260901.json` | Output of `scripts/stability_comparison.py`: the primary-versus-separated-panel comparison reported in the paper's stability section. Regenerated on September 5, 2026 after the second reference-set correction; only its reference-set evaluation blocks changed. |
| `data/*_commitment_classifications_noname_20260904.json` | Raw per-statement outputs of the no-name ablation (September 4, 2026); each record carries the masked text actually sent to the judges in `text_masked`. |
| `data/ablation_comparison_noname_20260904.json` | Output of `scripts/ablation_comparison.py`: the masked-versus-named comparison reported in the paper's stability section. |
| `data/company_name_forms.json` | The surface forms of each company's name observed in its own statements, including brand aliases for the conglomerates, used by `classify_commitments.py --mask-company`. |
| `data/inferential_analysis.json` | Output of `scripts/analyze_inferential.py`. |
| `data/opp115_policy_id_crosswalk.json` | Crosswalk between the OPP-115 corpus's numeric policy identifiers and the domain names the extracted statements use, derived from the policy identifier column of the public corpus's annotation files; recomputing the paper's polarity cross-tabulation requires it. |
| `data/supplementary_sample_60_blind.csv`, `data/supplementary_sample_60_key.json`, `data/supplementary_sample_60_labeling.md` | The supplementary reference sample of 60 marker-free statements drawn on September 4, 2026 (seed 20260904; 20 per stratum, 10 per corpus, at most two per company): the blind sheet, the key recording each statement's stratum and both panels' labels, and the labeling file containing the decision guide, the adjudicated labels, and a rationale per statement. Candidate labels were proposed by Claude Fable 5.1 without the panel labels or strata and approved without change by the author on September 5, 2026. The vocabulary filter that defined stratum C was not preserved. |
| `data/phase3_ratio_analysis.json` | Per-company practice-to-commitment ratios for both corpora. |
| `data/industry_analysis.json` | Per-sector ratio analysis. |
| `data/strategy_taxonomy.json` | Linguistic strategy taxonomy and per-class feature prevalence. |
| `data/gold_standard_200.json`, `data/gold_evaluation_results.json` | The 200-statement stratified reference set and the panel's evaluation against it. Six security-disclaimer statements ("cannot guarantee absolute security") were corrected from Company_Commitment to Practice on September 1, 2026, and one encryption statement ("a secure server that encrypts all user input information") was corrected from Practice to Company_Commitment on September 5, 2026; each file's metadata records both corrections (`corrections`; `gold_label_corrections` and `gold_label_corrections_20260905`) together with the pre-correction figures, and the reference file's summary block was recomputed from the current labels on September 5. |
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
python scripts/stability_comparison.py   # needs scipy
python scripts/ablation_comparison.py    # needs scipy
python scripts/analyze_inferential.py --json data/inferential_analysis.json   # needs scipy
python scripts/score_supplementary_sample.py
```

Re-running the classification itself requires an OpenRouter API key:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OpenRouter API key
python scripts/classify_commitments.py --corpus oppt
python scripts/classify_commitments.py --corpus opp115
```

The stability re-run uses the separated panel named by `JUDGE_MODEL_1/2/3` in `.env` and writes alongside, not over, the primary artifacts:

```bash
python scripts/classify_commitments.py --corpus oppt --judge-panel --output-suffix stability_20260901
python scripts/classify_commitments.py --corpus opp115 --judge-panel --output-suffix stability_20260901
```

The no-name ablation re-runs the separated panel with the company masked in both the prompt slot and the statement text (surface forms from `data/company_name_forms.json`):

```bash
python scripts/classify_commitments.py --corpus oppt --judge-panel --mask-company --output-suffix noname_20260904
python scripts/classify_commitments.py --corpus opp115 --judge-panel --mask-company --output-suffix noname_20260904
```

The judge panel comprises `anthropic/claude-haiku-4.5`, `openai/gpt-5-mini`, and `google/gemini-3-flash-preview`, accessed January–February 2026 via OpenRouter at temperature 0.0. Model versions may not remain available, and requests were not pinned to a specific backend provider; the released raw outputs enable verification without re-running the classification. The stability re-run (September 1, 2026) used `deepseek/deepseek-v4-flash-0731`, `z-ai/glm-5.3-flash`, and `moonshotai/kimi-k3`, also via OpenRouter at temperature 0.0, with a 4,096-token completion budget (the panel models emit reasoning tokens that count against it) and retries for empty or transiently failed responses; the prompt was unchanged. The no-name ablation (September 4, 2026) used the same separated panel and prompt template with the company slot set to "the company" and every observed surface form of the company's name replaced in the statement text.

## Interpreting the outputs

Per-company ratios are classifier outputs computed over publicly available policy documents; they are not allegations of legal violation, and a high ratio is not evidence of wrongdoing (the observed pattern is consistent with genre-wide drafting conventions). Reference labels for the validation set were assigned by a single annotator, so reported accuracy is agreement with one informed rater, not multi-annotator ground truth. The supplementary sample's labels were proposed by an LLM and approved without change by the same annotator; on the marker-free half of the commitment class it puts the primary panel's precision near 55%, which is the better guide to classifier error on the statements that most determine the ratio. See the paper's Limitations and Ethics sections.

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
