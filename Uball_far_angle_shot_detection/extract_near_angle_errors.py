#!/usr/bin/env python3
"""
Extract near angle errors for fusion strategy planning.
Focus on identifying error patterns and low confidence classifications.
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_near_angle_errors(accuracy_file):
    """Analyze errors from near angle results."""

    with open(accuracy_file, 'r') as f:
        data = json.load(f)

    game_name = Path(accuracy_file).parent.name

    # Extract summary
    acc_summary = data['accuracy_analysis']
    print(f"\n{'='*80}")
    print(f"NEAR ANGLE ANALYSIS: {game_name}")
    print(f"{'='*80}")
    print(f"Total detected shots: {acc_summary['total_detected_shots']}")
    print(f"Matched correct: {acc_summary['matched_correct']}")
    print(f"Matched incorrect: {acc_summary['matched_incorrect']}")
    print(f"Overall accuracy: {acc_summary['overall_accuracy_percentage']:.1f}%")
    print(f"Ground truth coverage: {acc_summary['ground_truth_coverage']:.1f}%")

    # Extract errors
    incorrect_shots = data['detailed_analysis']['matched_incorrect']

    false_negatives = []  # Made -> Missed
    false_positives = []  # Missed -> Made

    for shot in incorrect_shots:
        gt_outcome = shot['ground_truth_shot']['outcome']
        det_outcome = shot['detected_shot']['outcome']

        error_info = {
            'timestamp': shot['ground_truth_shot']['timestamp_seconds'],
            'type': shot['ground_truth_shot']['classification'],
            'gt_outcome': gt_outcome,
            'detected_outcome': det_outcome,
            'detected_reason': shot['detected_shot'].get('outcome_reason', 'unknown'),
            'confidence': shot['detected_shot'].get('decision_confidence', 0),
            'detection_confidence': shot['detected_shot'].get('detection_confidence', 0),
            'max_overlap': shot['detected_shot'].get('max_overlap_percentage', 0),
            'avg_overlap': shot['detected_shot'].get('avg_overlap_percentage', 0),
            'weighted_score': shot['detected_shot'].get('weighted_overlap_score', 0),
            'is_rim_bounce': shot['detected_shot'].get('is_rim_bounce', False),
            'rim_bounce_confidence': shot['detected_shot'].get('rim_bounce_confidence', 0),
            'entry_angle': shot['detected_shot'].get('entry_angle'),
            'full_shot': shot
        }

        if gt_outcome == 'made' and det_outcome == 'missed':
            false_negatives.append(error_info)
        elif gt_outcome == 'missed' and det_outcome == 'made':
            false_positives.append(error_info)

    # Analyze False Negatives
    print(f"\n{'='*80}")
    print(f"FALSE NEGATIVES (Made → Missed): {len(false_negatives)}")
    print(f"{'='*80}")

    if false_negatives:
        # Group by reason
        fn_by_reason = defaultdict(list)
        for fn in false_negatives:
            fn_by_reason[fn['detected_reason']].append(fn)

        print("\nBy Reason:")
        for reason, shots in sorted(fn_by_reason.items(), key=lambda x: len(x[1]), reverse=True):
            avg_conf = sum(s['confidence'] for s in shots) / len(shots)
            print(f"  {reason}: {len(shots)} shots (avg conf: {avg_conf:.3f})")
            for shot in shots:
                print(f"    {shot['timestamp']:.1f}s ({shot['type']}): conf={shot['confidence']:.3f}, "
                      f"overlap={shot['max_overlap']:.0f}%, rim_bounce={shot['is_rim_bounce']}")

        # Group by shot type
        fn_by_type = defaultdict(list)
        for fn in false_negatives:
            fn_by_type[fn['type']].append(fn)

        print("\nBy Shot Type:")
        for shot_type, shots in sorted(fn_by_type.items(), key=lambda x: len(x[1]), reverse=True):
            avg_conf = sum(s['confidence'] for s in shots) / len(shots)
            print(f"  {shot_type}: {len(shots)} shots (avg conf: {avg_conf:.3f})")

    # Analyze False Positives
    print(f"\n{'='*80}")
    print(f"FALSE POSITIVES (Missed → Made): {len(false_positives)}")
    print(f"{'='*80}")

    if false_positives:
        # Group by reason
        fp_by_reason = defaultdict(list)
        for fp in false_positives:
            fp_by_reason[fp['detected_reason']].append(fp)

        print("\nBy Reason:")
        for reason, shots in sorted(fp_by_reason.items(), key=lambda x: len(x[1]), reverse=True):
            avg_conf = sum(s['confidence'] for s in shots) / len(shots)
            print(f"  {reason}: {len(shots)} shots (avg conf: {avg_conf:.3f})")
            for shot in shots:
                print(f"    {shot['timestamp']:.1f}s ({shot['type']}): conf={shot['confidence']:.3f}, "
                      f"overlap={shot['max_overlap']:.0f}%, rim_bounce={shot['is_rim_bounce']}")

        # Group by shot type
        fp_by_type = defaultdict(list)
        for fp in false_positives:
            fp_by_type[fp['type']].append(fp)

        print("\nBy Shot Type:")
        for shot_type, shots in sorted(fp_by_type.items(), key=lambda x: len(x[1]), reverse=True):
            avg_conf = sum(s['confidence'] for s in shots) / len(shots)
            print(f"  {shot_type}: {len(shots)} shots (avg conf: {avg_conf:.3f})")

    return {
        'game_name': game_name,
        'false_negatives': false_negatives,
        'false_positives': false_positives,
        'summary': acc_summary
    }

if __name__ == "__main__":
    results_dir = Path("/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_near_angle_shot_detection/results")

    games = [
        "09-22(3-NL)_d2a451bb-c5c5-4b20-87bd-3e073fabf277",
        "09-23(1-NL)_fc2a92db-5a81-4f2a-acda-3e86b9098356"
    ]

    all_results = []

    for game in games:
        accuracy_file = results_dir / game / "accuracy_analysis.json"
        if accuracy_file.exists():
            result = analyze_near_angle_errors(accuracy_file)
            all_results.append(result)
        else:
            print(f"File not found: {accuracy_file}")

    # Combined analysis
    print(f"\n{'='*80}")
    print("COMBINED ANALYSIS")
    print(f"{'='*80}")

    all_fn = []
    all_fp = []

    for result in all_results:
        all_fn.extend(result['false_negatives'])
        all_fp.extend(result['false_positives'])

    print(f"\nTotal False Negatives: {len(all_fn)}")
    print(f"Total False Positives: {len(all_fp)}")

    # Combined reason analysis
    fn_reasons = defaultdict(list)
    for fn in all_fn:
        fn_reasons[fn['detected_reason']].append(fn)

    fp_reasons = defaultdict(list)
    for fp in all_fp:
        fp_reasons[fp['detected_reason']].append(fp)

    print("\nFalse Negatives by Reason:")
    for reason, shots in sorted(fn_reasons.items(), key=lambda x: len(x[1]), reverse=True):
        avg_conf = sum(s['confidence'] for s in shots) / len(shots) if shots else 0
        print(f"  {reason}: {len(shots)} shots (avg conf: {avg_conf:.3f})")

    print("\nFalse Positives by Reason:")
    for reason, shots in sorted(fp_reasons.items(), key=lambda x: len(x[1]), reverse=True):
        avg_conf = sum(s['confidence'] for s in shots) / len(shots) if shots else 0
        print(f"  {reason}: {len(shots)} shots (avg conf: {avg_conf:.3f})")

    # Identify low confidence errors
    print(f"\n{'='*80}")
    print("LOW CONFIDENCE ERRORS (Candidates for Far Angle Override)")
    print(f"{'='*80}")

    low_conf_fn = [fn for fn in all_fn if fn['confidence'] < 0.8]
    low_conf_fp = [fp for fp in all_fp if fp['confidence'] < 0.8]

    if all_fn:
        print(f"\nFalse Negatives with confidence < 0.8: {len(low_conf_fn)}/{len(all_fn)} ({len(low_conf_fn)/len(all_fn)*100:.1f}%)")
        for fn in low_conf_fn:
            print(f"  {fn['timestamp']:.1f}s ({fn['type']}): {fn['detected_reason']} (conf={fn['confidence']:.3f})")

    if all_fp:
        print(f"\nFalse Positives with confidence < 0.8: {len(low_conf_fp)}/{len(all_fp)} ({len(low_conf_fp)/len(all_fp)*100:.1f}%)")
        for fp in low_conf_fp:
            print(f"  {fp['timestamp']:.1f}s ({fp['type']}): {fp['detected_reason']} (conf={fp['confidence']:.3f})")

    # Save detailed results
    output = {
        'games_analyzed': games,
        'combined_stats': {
            'total_false_negatives': len(all_fn),
            'total_false_positives': len(all_fp),
            'low_confidence_fn': len(low_conf_fn),
            'low_confidence_fp': len(low_conf_fp)
        },
        'false_negative_patterns': {
            'by_reason': {reason: len(shots) for reason, shots in fn_reasons.items()},
            'by_type': {}
        },
        'false_positive_patterns': {
            'by_reason': {reason: len(shots) for reason, shots in fp_reasons.items()},
            'by_type': {}
        },
        'low_confidence_errors': {
            'false_negatives': [{k: v for k, v in fn.items() if k != 'full_shot'} for fn in low_conf_fn],
            'false_positives': [{k: v for k, v in fp.items() if k != 'full_shot'} for fp in low_conf_fp]
        },
        'all_false_negatives': [{k: v for k, v in fn.items() if k != 'full_shot'} for fn in all_fn],
        'all_false_positives': [{k: v for k, v in fp.items() if k != 'full_shot'} for fp in all_fp]
    }

    output_file = Path("near_angle_error_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Detailed results saved to: {output_file}")
