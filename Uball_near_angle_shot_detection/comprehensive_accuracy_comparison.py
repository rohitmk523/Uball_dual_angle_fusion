import json
import os
from pathlib import Path

# Find all accuracy_analysis.json files
results_dir = Path('results')
all_results = {}

for result_folder in results_dir.iterdir():
    if result_folder.is_dir():
        accuracy_file = result_folder / 'accuracy_analysis.json'
        if accuracy_file.exists():
            with open(accuracy_file) as f:
                data = json.load(f)

            folder_name = result_folder.name
            # Extract dataset name (e.g., "09-22(1-NL)")
            # Remove UUID suffix if present
            if '_' in folder_name:
                dataset = folder_name.split('_')[0]
                run_id = folder_name.split('_')[1]
            else:
                dataset = folder_name
                run_id = 'old'

            if dataset not in all_results:
                all_results[dataset] = {}

            all_results[dataset][run_id] = {
                'matched_correct': data['accuracy_analysis']['matched_correct'],
                'matched_incorrect': data['accuracy_analysis']['matched_incorrect'],
                'matched_shots_accuracy': data['accuracy_analysis']['matched_shots_accuracy'],
                'total_shots': data['detection_summary']['total_shots'],
                'made_shots': data['detection_summary']['made_shots'],
                'missed_shots': data['detection_summary']['missed_shots']
            }

# Print comprehensive comparison
print("=" * 100)
print("COMPREHENSIVE ACCURACY COMPARISON: OLD vs NEW (CURRENT)")
print("=" * 100)

dataset_order = sorted(all_results.keys())

print("\n{:<20} {:<15} {:<15} {:<15} {:<12}".format(
    "Dataset", "Old Accuracy", "New Accuracy", "Change", "Status"
))
print("-" * 100)

total_old_correct = 0
total_old_incorrect = 0
total_new_correct = 0
total_new_incorrect = 0

improvements = []
regressions = []
no_comparison = []

for dataset in dataset_order:
    runs = all_results[dataset]

    if 'old' in runs and len(runs) > 1:
        # Find the most recent new run (not 'old')
        new_run_id = [k for k in runs.keys() if k != 'old'][0]

        old_acc = runs['old']['matched_shots_accuracy']
        new_acc = runs[new_run_id]['matched_shots_accuracy']
        change = new_acc - old_acc

        old_correct = runs['old']['matched_correct']
        old_incorrect = runs['old']['matched_incorrect']
        new_correct = runs[new_run_id]['matched_correct']
        new_incorrect = runs[new_run_id]['matched_incorrect']

        total_old_correct += old_correct
        total_old_incorrect += old_incorrect
        total_new_correct += new_correct
        total_new_incorrect += new_incorrect

        if change > 0:
            status = "✅ IMPROVED"
            improvements.append((dataset, change))
        elif change < 0:
            status = "❌ REGRESSED"
            regressions.append((dataset, change))
        else:
            status = "➡️  SAME"

        print("{:<20} {:<15.2f} {:<15.2f} {:<15.2f} {:<12}".format(
            dataset, old_acc, new_acc, change, status
        ))
        print(" " * 20 + f"({old_correct}✓/{old_incorrect}✗) → ({new_correct}✓/{new_incorrect}✗)")
    else:
        no_comparison.append(dataset)
        if 'old' in runs:
            acc = runs['old']['matched_shots_accuracy']
            print("{:<20} {:<15.2f} {:<15} {:<15} {:<12}".format(
                dataset, acc, "N/A", "N/A", "OLD ONLY"
            ))
        else:
            # Only new run
            new_run_id = list(runs.keys())[0]
            acc = runs[new_run_id]['matched_shots_accuracy']
            print("{:<20} {:<15} {:<15.2f} {:<15} {:<12}".format(
                dataset, "N/A", acc, "N/A", "NEW ONLY"
            ))

print("-" * 100)

# Calculate overall accuracy
if total_old_correct + total_old_incorrect > 0:
    overall_old_acc = (total_old_correct / (total_old_correct + total_old_incorrect)) * 100
else:
    overall_old_acc = 0

if total_new_correct + total_new_incorrect > 0:
    overall_new_acc = (total_new_correct / (total_new_correct + total_new_incorrect)) * 100
else:
    overall_new_acc = 0

overall_change = overall_new_acc - overall_old_acc

print("\n{:<20} {:<15.2f} {:<15.2f} {:<15.2f}".format(
    "OVERALL", overall_old_acc, overall_new_acc, overall_change
))
print(" " * 20 + f"({total_old_correct}✓/{total_old_incorrect}✗) → ({total_new_correct}✓/{total_new_incorrect}✗)")

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"Datasets with improvements: {len(improvements)}")
for ds, change in sorted(improvements, key=lambda x: x[1], reverse=True):
    print(f"  ✅ {ds}: +{change:.2f}%")

print(f"\nDatasets with regressions: {len(regressions)}")
for ds, change in sorted(regressions, key=lambda x: x[1]):
    print(f"  ❌ {ds}: {change:.2f}%")

print(f"\nDatasets without comparison: {len(no_comparison)}")
for ds in no_comparison:
    print(f"  ℹ️  {ds}")

print("\n" + "=" * 100)
print("RECOMMENDATION")
print("=" * 100)

if overall_change > 0:
    print(f"✅ OVERALL IMPROVEMENT: +{overall_change:.2f}%")
    print("   The changes have improved overall accuracy across all datasets.")
    if len(regressions) > 0:
        print(f"   However, {len(regressions)} dataset(s) regressed. Consider investigating specific cases.")
elif overall_change < 0:
    print(f"❌ OVERALL REGRESSION: {overall_change:.2f}%")
    print("   The changes have decreased overall accuracy across all datasets.")
    print("   RECOMMENDATION: Consider reverting to previous version.")
else:
    print("➡️  NO CHANGE: Overall accuracy unchanged.")
    print("   The changes neither improved nor regressed overall accuracy.")
