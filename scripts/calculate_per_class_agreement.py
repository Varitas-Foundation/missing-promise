#!/usr/bin/env python3
"""
Calculate per-class unanimous agreement rates for LLM judge panel.
"""

import json
from pathlib import Path
from collections import defaultdict

def calculate_per_class_agreement(filepath, corpus_name):
    """Calculate unanimous agreement rates broken down by final classification."""
    with open(filepath, 'r') as f:
        data = json.load(f)

    # Overall metrics from metadata
    metadata = data['agreement_metrics']
    total_statements = metadata['total_statements']
    overall_unanimous = metadata['consensus_counts']['unanimous']
    overall_unanimous_rate = metadata['unanimous_rate']

    print(f"\n{'='*80}")
    print(f"CORPUS: {corpus_name}")
    print(f"{'='*80}")
    print(f"\nOVERALL AGREEMENT:")
    print(f"  Total statements: {total_statements:,}")
    print(f"  Unanimous: {overall_unanimous:,} ({overall_unanimous_rate:.2%})")
    print(f"  Majority: {metadata['consensus_counts']['majority']:,} ({metadata['majority_rate']:.2%})")
    print(f"  Split: {metadata['consensus_counts']['split']:,} ({metadata['split_rate']:.2%})")
    print(f"  Fleiss' Kappa: {metadata['fleiss_kappa']:.4f}")

    # Per-class breakdown
    class_counts = defaultdict(lambda: {'unanimous': 0, 'majority': 0, 'split': 0, 'total': 0})
    skipped_splits = 0

    for result in data['results']:
        final_class = result.get('final_classification')
        consensus = result['consensus_type']

        # Skip split decisions (no final classification, all 3 judges disagreed)
        if final_class is None:
            skipped_splits += 1
            continue

        class_counts[final_class]['total'] += 1
        class_counts[final_class][consensus] += 1

    # Calculate and display per-class rates
    print(f"\nPER-CLASS UNANIMOUS AGREEMENT RATES:")
    print(f"{'Class':<25} {'Total':>8} {'Unanimous':>10} {'Majority':>10} {'Split':>8} {'Unanimous %':>12}")
    print(f"{'-'*80}")

    for class_name in sorted(class_counts.keys()):
        counts = class_counts[class_name]
        total = counts['total']
        unanimous = counts['unanimous']
        majority = counts['majority']
        split = counts['split']
        unanimous_rate = unanimous / total if total > 0 else 0

        print(f"{class_name:<25} {total:>8,} {unanimous:>10,} {majority:>10,} {split:>8,} {unanimous_rate:>11.2%}")

    # Verification
    total_check = sum(c['total'] for c in class_counts.values())
    unanimous_check = sum(c['unanimous'] for c in class_counts.values())

    print(f"\n{'='*80}")
    print(f"VERIFICATION:")
    print(f"  Skipped splits (no final classification): {skipped_splits}")
    print(f"  Sum of per-class totals: {total_check:,} (should equal {total_statements - skipped_splits:,})")
    print(f"  Sum of per-class unanimous: {unanimous_check:,} (should equal {overall_unanimous:,})")
    print(f"  Match: {total_check == total_statements - skipped_splits and unanimous_check == overall_unanimous}")

    return class_counts

# Process both corpora
oppt_counts = calculate_per_class_agreement(
    Path(__file__).resolve().parents[1] / "data" / "oppt_commitment_classifications.json",
    'OPPT'
)

opp115_counts = calculate_per_class_agreement(
    Path(__file__).resolve().parents[1] / "data" / "opp115_commitment_classifications.json",
    'OPP-115'
)

print(f"\n{'='*80}")
print("SUMMARY COMPARISON")
print(f"{'='*80}")
print(f"\n{'Metric':<40} {'OPPT':>15} {'OPP-115':>15}")
print(f"{'-'*80}")

# Compare overall rates
print(f"{'Overall Unanimous Rate':<40} {0.8900:>14.2%} {0.8905:>14.2%}")

# Compare per-class rates
for class_name in ['COMPANY_COMMITMENT', 'PRACTICE', 'USER_CONTROL']:
    if class_name in oppt_counts and class_name in opp115_counts:
        oppt_rate = oppt_counts[class_name]['unanimous'] / oppt_counts[class_name]['total']
        opp115_rate = opp115_counts[class_name]['unanimous'] / opp115_counts[class_name]['total']
        print(f"{class_name + ' Unanimous Rate':<40} {oppt_rate:>14.2%} {opp115_rate:>14.2%}")

print()
