#!/usr/bin/env python3
"""
Analyze the 8 timestamps where Far Angle was correct and Near Angle failed
"""

import json
from pathlib import Path

# The 8 winning timestamps
WINNING_TIMESTAMPS = [381, 939, 1405, 1698, 2289, 2555, 2638, 2862]

def analyze_shots():
    """Analyze far angle shots at winning timestamps"""

    # Load far angle session data
    far_session = json.load(open('Game-1/game1_farright_session.json'))

    # Load far angle accuracy results
    far_accuracy = json.load(open('results/game1-farright_311ee2cb-ebc6-4d9b-908a-2ebe001fc395/accuracy_analysis.json'))

    # Load near angle accuracy results for comparison
    near_accuracy = json.load(open('/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_near_angle_shot_detection/results/09-23(1-NL)_fc2a92db-5a81-4f2a-acda-3e86b9098356/accuracy_analysis.json'))

    print("="*80)
    print("FAR ANGLE WINNING SHOTS ANALYSIS")
    print("="*80)

    # Categorize by type
    rim_bounces = []  # Near said MADE, actually MISSED
    clean_makes = []  # Near said MISSED, actually MADE

    # Get matched correct from far angle
    far_correct = far_accuracy['detailed_analysis']['matched_correct']

    for timestamp in WINNING_TIMESTAMPS:
        # Find this shot in far angle results
        far_shot = None
        for shot in far_correct:
            ts = int(shot['detected_timestamp_seconds'])
            if abs(ts - timestamp) <= 2:  # Within 2 seconds
                far_shot = shot
                break

        if far_shot:
            ground_truth = far_shot['ground_truth_outcome']
            far_detected = far_shot['detected_outcome']

            # Get detection details
            detection = far_shot['detected_shot']

            if ground_truth == 'missed':
                # This is a rim bounce that near angle missed
                rim_bounces.append({
                    'timestamp': timestamp,
                    'detection': detection
                })
            else:
                # This is a clean make that near angle missed
                clean_makes.append({
                    'timestamp': timestamp,
                    'detection': detection
                })

    # Analyze rim bounces
    print(f"\n{'='*80}")
    print(f"1. RIM BOUNCES (Far Correct, Near Wrong) - {len(rim_bounces)} cases")
    print(f"{'='*80}")
    print("\nNear Angle FALSELY classified these as MADE")
    print("Far Angle CORRECTLY detected as MISSED rim bounces")

    for i, shot in enumerate(rim_bounces, 1):
        d = shot['detection']
        print(f"\n{i}. Time: {shot['timestamp']}s")
        print(f"   Outcome: {d['outcome'].upper()}")
        print(f"   Reason: {d['outcome_reason']}")
        print(f"   Frames in zone: {d['frames_in_zone']}")
        print(f"   Downward: {d['downward_movement']:.0f}px")
        print(f"   Upward: {d['upward_movement']:.0f}px")
        print(f"   Consistency: {d['trajectory_consistency']:.3f}")
        print(f"   Confidence: {d['decision_confidence']:.2f}")

        # Check if it triggered rim bounce rule
        if 'rim_bounce' in d['outcome_reason']:
            print(f"   ✅ RIM BOUNCE RULE TRIGGERED")
        else:
            print(f"   ⚠️  Detected by other rule: {d['outcome_reason']}")

    # Find patterns
    if rim_bounces:
        avg_frames = sum(s['detection']['frames_in_zone'] for s in rim_bounces) / len(rim_bounces)
        avg_upward = sum(s['detection']['upward_movement'] for s in rim_bounces) / len(rim_bounces)
        avg_downward = sum(s['detection']['downward_movement'] for s in rim_bounces) / len(rim_bounces)
        avg_consistency = sum(s['detection']['trajectory_consistency'] for s in rim_bounces) / len(rim_bounces)

        print(f"\n{'='*80}")
        print("RIM BOUNCE PATTERNS:")
        print(f"{'='*80}")
        print(f"Average Frames in Zone: {avg_frames:.1f}")
        print(f"Average Upward Movement: {avg_upward:.1f}px")
        print(f"Average Downward Movement: {avg_downward:.1f}px")
        print(f"Average Consistency: {avg_consistency:.3f}")
        print(f"Average Up/Down Ratio: {avg_upward/avg_downward:.3f}")

    # Analyze clean makes
    print(f"\n{'='*80}")
    print(f"2. CLEAN MAKES (Far Correct, Near Wrong) - {len(clean_makes)} cases")
    print(f"{'='*80}")
    print("\nNear Angle FALSELY classified these as MISSED")
    print("Far Angle CORRECTLY detected as MADE")

    for i, shot in enumerate(clean_makes, 1):
        d = shot['detection']
        print(f"\n{i}. Time: {shot['timestamp']}s")
        print(f"   Outcome: {d['outcome'].upper()}")
        print(f"   Reason: {d['outcome_reason']}")
        print(f"   Frames in zone: {d['frames_in_zone']}")
        print(f"   Downward: {d['downward_movement']:.0f}px")
        print(f"   Upward: {d['upward_movement']:.0f}px")
        print(f"   Consistency: {d['trajectory_consistency']:.3f}")
        print(f"   Confidence: {d['decision_confidence']:.2f}")

        # Check if it triggered swish rule
        if 'swish' in d['outcome_reason']:
            print(f"   ✅ CLEAN SWISH RULE TRIGGERED")
        else:
            print(f"   ⚠️  Detected by other rule: {d['outcome_reason']}")

    # Find patterns
    if clean_makes:
        avg_frames = sum(s['detection']['frames_in_zone'] for s in clean_makes) / len(clean_makes)
        avg_upward = sum(s['detection']['upward_movement'] for s in clean_makes) / len(clean_makes)
        avg_downward = sum(s['detection']['downward_movement'] for s in clean_makes) / len(clean_makes)
        avg_consistency = sum(s['detection']['trajectory_consistency'] for s in clean_makes) / len(clean_makes)

        print(f"\n{'='*80}")
        print("CLEAN MAKE PATTERNS:")
        print(f"{'='*80}")
        print(f"Average Frames in Zone: {avg_frames:.1f}")
        print(f"Average Upward Movement: {avg_upward:.1f}px")
        print(f"Average Downward Movement: {avg_downward:.1f}px")
        print(f"Average Consistency: {avg_consistency:.3f}")

    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS FOR FAR ANGLE LOGIC:")
    print(f"{'='*80}")

    if rim_bounces:
        avg_frames = sum(s['detection']['frames_in_zone'] for s in rim_bounces) / len(rim_bounces)
        avg_upward = sum(s['detection']['upward_movement'] for s in rim_bounces) / len(rim_bounces)

        print(f"\n1. RIM BOUNCE DETECTION:")
        print(f"   Current: frames >= 30 AND upward >= 35px")
        print(f"   Actual rim bounces average: {avg_frames:.0f} frames, {avg_upward:.0f}px upward")
        print(f"   Recommendation: Keep current thresholds or slightly lower")

    if clean_makes:
        avg_upward = sum(s['detection']['upward_movement'] for s in clean_makes) / len(clean_makes)
        avg_consistency = sum(s['detection']['trajectory_consistency'] for s in clean_makes) / len(clean_makes)

        print(f"\n2. CLEAN SWISH/MAKE DETECTION:")
        print(f"   Current: upward <= 20px AND consistency >= 0.85 for swish")
        print(f"   Actual clean makes average: {avg_upward:.0f}px upward, {avg_consistency:.3f} consistency")
        print(f"   Recommendation: Adjust thresholds based on actual data")

    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    analyze_shots()
