#!/usr/bin/env python3
"""
Analyze near angle detection errors to identify patterns for fusion strategy.
Extracts false negatives and false positives with their characteristics.
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_errors(accuracy_file_path):
    """Analyze errors from near angle accuracy analysis."""

    with open(accuracy_file_path, 'r') as f:
        data = json.load(f)

    # Extract summary statistics
    summary = data.get('summary', {})
    print(f"\n{'='*80}")
    print(f"File: {Path(accuracy_file_path).parent.name}")
    print(f"{'='*80}")
    print(f"Total shots: {summary.get('total_ground_truth_shots', 0)}")
    print(f"Accuracy: {summary.get('overall_accuracy', 0)*100:.1f}%")
    print(f"False Negatives (Made→Missed): {summary.get('false_negatives', 0)}")
    print(f"False Positives (Missed→Made): {summary.get('false_positives', 0)}")
    print(f"Not Detected: {summary.get('not_detected', 0)}")

    # Extract error patterns
    false_negatives = []
    false_positives = []

    matched_shots = data.get('matched_shots', [])

    for shot in matched_shots:
        gt_outcome = shot.get('ground_truth', {}).get('shot_outcome')
        detected_outcome = shot.get('detected', {}).get('outcome')

        # False Negative: Made → Missed
        if gt_outcome == 'made' and detected_outcome == 'missed':
            false_negatives.append({
                'timestamp': shot.get('ground_truth', {}).get('time_in_seconds'),
                'type': shot.get('ground_truth', {}).get('type'),
                'reason': shot.get('detected', {}).get('reason', 'unknown'),
                'confidence': shot.get('detected', {}).get('confidence', 0),
                'trajectory_score': shot.get('detected', {}).get('trajectory_score', 0),
                'characteristics': {
                    'line_crossings': shot.get('detected', {}).get('line_crossings', 0),
                    'points_inside': shot.get('detected', {}).get('points_inside_pct', 0),
                    'vertical_movement': shot.get('detected', {}).get('downward_movement', 0),
                }
            })

        # False Positive: Missed → Made
        elif gt_outcome == 'missed' and detected_outcome == 'made':
            false_positives.append({
                'timestamp': shot.get('ground_truth', {}).get('time_in_seconds'),
                'type': shot.get('ground_truth', {}).get('type'),
                'reason': shot.get('detected', {}).get('reason', 'unknown'),
                'confidence': shot.get('detected', {}).get('confidence', 0),
                'trajectory_score': shot.get('detected', {}).get('trajectory_score', 0),
                'characteristics': {
                    'line_crossings': shot.get('detected', {}).get('line_crossings', 0),
                    'points_inside': shot.get('detected', {}).get('points_inside_pct', 0),
                    'vertical_movement': shot.get('detected', {}).get('downward_movement', 0),
                }
            })

    # Analyze False Negatives
    print(f"\n{'='*80}")
    print(f"FALSE NEGATIVES ANALYSIS (Made → Missed): {len(false_negatives)}")
    print(f"{'='*80}")

    # Group by reason
    fn_reasons = defaultdict(list)
    for fn in false_negatives:
        fn_reasons[fn['reason']].append(fn)

    print("\nBy Reason:")
    for reason, shots in sorted(fn_reasons.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {reason}: {len(shots)} shots")
        avg_conf = sum(s['confidence'] for s in shots) / len(shots) if shots else 0
        avg_traj = sum(s['trajectory_score'] for s in shots) / len(shots) if shots else 0
        print(f"    Avg confidence: {avg_conf:.3f}, Avg trajectory score: {avg_traj:.3f}")

        # Show a few examples
        for shot in shots[:3]:
            print(f"      {shot['timestamp']:.1f}s ({shot['type']}): conf={shot['confidence']:.3f}, "
                  f"crossings={shot['characteristics']['line_crossings']}, "
                  f"inside={shot['characteristics']['points_inside']:.1%}")

    # Group by shot type
    fn_by_type = defaultdict(list)
    for fn in false_negatives:
        fn_by_type[fn['type']].append(fn)

    print("\nBy Shot Type:")
    for shot_type, shots in sorted(fn_by_type.items(), key=lambda x: len(x[1]), reverse=True):
        avg_conf = sum(s['confidence'] for s in shots) / len(shots) if shots else 0
        print(f"  {shot_type}: {len(shots)} shots (avg conf: {avg_conf:.3f})")

    # Analyze False Positives
    print(f"\n{'='*80}")
    print(f"FALSE POSITIVES ANALYSIS (Missed → Made): {len(false_positives)}")
    print(f"{'='*80}")

    # Group by reason
    fp_reasons = defaultdict(list)
    for fp in false_positives:
        fp_reasons[fp['reason']].append(fp)

    print("\nBy Reason:")
    for reason, shots in sorted(fp_reasons.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {reason}: {len(shots)} shots")
        avg_conf = sum(s['confidence'] for s in shots) / len(shots) if shots else 0
        avg_traj = sum(s['trajectory_score'] for s in shots) / len(shots) if shots else 0
        print(f"    Avg confidence: {avg_conf:.3f}, Avg trajectory score: {avg_traj:.3f}")

        # Show a few examples
        for shot in shots[:3]:
            print(f"      {shot['timestamp']:.1f}s ({shot['type']}): conf={shot['confidence']:.3f}, "
                  f"crossings={shot['characteristics']['line_crossings']}, "
                  f"inside={shot['characteristics']['points_inside']:.1%}")

    # Group by shot type
    fp_by_type = defaultdict(list)
    for fp in false_positives:
        fp_by_type[fp['type']].append(fp)

    print("\nBy Shot Type:")
    for shot_type, shots in sorted(fp_by_type.items(), key=lambda x: len(x[1]), reverse=True):
        avg_conf = sum(s['confidence'] for s in shots) / len(shots) if shots else 0
        print(f"  {shot_type}: {len(shots)} shots (avg conf: {avg_conf:.3f})")

    return {
        'false_negatives': false_negatives,
        'false_positives': false_positives,
        'summary': summary
    }

if __name__ == "__main__":
    # Paths to near angle results
    results_dir = Path("/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_near_angle_shot_detection/results")

    games = [
        "09-22(3-NL)_d2a451bb-c5c5-4b20-87bd-3e073fabf277",
        "09-23(1-NL)_fc2a92db-5a81-4f2a-acda-3e86b9098356"
    ]

    all_results = {}

    for game in games:
        accuracy_file = results_dir / game / "accuracy_analysis.json"
        if accuracy_file.exists():
            all_results[game] = analyze_errors(accuracy_file)
        else:
            print(f"File not found: {accuracy_file}")

    # Combined analysis
    print(f"\n{'='*80}")
    print("COMBINED ANALYSIS ACROSS BOTH GAMES")
    print(f"{'='*80}")

    all_fn = []
    all_fp = []

    for game, results in all_results.items():
        all_fn.extend(results['false_negatives'])
        all_fp.extend(results['false_positives'])

    print(f"\nTotal False Negatives: {len(all_fn)}")
    print(f"Total False Positives: {len(all_fp)}")

    # Combined reason analysis for FN
    fn_reasons = defaultdict(list)
    for fn in all_fn:
        fn_reasons[fn['reason']].append(fn)

    print("\nFalse Negatives by Reason (Combined):")
    for reason, shots in sorted(fn_reasons.items(), key=lambda x: len(x[1]), reverse=True):
        avg_conf = sum(s['confidence'] for s in shots) / len(shots) if shots else 0
        print(f"  {reason}: {len(shots)} shots (avg conf: {avg_conf:.3f})")

    # Combined reason analysis for FP
    fp_reasons = defaultdict(list)
    for fp in all_fp:
        fp_reasons[fp['reason']].append(fp)

    print("\nFalse Positives by Reason (Combined):")
    for reason, shots in sorted(fp_reasons.items(), key=lambda x: len(x[1]), reverse=True):
        avg_conf = sum(s['confidence'] for s in shots) / len(shots) if shots else 0
        print(f"  {reason}: {len(shots)} shots (avg conf: {avg_conf:.3f})")

    # Identify low confidence errors (candidates for far angle override)
    print(f"\n{'='*80}")
    print("LOW CONFIDENCE ERRORS (Candidates for Far Angle Override)")
    print(f"{'='*80}")

    low_conf_fn = [fn for fn in all_fn if fn['confidence'] < 0.7]
    low_conf_fp = [fp for fp in all_fp if fp['confidence'] < 0.7]

    print(f"\nFalse Negatives with confidence < 0.7: {len(low_conf_fn)}/{len(all_fn)} ({len(low_conf_fn)/len(all_fn)*100:.1f}%)")
    for fn in low_conf_fn:
        print(f"  {fn['timestamp']:.1f}s ({fn['type']}): {fn['reason']} (conf={fn['confidence']:.3f})")

    print(f"\nFalse Positives with confidence < 0.7: {len(low_conf_fp)}/{len(all_fp)} ({len(low_conf_fp)/len(all_fp)*100:.1f}%)")
    for fp in low_conf_fp:
        print(f"  {fp['timestamp']:.1f}s ({fp['type']}): {fp['reason']} (conf={fp['confidence']:.3f})")

    # Save results for fusion strategy
    output = {
        'games_analyzed': games,
        'combined_stats': {
            'total_false_negatives': len(all_fn),
            'total_false_positives': len(all_fp),
            'low_confidence_fn': len(low_conf_fn),
            'low_confidence_fp': len(low_conf_fp)
        },
        'false_negative_reasons': {reason: len(shots) for reason, shots in fn_reasons.items()},
        'false_positive_reasons': {reason: len(shots) for reason, shots in fp_reasons.items()},
        'low_confidence_errors': {
            'false_negatives': low_conf_fn,
            'false_positives': low_conf_fp
        }
    }

    output_file = Path("near_angle_error_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
