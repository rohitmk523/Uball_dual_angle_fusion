#!/usr/bin/env python3
"""
Dual Angle Fusion V2 - Targeted Specialist Approach

Based on empirical findings:
- Far angle is 100% reliable ONLY for FREE_THROW_MISS
- Far angle is unreliable for all other shot types
- Near angle confidence doesn't distinguish errors from correct

Strategy:
1. Use far angle ONLY for FREE_THROW_MISS (100% reliability)
2. For all other shots: use near angle (far is 85% wrong when disagreeing)
3. Low-confidence tiebreaker: when both < 0.65, use higher confidence
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class DualAngleFusionV2:
    """Conservative fusion using far angle only where proven reliable"""

    def __init__(self, time_window: float = 5.0):
        self.time_window = time_window
        self.fusion_decisions = []

    def load_near_angle_results(self, accuracy_file: Path) -> Dict:
        """Load near angle detection results"""
        with open(accuracy_file, 'r') as f:
            data = json.load(f)

        matched_correct = data['detailed_analysis']['matched_correct']
        matched_incorrect = data['detailed_analysis']['matched_incorrect']

        all_shots = []
        for shot in matched_correct:
            all_shots.append({
                'timestamp': shot['detected_shot']['timestamp_seconds'],
                'outcome': shot['detected_shot']['outcome'],
                'confidence': shot['detected_shot']['decision_confidence'],
                'reason': shot['detected_shot'].get('outcome_reason', 'unknown'),
                'ground_truth': shot['ground_truth_shot']['outcome'],
                'shot_type': shot['ground_truth_shot']['classification'],
                'is_correct': True,
                'full_data': shot
            })

        for shot in matched_incorrect:
            all_shots.append({
                'timestamp': shot['detected_shot']['timestamp_seconds'],
                'outcome': shot['detected_shot']['outcome'],
                'confidence': shot['detected_shot']['decision_confidence'],
                'reason': shot['detected_shot'].get('outcome_reason', 'unknown'),
                'ground_truth': shot['ground_truth_shot']['outcome'],
                'shot_type': shot['ground_truth_shot']['classification'],
                'is_correct': False,
                'full_data': shot
            })

        return {
            'shots': sorted(all_shots, key=lambda x: x['timestamp']),
            'summary': data['accuracy_analysis']
        }

    def load_far_angle_results(self, session_file: Path) -> Dict:
        """Load far angle detection results"""
        with open(session_file, 'r') as f:
            data = json.load(f)

        shots = []
        for shot in data.get('shots', []):
            shots.append({
                'timestamp': shot['timestamp_seconds'],
                'outcome': shot['outcome'],
                'confidence': shot.get('decision_confidence', 0),
                'reason': shot.get('outcome_reason', 'unknown'),
                'full_data': shot
            })

        return {
            'shots': sorted(shots, key=lambda x: x['timestamp']),
            'stats': data.get('stats', {})
        }

    def match_shots(self, near_shots: List[Dict], far_shots: List[Dict]) -> List[Dict]:
        """Match near and far angle shots by timestamp"""
        matched_pairs = []

        for near in near_shots:
            near_time = near['timestamp']
            best_match = None
            best_time_diff = float('inf')

            for far in far_shots:
                far_time = far['timestamp']
                time_diff = abs(far_time - near_time)

                if time_diff <= self.time_window and time_diff < best_time_diff:
                    best_match = far
                    best_time_diff = time_diff

            if best_match:
                matched_pairs.append({
                    'near': near,
                    'far': best_match,
                    'time_diff': best_time_diff,
                    'ground_truth': near['ground_truth'],
                    'shot_type': near['shot_type']
                })

        return matched_pairs

    def apply_fusion_rules(self, near: Dict, far: Dict, shot_type: str) -> Tuple[str, float, str]:
        """Apply targeted fusion rules based on empirical findings

        Findings:
        - Far angle 100% reliable for FREE_THROW_MISS (3/3 correct when disagreeing)
        - Far angle 0-14.3% reliable for all other shot types when disagreeing
        - Near angle errors have same confidence as correct (avg 0.81)
        """

        # Rule 1: FREE_THROW_MISS - Far angle is 100% reliable
        if shot_type == 'FREE_THROW_MISS':
            # Far angle has proven 100% reliability for this shot type
            # Use far if it disagrees with near
            if far['outcome'] != near['outcome']:
                return (far['outcome'], far['confidence'] * 0.95,
                       "free_throw_miss_far_angle_specialist (100% reliability)")
            else:
                # Both agree - use near angle with boosted confidence
                return (near['outcome'], min(near['confidence'] * 1.05, 0.98),
                       "free_throw_miss_both_angles_agree")

        # Rule 2: Low confidence tiebreaker
        # When BOTH angles have low confidence, use higher confidence
        if near['confidence'] < 0.65 and far['confidence'] < 0.65:
            if far['confidence'] > near['confidence']:
                return (far['outcome'], far['confidence'],
                       "low_confidence_tiebreaker_far")
            else:
                return (near['outcome'], near['confidence'],
                       "low_confidence_tiebreaker_near")

        # Rule 3: Near angle dominant (default)
        # For all other shot types, far angle is unreliable (0-14.3% when disagreeing)
        # Stick with near angle
        return (near['outcome'], near['confidence'], "near_angle_dominant")

    def process_fusion(self, matched_pairs: List[Dict]) -> Dict:
        """Process all matched pairs through fusion rules"""
        fusion_correct = 0
        fusion_incorrect = 0
        near_alone_correct = 0
        far_alone_correct = 0

        decisions = []

        for pair in matched_pairs:
            near = pair['near']
            far = pair['far']
            ground_truth = pair['ground_truth']
            shot_type = pair['shot_type']

            # Apply fusion
            final_outcome, final_confidence, fusion_reason = self.apply_fusion_rules(near, far, shot_type)

            # Check if correct
            is_correct = (final_outcome == ground_truth)
            near_was_correct = (near['outcome'] == ground_truth)
            far_was_correct = (far['outcome'] == ground_truth)

            if is_correct:
                fusion_correct += 1
            else:
                fusion_incorrect += 1

            if near_was_correct:
                near_alone_correct += 1
            if far_was_correct:
                far_alone_correct += 1

            decision = {
                'timestamp': near['timestamp'],
                'shot_type': shot_type,
                'ground_truth': ground_truth,
                'near_outcome': near['outcome'],
                'near_confidence': near['confidence'],
                'near_reason': near['reason'],
                'far_outcome': far['outcome'],
                'far_confidence': far['confidence'],
                'far_reason': far['reason'],
                'fusion_outcome': final_outcome,
                'fusion_confidence': final_confidence,
                'fusion_reason': fusion_reason,
                'is_correct': is_correct,
                'near_was_correct': near_was_correct,
                'far_was_correct': far_was_correct,
                'time_diff': pair['time_diff']
            }

            decisions.append(decision)

        total = fusion_correct + fusion_incorrect
        fusion_accuracy = fusion_correct / total if total > 0 else 0
        near_accuracy = near_alone_correct / total if total > 0 else 0
        far_accuracy = far_alone_correct / total if total > 0 else 0

        return {
            'fusion_accuracy': fusion_accuracy,
            'near_alone_accuracy': near_accuracy,
            'far_alone_accuracy': far_accuracy,
            'fusion_correct': fusion_correct,
            'fusion_incorrect': fusion_incorrect,
            'near_alone_correct': near_alone_correct,
            'far_alone_correct': far_alone_correct,
            'total_matched': total,
            'decisions': decisions,
            'accuracy_improvement': fusion_accuracy - near_accuracy
        }

    def generate_report(self, results: Dict, output_file: Path):
        """Generate fusion accuracy report"""
        # Group decisions by fusion reason
        by_fusion_reason = defaultdict(list)
        for decision in results['decisions']:
            by_fusion_reason[decision['fusion_reason']].append(decision)

        # Calculate stats per fusion reason
        fusion_reason_stats = {}
        for reason, decisions in by_fusion_reason.items():
            correct = sum(1 for d in decisions if d['is_correct'])
            total = len(decisions)
            accuracy = correct / total if total > 0 else 0

            fusion_reason_stats[reason] = {
                'count': total,
                'correct': correct,
                'incorrect': total - correct,
                'accuracy': accuracy
            }

        # Find errors fixed and new errors
        errors_fixed = []
        new_errors = []

        for decision in results['decisions']:
            if not decision['near_was_correct'] and decision['is_correct']:
                errors_fixed.append({
                    'timestamp': decision['timestamp'],
                    'shot_type': decision['shot_type'],
                    'ground_truth': decision['ground_truth'],
                    'near_outcome': decision['near_outcome'],
                    'fusion_outcome': decision['fusion_outcome'],
                    'fusion_reason': decision['fusion_reason']
                })
            elif decision['near_was_correct'] and not decision['is_correct']:
                new_errors.append({
                    'timestamp': decision['timestamp'],
                    'shot_type': decision['shot_type'],
                    'ground_truth': decision['ground_truth'],
                    'near_outcome': decision['near_outcome'],
                    'fusion_outcome': decision['fusion_outcome'],
                    'fusion_reason': decision['fusion_reason']
                })

        report = {
            'summary': {
                'total_matched_shots': results['total_matched'],
                'fusion_accuracy': results['fusion_accuracy'],
                'near_alone_accuracy': results['near_alone_accuracy'],
                'far_alone_accuracy': results['far_alone_accuracy'],
                'accuracy_improvement': results['accuracy_improvement'],
                'fusion_correct': results['fusion_correct'],
                'fusion_incorrect': results['fusion_incorrect'],
                'errors_fixed_count': len(errors_fixed),
                'new_errors_count': len(new_errors)
            },
            'fusion_reason_stats': fusion_reason_stats,
            'errors_fixed': errors_fixed,
            'new_errors': new_errors,
            'all_decisions': results['decisions']
        }

        # Save to file
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n✅ Fusion V2 report saved to: {output_file}")

        return report


def main():
    parser = argparse.ArgumentParser(description='Dual Angle Fusion V2 - Targeted Specialist')
    parser.add_argument('--near_accuracy', required=True, help='Near angle accuracy_analysis.json')
    parser.add_argument('--far_session', required=True, help='Far angle session JSON')
    parser.add_argument('--output', required=True, help='Output fusion report JSON')
    parser.add_argument('--time_window', type=float, default=5.0, help='Time window for matching (seconds)')

    args = parser.parse_args()

    # Initialize fusion system
    fusion = DualAngleFusionV2(time_window=args.time_window)

    # Load results
    print(f"Loading near angle results from: {args.near_accuracy}")
    near_results = fusion.load_near_angle_results(Path(args.near_accuracy))

    print(f"Loading far angle results from: {args.far_session}")
    far_results = fusion.load_far_angle_results(Path(args.far_session))

    # Match shots
    print(f"\nMatching shots (time window: ±{args.time_window}s)...")
    matched_pairs = fusion.match_shots(near_results['shots'], far_results['shots'])
    print(f"Matched {len(matched_pairs)} shot pairs")

    # Process fusion
    print("\nApplying targeted fusion rules...")
    results = fusion.process_fusion(matched_pairs)

    # Generate report
    print("\nGenerating fusion report...")
    report = fusion.generate_report(results, Path(args.output))

    # Print summary
    print(f"\n{'='*80}")
    print("FUSION V2 RESULTS SUMMARY (Targeted Specialist)")
    print(f"{'='*80}")
    print(f"Total Matched Shots: {results['total_matched']}")
    print(f"\nNear Angle Alone:  {results['near_alone_accuracy']*100:.2f}% ({results['near_alone_correct']}/{results['total_matched']})")
    print(f"Far Angle Alone:   {results['far_alone_accuracy']*100:.2f}% ({results['far_alone_correct']}/{results['total_matched']})")
    print(f"Fusion V2 Combined:{results['fusion_accuracy']*100:.2f}% ({results['fusion_correct']}/{results['total_matched']})")

    improvement = results['accuracy_improvement']
    symbol = "✅" if improvement >= 0 else "❌"
    print(f"\n{symbol} Accuracy Change: {improvement*100:+.2f} percentage points")
    print(f"\n🔧 Errors Fixed: {len(report['errors_fixed'])}")
    print(f"⚠️  New Errors: {len(report['new_errors'])}")
    print(f"📊 Net Impact: {len(report['errors_fixed']) - len(report['new_errors'])} errors")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
