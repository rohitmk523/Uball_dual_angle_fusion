#!/usr/bin/env python3
import json

# Load OLD results (65.33% accuracy)
with open('results/game1-farright_b8c98465-3d89-4cbf-be78-1740432be0ee/accuracy_analysis.json', 'r') as f:
    old_data = json.load(f)

# Load NEW results (57.3% accuracy)
with open('results/game1-farright_1d48e492-1729-438d-82af-bd60d3966ba9/accuracy_analysis.json', 'r') as f:
    new_data = json.load(f)

old_errors = old_data['detailed_analysis']['matched_incorrect']
new_errors = new_data['detailed_analysis']['matched_incorrect']

print("="*80)
print("ACCURACY COMPARISON")
print("="*80)
print(f"OLD: {old_data['accuracy_analysis']['matched_shots_accuracy']:.2f}% ({old_data['accuracy_analysis']['matched_correct']}/{old_data['timestamp_matching']['total_matches']} correct)")
print(f"NEW: {new_data['accuracy_analysis']['matched_shots_accuracy']:.2f}% ({new_data['accuracy_analysis']['matched_correct']}/{new_data['timestamp_matching']['total_matches']} correct)")
print(f"CHANGE: {new_data['accuracy_analysis']['matched_shots_accuracy'] - old_data['accuracy_analysis']['matched_shots_accuracy']:.2f} percentage points")
print()

# Create timestamp -> shot mappings
old_error_map = {round(shot['detected_shot']['timestamp_seconds'], 1): shot for shot in old_errors}
new_error_map = {round(shot['detected_shot']['timestamp_seconds'], 1): shot for shot in new_errors}

old_correct_map = {round(shot['detected_shot']['timestamp_seconds'], 1): shot for shot in old_data['detailed_analysis']['matched_correct']}
new_correct_map = {round(shot['detected_shot']['timestamp_seconds'], 1): shot for shot in new_data['detailed_analysis']['matched_correct']}

# Find REGRESSIONS (was correct, now wrong)
regressions = []
for ts in old_correct_map.keys():
    if ts in new_error_map:
        regressions.append({
            'timestamp': ts,
            'old': old_correct_map[ts],
            'new': new_error_map[ts]
        })

# Find FIXES (was wrong, now correct)
fixes = []
for ts in old_error_map.keys():
    if ts in new_correct_map:
        fixes.append({
            'timestamp': ts,
            'old': old_error_map[ts],
            'new': new_correct_map[ts]
        })

# Find STILL WRONG (was wrong, still wrong)
still_wrong = []
for ts in old_error_map.keys():
    if ts in new_error_map:
        still_wrong.append({
            'timestamp': ts,
            'old': old_error_map[ts],
            'new': new_error_map[ts]
        })

# Find NEW ERRORS (wasn't in old results at all)
new_only_errors = []
for ts in new_error_map.keys():
    if ts not in old_error_map and ts not in old_correct_map:
        new_only_errors.append({
            'timestamp': ts,
            'new': new_error_map[ts]
        })

print("="*80)
print(f"🔴 REGRESSIONS (Was Correct → Now Wrong): {len(regressions)}")
print("="*80)
for i, item in enumerate(regressions, 1):
    new_shot = item['new']['detected_shot']
    gt_shot = item['new']['ground_truth_shot']
    print(f"{i}. {item['timestamp']:.1f}s - Now detects as {new_shot['outcome'].upper()} (was correct), actually {gt_shot['outcome'].upper()}")
    print(f"   Reason: {new_shot.get('outcome_reason', 'N/A')}")

print()
print("="*80)
print(f"✅ FIXES (Was Wrong → Now Correct): {len(fixes)}")
print("="*80)
for i, item in enumerate(fixes, 1):
    old_shot = item['old']['detected_shot']
    new_shot = item['new']['detected_shot']
    gt_shot = item['new']['ground_truth_shot']
    print(f"{i}. {item['timestamp']:.1f}s - Was {old_shot['outcome'].upper()}, now correctly {new_shot['outcome'].upper()}")
    print(f"   Old reason: {old_shot.get('outcome_reason', 'N/A')}")
    print(f"   New reason: {new_shot.get('outcome_reason', 'N/A')}")

print()
print("="*80)
print(f"⚠️ STILL WRONG (Was Wrong → Still Wrong): {len(still_wrong)}")
print("="*80)
for i, item in enumerate(still_wrong, 1):
    old_shot = item['old']['detected_shot']
    new_shot = item['new']['detected_shot']
    gt_shot = item['new']['ground_truth_shot']
    print(f"{i}. {item['timestamp']:.1f}s - Still wrong: {new_shot['outcome'].upper()} (actually {gt_shot['outcome'].upper()})")
    print(f"   Old reason: {old_shot.get('outcome_reason', 'N/A')}")
    print(f"   New reason: {new_shot.get('outcome_reason', 'N/A')}")

if new_only_errors:
    print()
    print("="*80)
    print(f"❓ NEW ERRORS (Not in old results): {len(new_only_errors)}")
    print("="*80)
    for i, item in enumerate(new_only_errors, 1):
        new_shot = item['new']['detected_shot']
        gt_shot = item['new']['ground_truth_shot']
        print(f"{i}. {item['timestamp']:.1f}s - {new_shot['outcome'].upper()} (actually {gt_shot['outcome'].upper()})")
        print(f"   Reason: {new_shot.get('outcome_reason', 'N/A')}")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print(f"Fixes: +{len(fixes)}")
print(f"Regressions: -{len(regressions)}")
print(f"Still wrong: {len(still_wrong)}")
print(f"Net change: {len(fixes) - len(regressions)} (expected: +{new_data['accuracy_analysis']['matched_correct'] - old_data['accuracy_analysis']['matched_correct']})")
