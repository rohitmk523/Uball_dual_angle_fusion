#!/usr/bin/env python3
"""
Analyze V6 results and compare with V4 performance
"""
import json
from pathlib import Path
from collections import defaultdict

# V6 result directories
v6_results = {
    'Game 1': 'results/09-23(1-FR)_95863664-57d3-4f32-b270-e26069951eca',
    'Game 2': 'results/09-23(2-FR)_297966ab-8efc-4176-9854-74b0b417613b',
    'Game 3': 'results/09-23(3-FR)_1baf5973-e962-4bf2-a67e-f597aed8d8d3'
}

# V4 results for comparison
v4_results = {
    'Game 1': 'results/09-23(1-FR)_92969477-ee1f-44d5-869f-034e33c46f14',
    'Game 2': 'results/09-23(2-FR)_29017563-c908-4dac-b140-6a7137f2b0af',
    'Game 3': 'results/09-23(3-FR)_dc1c2e0f-ee5f-42f8-969d-6a3fac1e62cc'
}

def extract_accuracy_metrics(result_dir):
    """Extract key accuracy metrics from accuracy_analysis.json"""
    accuracy_file = Path(result_dir) / 'accuracy_analysis.json'

    with open(accuracy_file, 'r') as f:
        data = json.load(f)

    # Get accuracy metrics
    accuracy_data = data.get('accuracy_analysis', {})
    matched_accuracy = accuracy_data.get('matched_shots_accuracy', 0)
    matched_correct = accuracy_data.get('matched_correct', 0)
    matched_incorrect = accuracy_data.get('matched_incorrect', 0)
    total_matched = matched_correct + matched_incorrect

    # Extract incorrect matches
    incorrect_matches = []
    for match in data.get('detailed_analysis', {}).get('matched_incorrect', []):
        detected_shot = match.get('detected_shot', {})
        gt_shot = match.get('ground_truth_shot', {})

        incorrect_matches.append({
            'timestamp': match.get('detected_timestamp_seconds', detected_shot.get('timestamp_seconds')),
            'gt_outcome': match.get('ground_truth_outcome', gt_shot.get('outcome')),
            'pred_outcome': match.get('detected_outcome', detected_shot.get('outcome')),
            'classification_reason': detected_shot.get('outcome_reason', 'N/A')
        })

    return {
        'accuracy': matched_accuracy,
        'correct': matched_correct,
        'total': total_matched,
        'incorrect_count': len(incorrect_matches),
        'incorrect_matches': incorrect_matches
    }

def analyze_error_patterns(incorrect_matches):
    """Analyze patterns in incorrect matches"""
    error_types = defaultdict(int)

    for error in incorrect_matches:
        reason = error['classification_reason']

        # Categorize errors
        if 'size_ratio' in reason or 'ratio' in reason:
            error_types['size_ratio_failed'] += 1
        elif 'incomplete_pass' in reason:
            error_types['incomplete_pass'] += 1
        elif 'rim_bounce' in reason:
            error_types['rim_bounce'] += 1
        elif 'complete_pass_through' in reason:
            error_types['missed_complete_pass'] += 1
        elif 'no_line_cross' in reason or 'no_intersection' in reason:
            error_types['no_intersection'] += 1
        else:
            error_types['other'] += 1

    return dict(error_types)

print("=" * 80)
print("V6 RESULTS ANALYSIS")
print("=" * 80)
print()

# Analyze V6 results
v6_metrics = {}
all_v6_incorrect = []

for game_name, result_dir in v6_results.items():
    metrics = extract_accuracy_metrics(result_dir)
    v6_metrics[game_name] = metrics
    all_v6_incorrect.extend([(game_name, err) for err in metrics['incorrect_matches']])

    print(f"📊 {game_name} V6 Results:")
    print(f"   Accuracy: {metrics['accuracy']:.2f}%")
    print(f"   Correct: {metrics['correct']}/{metrics['total']}")
    print(f"   Errors: {metrics['incorrect_count']}")
    print()

# Calculate V6 average
v6_total_correct = sum(m['correct'] for m in v6_metrics.values())
v6_total = sum(m['total'] for m in v6_metrics.values())
v6_avg_accuracy = (v6_total_correct / v6_total * 100) if v6_total > 0 else 0
v6_total_errors = sum(m['incorrect_count'] for m in v6_metrics.values())

print(f"📈 V6 OVERALL PERFORMANCE:")
print(f"   Average Accuracy: {v6_avg_accuracy:.2f}%")
print(f"   Total Correct: {v6_total_correct}/{v6_total}")
print(f"   Total Errors: {v6_total_errors}")
print()

print("=" * 80)
print("V4 vs V6 COMPARISON")
print("=" * 80)
print()

# Compare with V4
v4_metrics = {}
for game_name, result_dir in v4_results.items():
    metrics = extract_accuracy_metrics(result_dir)
    v4_metrics[game_name] = metrics

v4_total_correct = sum(m['correct'] for m in v4_metrics.values())
v4_total = sum(m['total'] for m in v4_metrics.values())
v4_avg_accuracy = (v4_total_correct / v4_total * 100) if v4_total > 0 else 0
v4_total_errors = sum(m['incorrect_count'] for m in v4_metrics.values())

print(f"V4 Average: {v4_avg_accuracy:.2f}% ({v4_total_errors} errors)")
print(f"V6 Average: {v6_avg_accuracy:.2f}% ({v6_total_errors} errors)")
print(f"Improvement: {v6_avg_accuracy - v4_avg_accuracy:+.2f}%")
if v4_total_errors > 0:
    print(f"Error Reduction: {v4_total_errors - v6_total_errors} ({(v4_total_errors - v6_total_errors)/v4_total_errors*100:.1f}%)")
else:
    print(f"Error Reduction: {v4_total_errors - v6_total_errors}")
print()

print("Game-by-Game Comparison:")
for game_name in v6_results.keys():
    v4_acc = v4_metrics[game_name]['accuracy']
    v6_acc = v6_metrics[game_name]['accuracy']
    v4_err = v4_metrics[game_name]['incorrect_count']
    v6_err = v6_metrics[game_name]['incorrect_count']

    print(f"  {game_name}:")
    print(f"    V4: {v4_acc:.2f}% ({v4_err} errors)")
    print(f"    V6: {v6_acc:.2f}% ({v6_err} errors)")
    print(f"    Change: {v6_acc - v4_acc:+.2f}% ({v4_err - v6_err:+d} errors)")
print()

print("=" * 80)
print("V6 ERROR PATTERN ANALYSIS")
print("=" * 80)
print()

# Analyze error patterns in V6
all_v6_error_reasons = [err['classification_reason'] for _, err in all_v6_incorrect]
v6_error_patterns = analyze_error_patterns([err for _, err in all_v6_incorrect])

print(f"Total V6 Errors: {v6_total_errors}")
print()
print("Error Categories:")
for category, count in sorted(v6_error_patterns.items(), key=lambda x: -x[1]):
    percentage = (count / v6_total_errors * 100) if v6_total_errors > 0 else 0
    print(f"  {category}: {count} ({percentage:.1f}%)")
print()

print("=" * 80)
print("V6 INCORRECT MATCHES DETAILS")
print("=" * 80)
print()

for game_name, error in all_v6_incorrect[:50]:  # Show first 50 errors
    print(f"Game: {game_name}")
    print(f"  Timestamp: {error['timestamp']}")
    print(f"  Ground Truth: {error['gt_outcome']} | Predicted: {error['pred_outcome']}")
    print(f"  Reason: {error['classification_reason']}")
    print()

if len(all_v6_incorrect) > 50:
    print(f"... and {len(all_v6_incorrect) - 50} more errors")
    print()

# Save summary to file
summary_output = {
    'v4_performance': {
        'average_accuracy': v4_avg_accuracy,
        'total_errors': v4_total_errors,
        'game_details': {name: {'accuracy': m['accuracy'], 'errors': m['incorrect_count']}
                         for name, m in v4_metrics.items()}
    },
    'v6_performance': {
        'average_accuracy': v6_avg_accuracy,
        'total_errors': v6_total_errors,
        'game_details': {name: {'accuracy': m['accuracy'], 'errors': m['incorrect_count']}
                         for name, m in v6_metrics.items()}
    },
    'improvement': {
        'accuracy_gain': v6_avg_accuracy - v4_avg_accuracy,
        'error_reduction': v4_total_errors - v6_total_errors,
        'error_reduction_percent': (v4_total_errors - v6_total_errors)/v4_total_errors*100 if v4_total_errors > 0 else 0
    },
    'v6_error_patterns': v6_error_patterns,
    'all_v6_errors': [{'game': game, **error} for game, error in all_v6_incorrect]
}

with open('V6_ANALYSIS_SUMMARY.json', 'w') as f:
    json.dump(summary_output, f, indent=2)

print("=" * 80)
print(f"✅ Summary saved to: V6_ANALYSIS_SUMMARY.json")
print("=" * 80)
