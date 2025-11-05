#!/usr/bin/env python3
"""
Comprehensive Comparison: Far Angle vs Near Angle Shot Detection

Compares synced camera angles:
- Far-Right ↔ Near-Left
- Far-Left ↔ Near-Right
"""

import json
import sys
from pathlib import Path
from typing import Dict, List


def load_accuracy_results(results_path: str) -> Dict:
    """Load accuracy analysis JSON"""
    accuracy_file = Path(results_path) / "accuracy_analysis.json"
    if not accuracy_file.exists():
        print(f"Error: {accuracy_file} not found")
        sys.exit(1)

    with open(accuracy_file, 'r') as f:
        return json.load(f)


def compare_angles(far_results: Dict, near_results: Dict, angle_name: str):
    """Compare far angle vs near angle results"""

    print("="*80)
    print(f"COMPREHENSIVE COMPARISON REPORT: {angle_name}")
    print("="*80)

    # Extract summaries
    far_summary = far_results['accuracy_analysis']
    near_summary = near_results['accuracy_analysis']

    far_detail = far_results['detailed_analysis']
    near_detail = near_results['detailed_analysis']

    print(f"\n{'='*80}")
    print("1. OVERALL ACCURACY COMPARISON")
    print(f"{'='*80}")

    metrics = [
        ("Total Detected Shots",
         far_summary['total_detected_shots'],
         near_summary['total_detected_shots']),
        ("Matched Correct",
         far_summary['matched_correct'],
         near_summary['matched_correct']),
        ("Matched Incorrect",
         far_summary['matched_incorrect'],
         near_summary['matched_incorrect']),
        ("False Positives (Missing from GT)",
         far_summary['missing_from_ground_truth'],
         near_summary['missing_from_ground_truth']),
        ("Outcome Accuracy %",
         far_summary['matched_shots_accuracy'],
         near_summary['matched_shots_accuracy']),
        ("Overall Accuracy %",
         far_summary['overall_accuracy_percentage'],
         near_summary['overall_accuracy_percentage']),
        ("Ground Truth Coverage %",
         far_summary['ground_truth_coverage'],
         near_summary['ground_truth_coverage']),
    ]

    print(f"\n{'Metric':<40} {'Far Angle':>15} {'Near Angle':>15} {'Diff':>10}")
    print("-" * 80)

    for metric_name, far_val, near_val in metrics:
        if isinstance(far_val, float):
            diff = far_val - near_val
            print(f"{metric_name:<40} {far_val:>15.2f} {near_val:>15.2f} {diff:>10.2f}")
        else:
            diff = far_val - near_val
            print(f"{metric_name:<40} {far_val:>15d} {near_val:>15d} {diff:>10d}")

    # Summary verdict
    print(f"\n{'='*80}")
    print("VERDICT:")
    print(f"{'='*80}")

    far_outcome_acc = far_summary['matched_shots_accuracy']
    near_outcome_acc = near_summary['matched_shots_accuracy']

    if far_outcome_acc > near_outcome_acc:
        print(f"✅ FAR ANGLE WINS: {far_outcome_acc:.1f}% vs {near_outcome_acc:.1f}% (+{far_outcome_acc - near_outcome_acc:.1f}%)")
    elif near_outcome_acc > far_outcome_acc:
        print(f"❌ NEAR ANGLE WINS: {near_outcome_acc:.1f}% vs {far_outcome_acc:.1f}% (+{near_outcome_acc - far_outcome_acc:.1f}%)")
    else:
        print(f"🤝 TIE: Both at {far_outcome_acc:.1f}%")

    # Compare incorrect classifications
    print(f"\n{'='*80}")
    print("2. INCORRECT CLASSIFICATIONS ANALYSIS")
    print(f"{'='*80}")

    far_incorrect = far_detail['matched_incorrect']
    near_incorrect = near_detail['matched_incorrect']

    print(f"\nFar Angle Incorrect: {len(far_incorrect)}")
    print(f"Near Angle Incorrect: {len(near_incorrect)}")

    # Build timestamp index for comparison
    far_incorrect_timestamps = {
        int(item['detected_timestamp_seconds']): item
        for item in far_incorrect
    }
    near_incorrect_timestamps = {
        int(item['detected_timestamp_seconds']): item
        for item in near_incorrect
    }

    # Find where one angle was correct but other was wrong
    all_timestamps = set(far_incorrect_timestamps.keys()) | set(near_incorrect_timestamps.keys())

    far_wins = []  # Far correct, near wrong
    near_wins = []  # Near correct, far wrong
    both_wrong = []  # Both wrong

    for ts in sorted(all_timestamps):
        far_wrong = ts in far_incorrect_timestamps
        near_wrong = ts in near_incorrect_timestamps

        if far_wrong and near_wrong:
            both_wrong.append((ts, far_incorrect_timestamps[ts], near_incorrect_timestamps[ts]))
        elif far_wrong and not near_wrong:
            near_wins.append((ts, far_incorrect_timestamps[ts]))
        elif not far_wrong and near_wrong:
            far_wins.append((ts, near_incorrect_timestamps[ts]))

    print(f"\n{'='*80}")
    print("3. HEAD-TO-HEAD COMPARISON")
    print(f"{'='*80}")

    print(f"\n✅ FAR ANGLE CORRECT, NEAR ANGLE WRONG: {len(far_wins)} cases")
    print(f"❌ NEAR ANGLE CORRECT, FAR ANGLE WRONG: {len(near_wins)} cases")
    print(f"❌ BOTH ANGLES WRONG: {len(both_wrong)} cases")

    # Detailed far angle wins
    if far_wins:
        print(f"\n{'='*80}")
        print("4. FAR ANGLE ADVANTAGES (Correct where Near failed)")
        print(f"{'='*80}")

        for i, (ts, near_item) in enumerate(far_wins[:10], 1):  # Show first 10
            print(f"\n{i}. Time: {ts}s")
            print(f"   Ground Truth: {near_item['ground_truth_outcome'].upper()}")
            print(f"   Near Detected: {near_item['detected_outcome'].upper()} ❌")
            print(f"   Far Angle: CORRECT ✅")
            print(f"   Near Reason: {near_item['detected_shot'].get('outcome_reason', 'N/A')}")

    # Detailed near angle wins
    if near_wins:
        print(f"\n{'='*80}")
        print("5. NEAR ANGLE ADVANTAGES (Correct where Far failed)")
        print(f"{'='*80}")

        for i, (ts, far_item) in enumerate(near_wins[:10], 1):  # Show first 10
            print(f"\n{i}. Time: {ts}s")
            print(f"   Ground Truth: {far_item['ground_truth_outcome'].upper()}")
            print(f"   Far Detected: {far_item['detected_outcome'].upper()} ❌")
            print(f"   Near Angle: CORRECT ✅")
            print(f"   Far Reason: {far_item['detected_shot'].get('outcome_reason', 'N/A')}")

    # Both wrong - opportunities for improvement
    if both_wrong:
        print(f"\n{'='*80}")
        print("6. BOTH ANGLES FAILED (Improvement Opportunities)")
        print(f"{'='*80}")

        for i, (ts, far_item, near_item) in enumerate(both_wrong[:5], 1):  # Show first 5
            print(f"\n{i}. Time: {ts}s")
            print(f"   Ground Truth: {far_item['ground_truth_outcome'].upper()}")
            print(f"   Far Detected: {far_item['detected_outcome'].upper()} ❌")
            print(f"   Near Detected: {near_item['detected_outcome'].upper()} ❌")
            print(f"   Far Reason: {far_item['detected_shot'].get('outcome_reason', 'N/A')}")
            print(f"   Near Reason: {near_item['detected_shot'].get('outcome_reason', 'N/A')}")

    # False positives comparison
    print(f"\n{'='*80}")
    print("7. FALSE POSITIVES COMPARISON")
    print(f"{'='*80}")

    far_fps = far_detail['missing_from_ground_truth']
    near_fps = near_detail['missing_from_ground_truth']

    print(f"\nFar Angle False Positives: {len(far_fps)}")
    print(f"Near Angle False Positives: {len(near_fps)}")

    if len(far_fps) < len(near_fps):
        print(f"✅ FAR ANGLE BETTER: {len(near_fps) - len(far_fps)} fewer false positives")
    elif len(near_fps) < len(far_fps):
        print(f"❌ NEAR ANGLE BETTER: {len(far_fps) - len(near_fps)} fewer false positives")

    # Final summary
    print(f"\n{'='*80}")
    print("8. FINAL SUMMARY")
    print(f"{'='*80}")

    print(f"\nFar Angle:")
    print(f"  - Matched Shot Accuracy: {far_summary['matched_shots_accuracy']:.1f}%")
    print(f"  - Overall Accuracy: {far_summary['overall_accuracy_percentage']:.1f}%")
    print(f"  - False Positives: {len(far_fps)}")
    print(f"  - Times Correct when Near Wrong: {len(far_wins)}")

    print(f"\nNear Angle:")
    print(f"  - Matched Shot Accuracy: {near_summary['matched_shots_accuracy']:.1f}%")
    print(f"  - Overall Accuracy: {near_summary['overall_accuracy_percentage']:.1f}%")
    print(f"  - False Positives: {len(near_fps)}")
    print(f"  - Times Correct when Far Wrong: {len(near_wins)}")

    print(f"\n{'='*80}")
    print("RECOMMENDATION:")
    print(f"{'='*80}")

    far_advantage = len(far_wins) - len(near_wins)

    if far_advantage > 5:
        print(f"✅ FAR ANGLE SIGNIFICANTLY BETTER (+{far_advantage} net advantage)")
        print("   Recommendation: Use Far Angle as primary detection")
    elif far_advantage > 0:
        print(f"✅ FAR ANGLE SLIGHTLY BETTER (+{far_advantage} net advantage)")
        print("   Recommendation: Use Far Angle, or dual-camera fusion")
    elif far_advantage < -5:
        print(f"❌ NEAR ANGLE SIGNIFICANTLY BETTER ({abs(far_advantage)} net advantage)")
        print("   Recommendation: Use Near Angle as primary detection")
    elif far_advantage < 0:
        print(f"❌ NEAR ANGLE SLIGHTLY BETTER ({abs(far_advantage)} net advantage)")
        print("   Recommendation: Use Near Angle, or dual-camera fusion")
    else:
        print("🤝 SIMILAR PERFORMANCE")
        print("   Recommendation: Dual-camera fusion for best results")

    print(f"\n{'='*80}\n")


def main():
    """Main entry point"""

    if len(sys.argv) < 3:
        print("Usage: python compare_angles.py <far_results_path> <near_results_path> [angle_name]")
        print("\nExample:")
        print("  python compare_angles.py \\")
        print("    results/game1-farright_311ee2cb-ebc6-4d9b-908a-2ebe001fc395 \\")
        print("    /Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_near_angle_shot_detection/results/09-23(1-NL)_fc2a92db-5a81-4f2a-acda-3e86b9098356 \\")
        print("    'Far-Right vs Near-Left'")
        sys.exit(1)

    far_results_path = sys.argv[1]
    near_results_path = sys.argv[2]
    angle_name = sys.argv[3] if len(sys.argv) > 3 else "Far Angle vs Near Angle"

    print("Loading results...")
    far_results = load_accuracy_results(far_results_path)
    near_results = load_accuracy_results(near_results_path)

    compare_angles(far_results, near_results, angle_name)


if __name__ == "__main__":
    main()
