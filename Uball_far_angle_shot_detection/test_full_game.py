#!/usr/bin/env python3
"""
Full Game Test Script - Iterative Accuracy Improvement

This script tests detection against ALL ground truth shots in the game,
analyzes errors, and provides detailed recommendations for logic improvements.
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def fetch_ground_truth(game_id: str, angle: str) -> List[Dict]:
    """Fetch ground truth from Supabase"""
    from accuracy_validator import AccuracyValidator

    validator = AccuracyValidator()
    return validator.fetch_ground_truth(game_id, angle)


def test_timestamp(video_path: str, model_path: str, gt_shot: Dict, window: int = 5) -> Dict:
    """Test detection on a single ground truth shot

    Uses same approach as test_incorrect_matches.py - parses log output directly

    Args:
        video_path: Path to video file
        model_path: Path to YOLO model
        gt_shot: Ground truth shot data
        window: Time window in seconds

    Returns:
        Test result with comparison
    """
    timestamp = gt_shot['timestamp_seconds']
    gt_outcome = gt_shot['outcome']

    start_time = max(0, timestamp - window)
    # Add 3 seconds to allow for shot finalization timeout
    end_time = timestamp + window + 3

    # Run detection
    cmd = [
        'python', 'main.py',
        '--action', 'video',
        '--video_path', video_path,
        '--model', model_path,
        '--start_time', str(int(start_time)),
        '--end_time', str(int(end_time))
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # Parse output to find shot detection
        # Accept ANY shot within the test window (not just exact timestamp match)
        detected_outcome = None
        detected_reason = None
        detected_timestamp = None

        for line in result.stderr.split('\n'):
            if 'Shot detected' in line:
                # Extract the detected timestamp from the log line
                # Format: "Shot detected at 48.5s: MADE/MISSED"
                try:
                    timestamp_str = line.split('at ')[1].split('s:')[0]
                    detected_ts = float(timestamp_str)

                    # Check if detected shot is within our test window
                    if start_time <= detected_ts <= end_time:
                        detected_timestamp = detected_ts

                        if 'MADE' in line:
                            detected_outcome = 'made'
                        elif 'MISSED' in line:
                            detected_outcome = 'missed'

                        # Extract reason
                        if 'reason:' in line:
                            reason_part = line.split('reason:')[1].strip()
                            detected_reason = reason_part.rstrip(')')

                        # Take the first shot found in window
                        break
                except (IndexError, ValueError):
                    continue

        # Check if detected shot matches ground truth
        is_correct = detected_outcome == gt_outcome if detected_outcome else False

        return {
            'timestamp': timestamp,
            'gt_outcome': gt_outcome,
            'gt_classification': gt_shot['classification'],
            'detected_outcome': detected_outcome,
            'detected_reason': detected_reason,
            'correct': is_correct,
            'was_detected': detected_outcome is not None,
            'error_type': _classify_error(gt_outcome, detected_outcome)
        }

    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout testing {timestamp:.1f}s")
        return {
            'timestamp': timestamp,
            'gt_outcome': gt_outcome,
            'gt_classification': gt_shot['classification'],
            'detected_outcome': None,
            'detected_reason': 'timeout',
            'correct': False,
            'was_detected': False,
            'error_type': 'not_detected'
        }
    except Exception as e:
        logger.error(f"Error testing {timestamp:.1f}s: {e}")
        return {
            'timestamp': timestamp,
            'gt_outcome': gt_outcome,
            'gt_classification': gt_shot['classification'],
            'detected_outcome': None,
            'detected_reason': str(e),
            'correct': False,
            'was_detected': False,
            'error_type': 'not_detected'
        }


def _classify_error(gt_outcome: str, detected_outcome: str) -> str:
    """Classify the type of error"""
    if detected_outcome is None:
        return 'not_detected'
    elif gt_outcome == detected_outcome:
        return 'correct'
    elif gt_outcome == 'made' and detected_outcome == 'missed':
        return 'false_negative'  # Made shot classified as missed
    elif gt_outcome == 'missed' and detected_outcome == 'made':
        return 'false_positive'  # Missed shot classified as made
    else:
        return 'unknown'


def analyze_errors(results: List[Dict]) -> Dict:
    """Analyze error patterns and generate recommendations"""

    analysis = {
        'total_shots': len(results),
        'correct': 0,
        'false_negatives': [],  # Made shots we called missed
        'false_positives': [],  # Missed shots we called made
        'not_detected': [],
        'by_shot_type': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'by_outcome': defaultdict(lambda: {'correct': 0, 'total': 0})
    }

    for result in results:
        error_type = result['error_type']
        gt_classification = result['gt_classification']
        gt_outcome = result['gt_outcome']

        # Count by shot type
        analysis['by_shot_type'][gt_classification]['total'] += 1
        analysis['by_outcome'][gt_outcome]['total'] += 1

        if error_type == 'correct':
            analysis['correct'] += 1
            analysis['by_shot_type'][gt_classification]['correct'] += 1
            analysis['by_outcome'][gt_outcome]['correct'] += 1
        elif error_type == 'false_negative':
            analysis['false_negatives'].append(result)
        elif error_type == 'false_positive':
            analysis['false_positives'].append(result)
        elif error_type == 'not_detected':
            analysis['not_detected'].append(result)

    # Analyze false negatives reasons
    if analysis['false_negatives']:
        fn_reasons = defaultdict(int)
        for fn in analysis['false_negatives']:
            reason = fn.get('detected_reason', 'unknown')
            fn_reasons[reason] += 1

        analysis['false_negative_reasons'] = dict(fn_reasons)

    # Analyze false positives reasons
    if analysis['false_positives']:
        fp_reasons = defaultdict(int)
        for fp in analysis['false_positives']:
            reason = fp.get('detected_reason', 'unknown')
            fp_reasons[reason] += 1

        analysis['false_positive_reasons'] = dict(fp_reasons)

    return analysis


def generate_recommendations(analysis: Dict) -> List[str]:
    """Generate logic improvement recommendations based on analysis"""
    recommendations = []

    fn_count = len(analysis['false_negatives'])
    fp_count = len(analysis['false_positives'])
    nd_count = len(analysis['not_detected'])
    total = analysis['total_shots']

    # Calculate detection rate
    detected = total - nd_count
    detection_rate = (detected / total * 100) if total > 0 else 0

    recommendations.append("\n" + "="*80)
    recommendations.append("RECOMMENDATIONS")
    recommendations.append("="*80)

    # Issue 1: Too many not detected
    if nd_count > detected:
        recommendations.append(f"\n🚨 CRITICAL: {nd_count}/{total} shots NOT DETECTED ({nd_count/total*100:.1f}%)")
        recommendations.append("   Zone too small or thresholds too strict!")
        recommendations.append("   FIXES:")
        recommendations.append("   1. Increase HOOP_ZONE_WIDTH from 60 to 70")
        recommendations.append("   2. Increase HOOP_ZONE_VERTICAL from 70 to 80")
        recommendations.append("   3. Reduce MIN_FRAMES_IN_ZONE from 3 to 2")

    # Issue 2: High false negatives
    if fn_count > 5:
        recommendations.append(f"\n⚠️  {fn_count} Made shots detected as MISSED")

        if 'false_negative_reasons' in analysis:
            recommendations.append("   Common reasons:")
            for reason, count in sorted(analysis['false_negative_reasons'].items(), key=lambda x: -x[1]):
                recommendations.append(f"     - {reason}: {count}")

            # Specific fixes based on reasons
            reasons = analysis['false_negative_reasons']
            if 'trajectory_grazed_hoop' in reasons:
                count = reasons['trajectory_grazed_hoop']
                recommendations.append(f"\n   FIX: {count} shots classified as 'grazed'")
                recommendations.append("   → Reduce points_inside threshold from 5 to 3")

            if 'rim_contact_detected' in reasons:
                count = reasons['rim_contact_detected']
                recommendations.append(f"\n   FIX: {count} shots flagged as 'rim_contact'")
                recommendations.append("   → Increase upward threshold from 10px to 20px OR remove rule")

    # Issue 3: High false positives
    if fp_count > 5:
        recommendations.append(f"\n⚠️  {fp_count} Missed shots detected as MADE")

        if 'false_positive_reasons' in analysis:
            recommendations.append("   Common reasons:")
            for reason, count in sorted(analysis['false_positive_reasons'].items(), key=lambda x: -x[1]):
                recommendations.append(f"     - {reason}: {count}")

            recommendations.append("\n   FIX: Increase strictness")
            recommendations.append("   → Require more points_inside or line_crossings")

    # Detection rate issue
    if detection_rate < 80:
        recommendations.append(f"\n⚠️  Low detection rate: {detection_rate:.1f}%")
        recommendations.append("   → Apply fixes from issues above")

    return recommendations


def main():
    """Main test workflow"""
    if len(sys.argv) < 5:
        print("Usage: python test_full_game.py <video_path> <model_path> <game_id> <angle>")
        print("\nExample:")
        print("  python test_full_game.py \\")
        print("    Game-2/game2_farright.mp4 \\")
        print("    runs/detect/basketball_yolo11n2/weights/best.pt \\")
        print("    b9477b23-c490-42ca-84e1-5dbae4150f54 \\")
        print("    RIGHT")
        sys.exit(1)

    video_path = sys.argv[1]
    model_path = sys.argv[2]
    game_id = sys.argv[3]
    angle = sys.argv[4]

    print("\n" + "="*80)
    print("FULL GAME ACCURACY TEST")
    print("="*80)
    print(f"Video: {video_path}")
    print(f"Game ID: {game_id}")
    print(f"Angle: {angle}")
    print("="*80 + "\n")

    # Fetch ground truth
    logger.info("Fetching ground truth from Supabase...")
    ground_truth = fetch_ground_truth(game_id, angle)

    if not ground_truth:
        logger.error("No ground truth found!")
        sys.exit(1)

    logger.info(f"Found {len(ground_truth)} ground truth shots")

    # Test each shot
    results = []
    for i, gt_shot in enumerate(ground_truth, 1):
        timestamp = gt_shot['timestamp_seconds']
        gt_outcome = gt_shot['outcome']

        print(f"\n[{i}/{len(ground_truth)}] Testing {timestamp:.1f}s (GT: {gt_outcome})...", end=" ")

        result = test_timestamp(video_path, model_path, gt_shot)
        results.append(result)

        if result['correct']:
            print("✅ CORRECT")
        elif result['was_detected']:
            print(f"❌ WRONG (detected: {result['detected_outcome']})")
        else:
            print("⚠️ NOT DETECTED")

    # Analyze results
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)

    analysis = analyze_errors(results)

    total = analysis['total_shots']
    correct = analysis['correct']
    fn_count = len(analysis['false_negatives'])
    fp_count = len(analysis['false_positives'])
    nd_count = len(analysis['not_detected'])

    accuracy = (correct / total * 100) if total > 0 else 0

    print(f"\nTotal Ground Truth Shots: {total}")
    print(f"Correct Classifications: {correct} ({accuracy:.1f}%)")
    print(f"False Negatives (Made→Missed): {fn_count} ({fn_count/total*100:.1f}%)")
    print(f"False Positives (Missed→Made): {fp_count} ({fp_count/total*100:.1f}%)")
    print(f"Not Detected: {nd_count} ({nd_count/total*100:.1f}%)")

    # Shot type breakdown
    print("\n--- By Shot Type ---")
    for shot_type, stats in sorted(analysis['by_shot_type'].items()):
        type_acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"{shot_type}: {stats['correct']}/{stats['total']} ({type_acc:.1f}%)")

    # False negative patterns
    if 'false_negative_patterns' in analysis:
        print("\n--- False Negative Patterns (Made shots we missed) ---")
        patterns = analysis['false_negative_patterns']
        print(f"Average points inside: {patterns['avg_points_inside']:.1f}")
        print(f"Average line crossings: {patterns['avg_line_crossings']:.1f}")
        print(f"Average upward movement: {patterns['avg_upward']:.1f}px")
        print(f"Common reasons:")
        for reason, count in sorted(patterns['common_reasons'].items(), key=lambda x: -x[1]):
            print(f"  - {reason}: {count}")

    # Generate recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    recommendations = generate_recommendations(analysis)
    if recommendations:
        for rec in recommendations:
            print(rec)
    else:
        print("✅ Logic performing well! No major changes recommended.")

    # Save detailed results
    output_file = Path('full_game_test_results.json')
    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'total': total,
                'correct': correct,
                'accuracy_percentage': accuracy,
                'false_negatives': fn_count,
                'false_positives': fp_count,
                'not_detected': nd_count
            },
            'analysis': analysis,
            'recommendations': recommendations,
            'detailed_results': results
        }, f, indent=2)

    print(f"\n✅ Detailed results saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    main()
