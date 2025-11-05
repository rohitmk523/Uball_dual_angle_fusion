#!/usr/bin/env python3
"""
Verify rim bounces and swishes are correctly classified in new results
"""

import json

def verify_critical_shots():
    """Verify far angle's critical advantages: rim bounces and swishes"""

    # Load new results
    results = json.load(open('results/game1-farright_b8c98465-3d89-4cbf-be78-1740432be0ee/accuracy_analysis.json'))

    matched_correct = results['detailed_analysis']['matched_correct']
    matched_incorrect = results['detailed_analysis']['matched_incorrect']

    print("="*80)
    print("VERIFYING FAR ANGLE'S CRITICAL ADVANTAGES")
    print("="*80)

    # Find rim bounces
    rim_bounces_correct = []
    rim_bounces_incorrect = []

    for item in matched_correct:
        shot = item['detected_shot']
        if 'rim_bounce' in shot.get('outcome_reason', ''):
            rim_bounces_correct.append(item)

    for item in matched_incorrect:
        shot = item['detected_shot']
        if 'rim_bounce' in shot.get('outcome_reason', ''):
            rim_bounces_incorrect.append(item)

    # Find clean swishes
    swishes_correct = []
    swishes_incorrect = []

    for item in matched_correct:
        shot = item['detected_shot']
        if 'swish' in shot.get('outcome_reason', ''):
            swishes_correct.append(item)

    for item in matched_incorrect:
        shot = item['detected_shot']
        if 'swish' in shot.get('outcome_reason', ''):
            swishes_incorrect.append(item)

    # Report rim bounces
    print(f"\n{'='*80}")
    print("1. RIM BOUNCE DETECTION (FAR ANGLE ADVANTAGE #1)")
    print(f"{'='*80}")

    print(f"\n✅ CORRECTLY DETECTED RIM BOUNCES: {len(rim_bounces_correct)}")
    for i, item in enumerate(rim_bounces_correct[:10], 1):
        shot = item['detected_shot']
        print(f"\n{i}. Time: {item['detected_timestamp_seconds']:.0f}s")
        print(f"   Ground Truth: {item['ground_truth_outcome'].upper()}")
        print(f"   Detected: {shot['outcome'].upper()} ✅")
        print(f"   Reason: {shot['outcome_reason']}")
        print(f"   Metrics: {shot['frames_in_zone']}f, {shot['upward_movement']:.0f}px up, {shot['downward_movement']:.0f}px down")

    if rim_bounces_incorrect:
        print(f"\n❌ INCORRECTLY DETECTED RIM BOUNCES: {len(rim_bounces_incorrect)}")
        for i, item in enumerate(rim_bounces_incorrect, 1):
            shot = item['detected_shot']
            print(f"\n{i}. Time: {item['detected_timestamp_seconds']:.0f}s")
            print(f"   Ground Truth: {item['ground_truth_outcome'].upper()}")
            print(f"   Detected: {shot['outcome'].upper()} ❌")
            print(f"   Reason: {shot['outcome_reason']}")
            print(f"   Metrics: {shot['frames_in_zone']}f, {shot['upward_movement']:.0f}px up, {shot['downward_movement']:.0f}px down")

    # Report swishes
    print(f"\n{'='*80}")
    print("2. CLEAN SWISH DETECTION (FAR ANGLE ADVANTAGE #2)")
    print(f"{'='*80}")

    print(f"\n✅ CORRECTLY DETECTED SWISHES: {len(swishes_correct)}")
    for i, item in enumerate(swishes_correct[:10], 1):
        shot = item['detected_shot']
        print(f"\n{i}. Time: {item['detected_timestamp_seconds']:.0f}s")
        print(f"   Ground Truth: {item['ground_truth_outcome'].upper()}")
        print(f"   Detected: {shot['outcome'].upper()} ✅")
        print(f"   Reason: {shot['outcome_reason']}")
        print(f"   Metrics: {shot['frames_in_zone']}f, {shot['upward_movement']:.0f}px up, cons:{shot['trajectory_consistency']:.2f}")

    if swishes_incorrect:
        print(f"\n❌ INCORRECTLY DETECTED SWISHES: {len(swishes_incorrect)}")
        for i, item in enumerate(swishes_incorrect, 1):
            shot = item['detected_shot']
            print(f"\n{i}. Time: {item['detected_timestamp_seconds']:.0f}s")
            print(f"   Ground Truth: {item['ground_truth_outcome'].upper()}")
            print(f"   Detected: {shot['outcome'].upper()} ❌")
            print(f"   Reason: {shot['outcome_reason']}")
            print(f"   Metrics: {shot['frames_in_zone']}f, {shot['upward_movement']:.0f}px up, cons:{shot['trajectory_consistency']:.2f}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    print(f"\nRim Bounce Detection:")
    print(f"  Correct: {len(rim_bounces_correct)}")
    print(f"  Incorrect: {len(rim_bounces_incorrect)}")
    print(f"  Success Rate: {len(rim_bounces_correct)/(len(rim_bounces_correct)+len(rim_bounces_incorrect))*100:.1f}%" if (len(rim_bounces_correct)+len(rim_bounces_incorrect)) > 0 else "  Success Rate: N/A")

    print(f"\nClean Swish Detection:")
    print(f"  Correct: {len(swishes_correct)}")
    print(f"  Incorrect: {len(swishes_incorrect)}")
    print(f"  Success Rate: {len(swishes_correct)/(len(swishes_correct)+len(swishes_incorrect))*100:.1f}%" if (len(swishes_correct)+len(swishes_incorrect)) > 0 else "  Success Rate: N/A")

    total_critical = len(rim_bounces_correct) + len(swishes_correct)
    total_critical_incorrect = len(rim_bounces_incorrect) + len(swishes_incorrect)

    print(f"\nOverall Critical Advantages:")
    print(f"  Correct: {total_critical}")
    print(f"  Incorrect: {total_critical_incorrect}")
    print(f"  Success Rate: {total_critical/(total_critical+total_critical_incorrect)*100:.1f}%" if (total_critical+total_critical_incorrect) > 0 else "  Success Rate: N/A")

    print(f"\n{'='*80}\n")

    return {
        'rim_bounces_correct': rim_bounces_correct,
        'rim_bounces_incorrect': rim_bounces_incorrect,
        'swishes_correct': swishes_correct,
        'swishes_incorrect': swishes_incorrect
    }

if __name__ == "__main__":
    verify_critical_shots()
