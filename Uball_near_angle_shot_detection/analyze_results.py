#!/usr/bin/env python3
"""
Script to analyze all result JSON files and generate comprehensive accuracy report
"""
import json
import os
from pathlib import Path
from collections import defaultdict
import statistics

def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_all_results():
    """Analyze all result directories and extract metrics"""
    results_dir = Path('results')
    all_sessions = []

    for session_dir in sorted(results_dir.iterdir()):
        if not session_dir.is_dir() or session_dir.name.startswith('.'):
            continue

        # Extract angle info from directory name
        dir_name = session_dir.name
        angle_info = dir_name.split('_')[0]  # e.g., "09-22(1-NL)"

        try:
            # Load all JSON files
            accuracy_file = session_dir / 'accuracy_analysis.json'
            summary_file = session_dir / 'session_summary.json'

            if not accuracy_file.exists() or not summary_file.exists():
                continue

            accuracy_data = load_json(accuracy_file)
            summary_data = load_json(summary_file)

            session_info = {
                'name': angle_info,
                'uuid': session_dir.name,
                'video_path': summary_data['session_info'].get('video_path', 'N/A'),
                'accuracy_data': accuracy_data,
                'summary_data': summary_data
            }
            all_sessions.append(session_info)

        except Exception as e:
            print(f"Error processing {session_dir.name}: {e}")
            continue

    return all_sessions

def extract_key_metrics(sessions):
    """Extract key metrics from all sessions"""
    metrics = {
        'matched_shots_accuracy': [],
        'overall_accuracy': [],
        'ground_truth_coverage': [],
        'detection_coverage': [],
        'total_detected_shots': [],
        'total_ground_truth_shots': [],
        'matched_correct': [],
        'matched_incorrect': [],
        'missing_from_ground_truth': [],
    }

    for session in sessions:
        acc = session['accuracy_data']['accuracy_analysis']
        metrics['matched_shots_accuracy'].append(acc['matched_shots_accuracy'])
        metrics['overall_accuracy'].append(acc['overall_accuracy_percentage'])
        metrics['ground_truth_coverage'].append(acc['ground_truth_coverage'])

        ts_match = session['accuracy_data']['timestamp_matching']
        metrics['detection_coverage'].append(ts_match['detection_coverage'])

        metrics['total_detected_shots'].append(acc['total_detected_shots'])
        metrics['total_ground_truth_shots'].append(
            session['accuracy_data']['ground_truth_summary']['total_shots']
        )
        metrics['matched_correct'].append(acc['matched_correct'])
        metrics['matched_incorrect'].append(acc['matched_incorrect'])
        metrics['missing_from_ground_truth'].append(acc['missing_from_ground_truth'])

    return metrics

def analyze_mismatches(sessions):
    """Analyze patterns in mismatched shots"""
    matched_incorrect_patterns = []
    missing_shots_patterns = []

    for session in sessions:
        acc_data = session['accuracy_data']

        # Analyze matched incorrect
        if 'detailed_analysis' in acc_data and 'matched_incorrect' in acc_data['detailed_analysis']:
            for mismatch in acc_data['detailed_analysis']['matched_incorrect']:
                pattern = {
                    'session': session['name'],
                    'detected_outcome': mismatch.get('detected_outcome'),
                    'ground_truth_outcome': mismatch.get('ground_truth_outcome'),
                    'detected_timestamp': mismatch.get('detected_timestamp_seconds'),
                    'ground_truth_timestamp': mismatch['ground_truth_shot'].get('timestamp_seconds'),
                    'outcome_reason': mismatch.get('detected_shot', {}).get('outcome_reason'),
                    'entry_angle': mismatch.get('detected_shot', {}).get('entry_angle'),
                    'max_overlap': mismatch.get('detected_shot', {}).get('max_overlap_percentage'),
                }
                matched_incorrect_patterns.append(pattern)

        # Analyze missing shots
        if 'detailed_analysis' in acc_data and 'missing_from_ground_truth' in acc_data['detailed_analysis']:
            for missing in acc_data['detailed_analysis']['missing_from_ground_truth']:
                pattern = {
                    'session': session['name'],
                    'timestamp': missing.get('timestamp_seconds'),
                    'outcome': missing.get('outcome'),
                    'outcome_reason': missing.get('outcome_reason'),
                    'entry_angle': missing.get('entry_angle'),
                    'max_overlap': missing.get('max_overlap_percentage'),
                    'detection_confidence': missing.get('detection_confidence'),
                }
                missing_shots_patterns.append(pattern)

    return matched_incorrect_patterns, missing_shots_patterns

def generate_report(sessions, metrics, matched_incorrect_patterns, missing_shots_patterns):
    """Generate comprehensive report"""

    # Calculate aggregates
    total_detected = sum(metrics['total_detected_shots'])
    total_ground_truth = sum(metrics['total_ground_truth_shots'])
    total_matched_correct = sum(metrics['matched_correct'])
    total_matched_incorrect = sum(metrics['matched_incorrect'])
    total_missing = sum(metrics['missing_from_ground_truth'])

    avg_matched_accuracy = statistics.mean(metrics['matched_shots_accuracy'])
    avg_overall_accuracy = statistics.mean(metrics['overall_accuracy'])
    avg_gt_coverage = statistics.mean(metrics['ground_truth_coverage'])
    avg_detection_coverage = statistics.mean(metrics['detection_coverage'])

    report = {
        'executive_summary': {
            'total_test_sessions': len(sessions),
            'total_detected_shots': total_detected,
            'total_ground_truth_shots': total_ground_truth,
            'total_matched_correct': total_matched_correct,
            'total_matched_incorrect': total_matched_incorrect,
            'total_false_positives': total_missing,
            'average_matched_shots_accuracy': round(avg_matched_accuracy, 2),
            'average_overall_accuracy': round(avg_overall_accuracy, 2),
            'average_ground_truth_coverage': round(avg_gt_coverage, 2),
            'average_detection_coverage': round(avg_detection_coverage, 2),
        },
        'per_session_results': [],
        'angle_breakdown': {},
        'error_analysis': {
            'matched_incorrect_count': len(matched_incorrect_patterns),
            'false_positives_count': len(missing_shots_patterns),
            'matched_incorrect_patterns': matched_incorrect_patterns,
            'false_positive_patterns': missing_shots_patterns,
        },
        'statistical_summary': {
            'matched_shots_accuracy': {
                'mean': round(avg_matched_accuracy, 2),
                'median': round(statistics.median(metrics['matched_shots_accuracy']), 2),
                'stdev': round(statistics.stdev(metrics['matched_shots_accuracy']), 2),
                'min': round(min(metrics['matched_shots_accuracy']), 2),
                'max': round(max(metrics['matched_shots_accuracy']), 2),
            },
            'overall_accuracy': {
                'mean': round(avg_overall_accuracy, 2),
                'median': round(statistics.median(metrics['overall_accuracy']), 2),
                'stdev': round(statistics.stdev(metrics['overall_accuracy']), 2),
                'min': round(min(metrics['overall_accuracy']), 2),
                'max': round(max(metrics['overall_accuracy']), 2),
            }
        }
    }

    # Per session results
    for session in sessions:
        acc = session['accuracy_data']['accuracy_analysis']
        session_result = {
            'session_name': session['name'],
            'video_path': session['video_path'],
            'detected_shots': acc['total_detected_shots'],
            'ground_truth_shots': session['accuracy_data']['ground_truth_summary']['total_shots'],
            'matched_correct': acc['matched_correct'],
            'matched_incorrect': acc['matched_incorrect'],
            'false_positives': acc['missing_from_ground_truth'],
            'matched_shots_accuracy': round(acc['matched_shots_accuracy'], 2),
            'overall_accuracy': round(acc['overall_accuracy_percentage'], 2),
            'ground_truth_coverage': round(acc['ground_truth_coverage'], 2),
        }
        report['per_session_results'].append(session_result)

    # Angle breakdown (NL vs NR)
    nl_metrics = {'matched_accuracy': [], 'overall_accuracy': []}
    nr_metrics = {'matched_accuracy': [], 'overall_accuracy': []}

    for session in sessions:
        acc = session['accuracy_data']['accuracy_analysis']
        if 'NL' in session['name']:
            nl_metrics['matched_accuracy'].append(acc['matched_shots_accuracy'])
            nl_metrics['overall_accuracy'].append(acc['overall_accuracy_percentage'])
        elif 'NR' in session['name']:
            nr_metrics['matched_accuracy'].append(acc['matched_shots_accuracy'])
            nr_metrics['overall_accuracy'].append(acc['overall_accuracy_percentage'])

    if nl_metrics['matched_accuracy']:
        report['angle_breakdown']['near_left'] = {
            'session_count': len(nl_metrics['matched_accuracy']),
            'avg_matched_shots_accuracy': round(statistics.mean(nl_metrics['matched_accuracy']), 2),
            'avg_overall_accuracy': round(statistics.mean(nl_metrics['overall_accuracy']), 2),
        }

    if nr_metrics['matched_accuracy']:
        report['angle_breakdown']['near_right'] = {
            'session_count': len(nr_metrics['matched_accuracy']),
            'avg_matched_shots_accuracy': round(statistics.mean(nr_metrics['matched_accuracy']), 2),
            'avg_overall_accuracy': round(statistics.mean(nr_metrics['overall_accuracy']), 2),
        }

    return report

def main():
    print("Analyzing all result files...")
    sessions = analyze_all_results()
    print(f"Found {len(sessions)} test sessions")

    print("Extracting metrics...")
    metrics = extract_key_metrics(sessions)

    print("Analyzing error patterns...")
    matched_incorrect_patterns, missing_shots_patterns = analyze_mismatches(sessions)

    print("Generating comprehensive report...")
    report = generate_report(sessions, metrics, matched_incorrect_patterns, missing_shots_patterns)

    # Save report
    output_file = 'comprehensive_accuracy_report.json'
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {output_file}")

    # Print summary
    print("\n=== EXECUTIVE SUMMARY ===")
    print(f"Total Test Sessions: {report['executive_summary']['total_test_sessions']}")
    print(f"Total Detected Shots: {report['executive_summary']['total_detected_shots']}")
    print(f"Total Ground Truth Shots: {report['executive_summary']['total_ground_truth_shots']}")
    print(f"Total Matched Correct: {report['executive_summary']['total_matched_correct']}")
    print(f"Total Matched Incorrect: {report['executive_summary']['total_matched_incorrect']}")
    print(f"Total False Positives: {report['executive_summary']['total_false_positives']}")
    print(f"\nAverage Matched Shots Accuracy: {report['executive_summary']['average_matched_shots_accuracy']}%")
    print(f"Average Overall Accuracy: {report['executive_summary']['average_overall_accuracy']}%")
    print(f"Average Ground Truth Coverage: {report['executive_summary']['average_ground_truth_coverage']}%")
    print(f"Average Detection Coverage: {report['executive_summary']['average_detection_coverage']}%")

if __name__ == '__main__':
    main()
