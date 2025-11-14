#!/usr/bin/env python3
"""
Detailed analysis of V6 error patterns
"""
import json
from collections import defaultdict

# Load V6 analysis summary
with open('V6_ANALYSIS_SUMMARY.json', 'r') as f:
    data = json.load(f)

all_errors = data['all_v6_errors']

print("=" * 100)
print("DETAILED V6 ERROR PATTERN ANALYSIS")
print("=" * 100)
print()
print(f"Total V6 Errors: {len(all_errors)}")
print()

# Categorize errors by type
error_categories = {
    'false_negatives': {
        'no_top_crossing': [],
        'incomplete_pass': [],
        'wrong_depth': [],
        'rim_bounce': []
    },
    'false_positives': {
        'complete_pass_through': [],
        'other': []
    }
}

for error in all_errors:
    gt = error['gt_outcome']
    pred = error['pred_outcome']
    reason = error['classification_reason']

    if gt == 'made' and pred == 'missed':
        # False Negative - Missed detecting a made shot
        if 'no_top_crossing' in reason:
            error_categories['false_negatives']['no_top_crossing'].append(error)
        elif 'incomplete_pass' in reason:
            error_categories['false_negatives']['incomplete_pass'].append(error)
        elif 'wrong_depth' in reason or 'wrong depth' in reason:
            error_categories['false_negatives']['wrong_depth'].append(error)
        elif 'rim_bounce' in reason:
            error_categories['false_negatives']['rim_bounce'].append(error)
    elif gt == 'missed' and pred == 'made':
        # False Positive - Incorrectly detected a missed shot as made
        if 'complete_pass_through' in reason:
            error_categories['false_positives']['complete_pass_through'].append(error)
        else:
            error_categories['false_positives']['other'].append(error)

# Calculate totals
total_fn = sum(len(errors) for errors in error_categories['false_negatives'].values())
total_fp = sum(len(errors) for errors in error_categories['false_positives'].values())

print("=" * 100)
print("ERROR BREAKDOWN")
print("=" * 100)
print()

print(f"FALSE NEGATIVES (GT=MADE, Predicted=MISSED): {total_fn} ({total_fn/len(all_errors)*100:.1f}%)")
print()
for category, errors in error_categories['false_negatives'].items():
    if errors:
        print(f"  {category.replace('_', ' ').title()}: {len(errors)} ({len(errors)/total_fn*100:.1f}% of FN)")
        for err in errors:
            print(f"    - {err['game']} @ {err['timestamp']}s: {err['classification_reason']}")
print()

print(f"FALSE POSITIVES (GT=MISSED, Predicted=MADE): {total_fp} ({total_fp/len(all_errors)*100:.1f}%)")
print()
for category, errors in error_categories['false_positives'].items():
    if errors:
        print(f"  {category.replace('_', ' ').title()}: {len(errors)} ({len(errors)/total_fp*100:.1f}% of FP)")
        for err in errors:
            print(f"    - {err['game']} @ {err['timestamp']}s: {err['classification_reason']}")
print()

print("=" * 100)
print("ROOT CAUSE ANALYSIS")
print("=" * 100)
print()

# Detailed root cause analysis
print("1️⃣  NO_TOP_CROSSING False Negatives ({} errors)".format(len(error_categories['false_negatives']['no_top_crossing'])))
print("   Issue: Ball never crossed the top hoop boundary in detected frames")
print("   Likely Causes:")
print("   - Ball trajectory starts INSIDE the hoop detection zone (already past top boundary)")
print("   - Very fast shots where ball passes through before detection begins")
print("   - Tracking lost before ball enters hoop zone")
print("   Potential Fix: Expand detection zone vertically to catch earlier trajectory")
print()

print("2️⃣  INCOMPLETE_PASS False Negatives ({} errors)".format(len(error_categories['false_negatives']['incomplete_pass'])))
print("   Issue: Ball entered from top but didn't cross bottom boundary")
print("   Likely Causes:")
print("   - Swish shots where ball passes through cleanly without triggering bottom crossing")
print("   - Bottom boundary crossing detection too strict")
print("   - Ball tracking lost after entering hoop")
print("   Potential Fix: Relax bottom crossing detection or use time-in-zone heuristic")
print()

print("3️⃣  WRONG_DEPTH False Negatives ({} errors)".format(len(error_categories['false_negatives']['wrong_depth'])))
print("   Issue: Size ratio exceeded MAX_BALL_HOOP_RATIO threshold")
print("   Size Ratios:")
for err in error_categories['false_negatives']['wrong_depth']:
    # Extract ratio from reason string
    reason = err['classification_reason']
    if 'ratio=' in reason:
        ratio = reason.split('ratio=')[1].split(')')[0]
        print(f"   - {err['game']} @ {err['timestamp']}s: ratio={ratio}")
print("   Likely Causes:")
print("   - Ball appears larger when farther from camera (perspective distortion)")
print("   - MAX_BALL_HOOP_RATIO=0.40 still too strict for some camera angles")
print("   Potential Fix: Increase MAX_BALL_HOOP_RATIO to 0.50 or use dynamic threshold")
print()

print("4️⃣  COMPLETE_PASS_THROUGH False Positives ({} errors)".format(len(error_categories['false_positives']['complete_pass_through'])))
print("   Issue: Ball passed through both boundaries but shot was missed")
print("   Size Ratios:")
for err in error_categories['false_positives']['complete_pass_through']:
    reason = err['classification_reason']
    if 'ratio=' in reason:
        ratio = reason.split('ratio=')[1].split(')')[0]
        print(f"   - {err['game']} @ {err['timestamp']}s: ratio={ratio}")
print("   Likely Causes:")
print("   - Rim-out shots that pass through but don't score (ball touched rim after exiting)")
print("   - Ball passed through hoop area but didn't actually go in basket")
print("   - Need additional validation beyond just boundary crossing")
print("   Potential Fix: Add rim contact detection or trajectory analysis after bottom crossing")
print()

print("5️⃣  RIM_BOUNCE False Negatives ({} error)".format(len(error_categories['false_negatives']['rim_bounce'])))
if error_categories['false_negatives']['rim_bounce']:
    for err in error_categories['false_negatives']['rim_bounce']:
        print(f"   - {err['game']} @ {err['timestamp']}s: {err['classification_reason']}")
    print("   Issue: Detected as rim bounce but was actually a made shot")
    print("   Likely Cause: In-and-out shot that eventually went in after bouncing")
    print("   Potential Fix: Increase rim bounce threshold or add multi-frame analysis")
print()

print("=" * 100)
print("V6 PERFORMANCE SUMMARY")
print("=" * 100)
print()

v6_perf = data['v6_performance']
v4_perf = data['v4_performance']
improvement = data['improvement']

print(f"V4 Performance: {v4_perf['average_accuracy']:.2f}% ({v4_perf['total_errors']} errors)")
print(f"V6 Performance: {v6_perf['average_accuracy']:.2f}% ({v6_perf['total_errors']} errors)")
print(f"Improvement: +{improvement['accuracy_gain']:.2f}%")
print(f"Error Reduction: {improvement['error_reduction']} errors ({improvement['error_reduction_percent']:.1f}%)")
print()

print("Game-by-Game:")
for game, details in v6_perf['game_details'].items():
    v4_details = v4_perf['game_details'][game]
    print(f"  {game}:")
    print(f"    V4: {v4_details['accuracy']:.2f}% ({v4_details['errors']} errors)")
    print(f"    V6: {details['accuracy']:.2f}% ({details['errors']} errors)")
    print(f"    Improvement: +{details['accuracy'] - v4_details['accuracy']:.2f}%")
print()

print("=" * 100)
print("NEXT STEPS FOR V7")
print("=" * 100)
print()
print("Based on error analysis, recommended V7 enhancements:")
print()
print("Priority 1: Fix 'no_top_crossing' False Negatives (10 errors)")
print("  - Expand vertical detection zone to catch earlier ball trajectory")
print("  - Start tracking before ball reaches hoop top boundary")
print()
print("Priority 2: Fix 'incomplete_pass' False Negatives (7 errors)")
print("  - Add swish detection: if ball enters from top and stays in zone >X frames → MADE")
print("  - Relax bottom crossing requirement for shots with high confidence")
print()
print("Priority 3: Fix 'complete_pass_through' False Positives (10 errors)")
print("  - Add post-exit trajectory analysis")
print("  - Detect if ball bounces out after passing through")
print()
print("Priority 4: Relax size ratio for remaining 'wrong_depth' errors (5 errors)")
print("  - Increase MAX_BALL_HOOP_RATIO from 0.40 to 0.50")
print()
print(f"Expected V7 Performance: ~91-93% accuracy (fix 22-27 of 35 errors)")
print()
