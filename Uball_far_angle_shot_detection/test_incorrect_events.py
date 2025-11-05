#!/usr/bin/env python3
"""
Test how many previously INCORRECT events can be fixed with new logic
"""

import json
from pathlib import Path

def test_incorrect_events():
    """Test new logic on previously incorrect classifications"""

    # Load previous incorrect results
    old_results_path = "results/game1-farright_311ee2cb-ebc6-4d9b-908a-2ebe001fc395/accuracy_analysis.json"
    old_results = json.load(open(old_results_path))

    old_incorrect = old_results['detailed_analysis']['matched_incorrect']

    print("="*80)
    print("TESTING NEW LOGIC ON PREVIOUSLY INCORRECT EVENTS")
    print("="*80)
    print(f"\nTotal previously incorrect: {len(old_incorrect)}")

    # Categorize by type
    false_made = []  # Detected MADE, actually MISSED
    false_missed = []  # Detected MISSED, actually MADE

    for item in old_incorrect:
        detected = item['detected_outcome']
        actual = item['ground_truth_outcome']

        if detected == 'made' and actual == 'missed':
            false_made.append(item)
        elif detected == 'missed' and actual == 'made':
            false_missed.append(item)

    print(f"\nFalse MADE (detected made, actually missed): {len(false_made)}")
    print(f"False MISSED (detected missed, actually made): {len(false_missed)}")

    # Analyze false made - should be caught by new rim bounce logic
    print(f"\n{'='*80}")
    print("1. FALSE MADE SHOTS (Should now be caught as rim bounces)")
    print(f"{'='*80}")

    potentially_fixed_false_made = 0

    for i, item in enumerate(false_made, 1):
        shot = item['detected_shot']
        ts = item['detected_timestamp_seconds']
        frames = shot['frames_in_zone']
        upward = shot['upward_movement']
        downward = shot['downward_movement']
        consistency = shot['trajectory_consistency']
        reason = shot['outcome_reason']

        # Check if new logic would catch it
        would_catch = False
        new_reason = ""

        # Rule 1: Rim bounce by frames + upward
        if frames >= 20 and upward >= 35:
            would_catch = True
            new_reason = f"rim_bounce_frames ({frames}f, {upward:.0f}px up)"

        # Rule 2: Rim bounce by ratio
        elif downward > 0 and upward / downward > 1.2:
            would_catch = True
            new_reason = f"rim_bounce_ratio (ratio:{upward/downward:.2f})"

        # Rule 3: Raised consistency threshold (0.55 -> 0.60)
        elif consistency < 0.60:
            would_catch = True
            new_reason = f"low_consistency ({consistency:.2f} < 0.60)"

        if would_catch:
            potentially_fixed_false_made += 1

        status = "✅ FIXED" if would_catch else "❌ STILL WRONG"

        print(f"\n{i}. Time: {ts:.0f}s - {status}")
        print(f"   Ground Truth: MISSED")
        print(f"   Old: Detected MADE - {reason}")
        if would_catch:
            print(f"   New: Would detect MISSED - {new_reason}")
        print(f"   Metrics: {frames}f, {upward:.0f}px up, {downward:.0f}px down, cons:{consistency:.2f}")

    # Analyze false missed
    print(f"\n{'='*80}")
    print("2. FALSE MISSED SHOTS (May still be issues)")
    print(f"{'='*80}")

    potentially_fixed_false_missed = 0

    for i, item in enumerate(false_missed, 1):
        shot = item['detected_shot']
        ts = item['detected_timestamp_seconds']
        frames = shot['frames_in_zone']
        upward = shot['upward_movement']
        downward = shot['downward_movement']
        consistency = shot['trajectory_consistency']
        reason = shot['outcome_reason']

        # Check if new logic would catch it
        would_catch = False
        new_reason = ""

        # Swish detection (up <= 20, cons >= 0.85)
        if upward <= 20 and consistency >= 0.85:
            would_catch = True
            new_reason = f"clean_swish ({upward:.0f}px up, {consistency:.2f} cons)"

        # General made (cons >= 0.60)
        elif consistency >= 0.60 and downward >= 60:
            would_catch = True
            new_reason = f"made_shot (cons:{consistency:.2f})"

        if would_catch:
            potentially_fixed_false_missed += 1

        status = "✅ FIXED" if would_catch else "❌ STILL WRONG"

        print(f"\n{i}. Time: {ts:.0f}s - {status}")
        print(f"   Ground Truth: MADE")
        print(f"   Old: Detected MISSED - {reason}")
        if would_catch:
            print(f"   New: Would detect MADE - {new_reason}")
        print(f"   Metrics: {frames}f, {upward:.0f}px up, {downward:.0f}px down, cons:{consistency:.2f}")

    # Summary
    print(f"\n{'='*80}")
    print("IMPROVEMENT POTENTIAL")
    print(f"{'='*80}")

    total_potentially_fixed = potentially_fixed_false_made + potentially_fixed_false_missed

    print(f"\nPreviously Incorrect: {len(old_incorrect)}")
    print(f"  - False MADE: {len(false_made)}")
    print(f"  - False MISSED: {len(false_missed)}")

    print(f"\nPotentially Fixed with New Logic: {total_potentially_fixed}")
    print(f"  - False MADE fixed: {potentially_fixed_false_made}/{len(false_made)}")
    print(f"  - False MISSED fixed: {potentially_fixed_false_missed}/{len(false_missed)}")

    print(f"\nStill Incorrect: {len(old_incorrect) - total_potentially_fixed}")

    # Calculate new expected accuracy
    old_correct = 45
    old_incorrect_count = 30
    old_total_matched = 75

    new_correct = old_correct + total_potentially_fixed
    new_incorrect = old_incorrect_count - total_potentially_fixed

    old_accuracy = (old_correct / old_total_matched) * 100
    new_accuracy = (new_correct / old_total_matched) * 100

    print(f"\n{'='*80}")
    print("EXPECTED ACCURACY IMPROVEMENT")
    print(f"{'='*80}")

    print(f"\nOld Matched Shot Accuracy: {old_accuracy:.1f}% ({old_correct}/{old_total_matched})")
    print(f"New Matched Shot Accuracy: {new_accuracy:.1f}% ({new_correct}/{old_total_matched})")
    print(f"Improvement: +{new_accuracy - old_accuracy:.1f}%")

    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    test_incorrect_events()
