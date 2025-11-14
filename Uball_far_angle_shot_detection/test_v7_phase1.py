#!/usr/bin/env python3
"""
Test V7 Phase 1 fixes on specific error timestamps from V6 analysis

Phase 1 Target Errors (15 total):
- Priority 4 (wrong_depth): 5 errors - size ratios 0.417-0.473 exceeded 0.40
- Priority 1 (no_top_crossing): 10 errors - ball never crossed top boundary

Expected: These 15 errors should be fixed after Phase 1
"""
import sys
import json
from pathlib import Path

# Test timestamps for Priority 4 (wrong_depth - 5 errors)
PRIORITY_4_ERRORS = {
    'Game 2': {
        'game_id': 'c07e85e8-9ae4-4adc-a757-3ca00d9d292a',
        'video_path': 'input/09-23/Game-2/game2_farright.mp4',
        'timestamps': [87.5, 623.6],
        'expected_outcome': 'made',  # All were GT=made, predicted=missed
        'expected_fix': 'Size ratio 0.444-0.473 now accepted (MAX=0.50)'
    },
    'Game 3': {
        'game_id': 'a3c9c041-6762-450a-8444-413767bb6428',
        'video_path': 'input/09-23/Game-3/game3_farright.mp4',
        'timestamps': [105.5, 780.9, 2984.4],
        'expected_outcome': 'made',
        'expected_fix': 'Size ratio 0.417-0.439-0.435 now accepted (MAX=0.50)'
    }
}

# Test timestamps for Priority 1 (no_top_crossing - 10 errors)
PRIORITY_1_ERRORS = {
    'Game 1': {
        'game_id': 'c56b96a1-6e85-469e-8ebe-6a86b929bad9',
        'video_path': 'input/09-23/Game-1/game1_farright.mp4',
        'timestamps': [25.8, 918.2, 2639.7],
        'expected_outcome': 'made',  # All were GT=made, predicted=missed
        'expected_fix': 'Expanded zone catches ball earlier (195px above hoop)'
    },
    'Game 2': {
        'game_id': 'c07e85e8-9ae4-4adc-a757-3ca00d9d292a',
        'video_path': 'input/09-23/Game-2/game2_farright.mp4',
        'timestamps': [685.6, 809.0, 880.0, 2545.5],
        'expected_outcome': 'made',
        'expected_fix': 'Expanded zone catches ball earlier (195px above hoop)'
    },
    'Game 3': {
        'game_id': 'a3c9c041-6762-450a-8444-413767bb6428',
        'video_path': 'input/09-23/Game-3/game3_farright.mp4',
        'timestamps': [734.4, 1538.8, 2324.2],
        'expected_outcome': 'made',
        'expected_fix': 'Expanded zone catches ball earlier (195px above hoop)'
    }
}

def run_test_on_timestamps(game_name, game_data, priority_name):
    """Run test on specific timestamps and check if they're fixed"""
    print(f"\n{'='*80}")
    print(f"Testing {priority_name}: {game_name}")
    print(f"{'='*80}")
    print(f"Video: {game_data['video_path']}")
    print(f"Game ID: {game_data['game_id']}")
    print(f"Test Timestamps: {game_data['timestamps']}")
    print(f"Expected Outcome: {game_data['expected_outcome']}")
    print(f"Expected Fix: {game_data['expected_fix']}")
    print()

    # Run detection on this video with V7 Phase 1
    import subprocess

    cmd = [
        'python3', 'main.py',
        '--action', 'video',
        '--video_path', game_data['video_path'],
        '--model', 'runs/detect/basketball_yolo11n2/weights/best.pt',
        '--game_id', game_data['game_id'],
        '--validate_accuracy',
        '--angle', 'RIGHT'
    ]

    print(f"Running command: {' '.join(cmd)}")
    print("This will process the full video and validate against ground truth...")
    print()

    return cmd

def main():
    print("=" * 80)
    print("V7 PHASE 1 VALIDATION TEST")
    print("=" * 80)
    print()
    print("Phase 1 Changes:")
    print("  ✅ Priority 4: MAX_BALL_HOOP_RATIO increased from 0.40 to 0.50")
    print("  ✅ Priority 1: Detection zone expanded upward by 100px (195px total above hoop)")
    print()
    print("Target Errors:")
    print("  - Priority 4 (wrong_depth): 5 errors")
    print("  - Priority 1 (no_top_crossing): 10 errors")
    print("  - TOTAL: 15 errors should be fixed")
    print()

    print("=" * 80)
    print("TESTING STRATEGY")
    print("=" * 80)
    print()
    print("We'll run ONE test game to validate Phase 1 fixes:")
    print("  - Game 3 has BOTH Priority 4 errors (3) and Priority 1 errors (3)")
    print("  - Total 6 target errors in Game 3")
    print()
    print("Expected Game 3 improvement:")
    print("  - V6: 87.13% (13 errors out of 101 matched shots)")
    print("  - V7 Phase 1: ~93% (7 errors out of 101, if 6 fixed)")
    print()

    # Test on Game 3 first (has both types of errors)
    game_name = 'Game 3'

    print("=" * 80)
    print(f"RUNNING GAME 3 WITH V7 PHASE 1")
    print("=" * 80)
    print()

    # Combine both error types for Game 3
    p4_data = PRIORITY_4_ERRORS['Game 3']
    p1_data = PRIORITY_1_ERRORS['Game 3']

    print(f"Priority 4 target timestamps: {p4_data['timestamps']}")
    print(f"Priority 1 target timestamps: {p1_data['timestamps']}")
    print()

    cmd = [
        'python3', 'main.py',
        '--action', 'video',
        '--video_path', 'input/09-23/Game-3/game3_farright.mp4',
        '--model', 'runs/detect/basketball_yolo11n2/weights/best.pt',
        '--game_id', 'a3c9c041-6762-450a-8444-413767bb6428',
        '--validate_accuracy',
        '--angle', 'RIGHT'
    ]

    print(f"Command: {' '.join(cmd)}")
    print()
    print("Starting test run...")
    print()

    import subprocess
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print()
        print("=" * 80)
        print("✅ Game 3 V7 Phase 1 test completed!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Check the results directory for accuracy_analysis.json")
        print("2. Compare with V6 Game 3: 87.13% (13 errors)")
        print("3. Verify if the 6 target error timestamps are now fixed")
        print("4. Expected: ~93% accuracy if all 6 errors fixed")
    else:
        print()
        print("❌ Test failed with error code:", result.returncode)

if __name__ == '__main__':
    main()
