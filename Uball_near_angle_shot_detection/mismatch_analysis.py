#!/usr/bin/env python3
"""
Comprehensive analysis of shot detection mismatches.
Extracts incorrect matches with timestamps and analyzes patterns.
"""

import json
import os
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

class MismatchAnalyzer:
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.all_mismatches = []
        self.video_stats = {}
        
    def load_accuracy_data(self, video_dir: Path) -> Dict[str, Any]:
        """Load accuracy analysis JSON for a video."""
        accuracy_file = video_dir / "accuracy_analysis.json"
        if not accuracy_file.exists():
            return None
        
        try:
            with open(accuracy_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {accuracy_file}: {e}")
            return None
    
    def parse_video_name(self, video_dir: Path) -> Tuple[str, str]:
        """Extract game and angle from directory name."""
        name = video_dir.name
        # Format: "09-22(1-NL)_uuid" or "09-22(2-NR)"
        parts = name.split('(')
        if len(parts) >= 2:
            date = parts[0]
            game_angle = parts[1].split(')')[0]
            if '_' in game_angle:
                game_angle = game_angle.split('_')[0]
            return date, game_angle
        return name, "unknown"
    
    def extract_mismatches(self, video_dir: Path) -> List[Dict[str, Any]]:
        """Extract all incorrect matches for a video."""
        data = self.load_accuracy_data(video_dir)
        if not data or 'detailed_analysis' not in data:
            return []
        
        mismatches = []
        date, game_angle = self.parse_video_name(video_dir)
        detailed_analysis = data['detailed_analysis']
        
        # Extract from matched_incorrect list (wrong outcome)
        incorrect_matches = detailed_analysis.get('matched_incorrect', [])
        
        for entry in incorrect_matches:
            mismatch = {
                'video_name': video_dir.name,
                'date': date,
                'game_angle': game_angle,
                'mismatch_type': 'outcome_mismatch',
                'detected_timestamp': entry.get('detected_timestamp_seconds'),
                'detected_outcome': entry.get('detected_outcome'),
                'ground_truth_outcome': entry.get('ground_truth_outcome'),
                'detected_shot': entry.get('detected_shot', {}),
                'ground_truth_shot': entry.get('ground_truth_shot', {}),
                'start_timestamp': entry.get('start_timestamp'),
                'end_timestamp': entry.get('end_timestamp'),
            }
            
            # Extract shot classifications
            detected_classification = mismatch['detected_shot'].get('classification', 'UNKNOWN')
            gt_classification = mismatch['ground_truth_shot'].get('classification', 'UNKNOWN')
            
            mismatch['detected_classification'] = detected_classification
            mismatch['ground_truth_classification'] = gt_classification
            mismatch['outcome_reason'] = mismatch['detected_shot'].get('outcome_reason', 'unknown')
            
            mismatches.append(mismatch)
        
        # Extract false positives (detected but not in ground truth)
        false_positives = detailed_analysis.get('missing_from_ground_truth', [])
        for entry in false_positives:
            mismatch = {
                'video_name': video_dir.name,
                'date': date,
                'game_angle': game_angle,
                'mismatch_type': 'false_positive',
                'detected_timestamp': entry.get('timestamp_seconds') or entry.get('detected_timestamp_seconds'),
                'detected_outcome': entry.get('outcome'),
                'ground_truth_outcome': None,
                'detected_shot': entry if isinstance(entry, dict) else {'outcome': entry},
                'ground_truth_shot': {},
                'start_timestamp': entry.get('start_timestamp'),
                'end_timestamp': entry.get('end_timestamp'),
            }
            mismatch['detected_classification'] = mismatch['detected_shot'].get('classification', 'UNKNOWN')
            mismatch['ground_truth_classification'] = 'MISSING'
            mismatch['outcome_reason'] = mismatch['detected_shot'].get('outcome_reason', 'unknown')
            mismatches.append(mismatch)
        
        # Extract false negatives (in ground truth but not detected)
        false_negatives = detailed_analysis.get('unmatched_ground_truth', [])
        for entry in false_negatives:
            mismatch = {
                'video_name': video_dir.name,
                'date': date,
                'game_angle': game_angle,
                'mismatch_type': 'false_negative',
                'detected_timestamp': None,
                'detected_outcome': None,
                'ground_truth_outcome': entry.get('outcome'),
                'detected_shot': {},
                'ground_truth_shot': entry,
                'start_timestamp': entry.get('start_timestamp'),
                'end_timestamp': entry.get('end_timestamp'),
            }
            mismatch['detected_classification'] = 'MISSING'
            mismatch['ground_truth_classification'] = entry.get('classification', 'UNKNOWN')
            mismatch['outcome_reason'] = 'not_detected'
            mismatches.append(mismatch)
        
        return mismatches
    
    def analyze_all_videos(self) -> Dict[str, Any]:
        """Analyze all videos in results directory."""
        if not self.results_dir.exists():
            print(f"Results directory not found: {self.results_dir}")
            return {}
        
        all_mismatches = []
        video_stats = {}
        
        for video_dir in sorted(self.results_dir.iterdir()):
            if not video_dir.is_dir():
                continue
            
            mismatches = self.extract_mismatches(video_dir)
            all_mismatches.extend(mismatches)
            
            # Calculate stats for this video
            data = self.load_accuracy_data(video_dir)
            if data:
                date, game_angle = self.parse_video_name(video_dir)
                detailed_analysis = data.get('detailed_analysis', {})
                outcome_mismatches = len(detailed_analysis.get('matched_incorrect', []))
                false_positives = len(detailed_analysis.get('missing_from_ground_truth', []))
                false_negatives = len(detailed_analysis.get('unmatched_ground_truth', []))
                
                video_stats[video_dir.name] = {
                    'date': date,
                    'game_angle': game_angle,
                    'total_mismatches': len(mismatches),
                    'outcome_mismatches': outcome_mismatches,
                    'false_positives': false_positives,
                    'false_negatives': false_negatives,
                    'total_matched': data.get('accuracy_analysis', {}).get('total_detected_shots', 0),
                    'overall_accuracy': data.get('accuracy_analysis', {}).get('overall_accuracy_percentage', 0),
                }
        
        self.all_mismatches = all_mismatches
        self.video_stats = video_stats
        
        return {
            'total_mismatches': len(all_mismatches),
            'mismatches': all_mismatches,
            'video_stats': video_stats,
        }
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in incorrect matches."""
        if not self.all_mismatches:
            return {}
        
        # Mismatch type distribution
        mismatch_types = Counter()
        for m in self.all_mismatches:
            mismatch_types[m.get('mismatch_type', 'unknown')] += 1
        
        # Outcome mismatch patterns (only for outcome_mismatch type)
        outcome_patterns = Counter()
        for m in self.all_mismatches:
            if m.get('mismatch_type') == 'outcome_mismatch':
                pattern = f"{m['detected_outcome']} -> {m['ground_truth_outcome']}"
                outcome_patterns[pattern] += 1
        
        # Classification mismatch patterns
        classification_patterns = Counter()
        for m in self.all_mismatches:
            detected = m.get('detected_classification', 'UNKNOWN')
            gt = m.get('ground_truth_classification', 'UNKNOWN')
            pattern = f"{detected} -> {gt}"
            classification_patterns[pattern] += 1
        
        # Shot type analysis (for all mismatch types)
        shot_type_errors = defaultdict(int)
        for m in self.all_mismatches:
            gt_type = m.get('ground_truth_classification', 'UNKNOWN')
            if gt_type != 'MISSING':
                shot_type_errors[gt_type] += 1
            else:
                # False positive - use detected classification
                detected_type = m.get('detected_classification', 'UNKNOWN')
                if detected_type != 'UNKNOWN':
                    shot_type_errors[f"FP:{detected_type}"] = shot_type_errors.get(f"FP:{detected_type}", 0) + 1
        
        # Outcome reason analysis
        outcome_reasons = Counter()
        for m in self.all_mismatches:
            reason = m.get('outcome_reason', 'unknown')
            outcome_reasons[reason] += 1
        
        # Video-wise distribution
        video_mismatches = Counter()
        for m in self.all_mismatches:
            video_mismatches[m['video_name']] += 1
        
        # Angle-wise distribution
        angle_mismatches = Counter()
        for m in self.all_mismatches:
            angle_mismatches[m['game_angle']] += 1
        
        return {
            'mismatch_types': dict(mismatch_types),
            'outcome_patterns': dict(outcome_patterns),
            'classification_patterns': dict(classification_patterns),
            'shot_type_errors': dict(shot_type_errors),
            'outcome_reasons': dict(outcome_reasons),
            'video_distribution': dict(video_mismatches),
            'angle_distribution': dict(angle_mismatches),
        }
    
    def generate_timestamp_report(self) -> str:
        """Generate detailed timestamp report for each video."""
        report_lines = []
        
        # Group by video
        by_video = defaultdict(list)
        for m in self.all_mismatches:
            by_video[m['video_name']].append(m)
        
        report_lines.append("=" * 80)
        report_lines.append("DETAILED TIMESTAMP REPORT - INCORRECT MATCHES")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        for video_name in sorted(by_video.keys()):
            mismatches = sorted(by_video[video_name], key=lambda x: x['detected_timestamp'] or 0)
            date = mismatches[0]['date']
            game_angle = mismatches[0]['game_angle']
            
            report_lines.append(f"\n{'='*80}")
            report_lines.append(f"Video: {video_name}")
            report_lines.append(f"Date: {date} | Game/Angle: {game_angle}")
            report_lines.append(f"Total Incorrect Matches: {len(mismatches)}")
            report_lines.append(f"{'='*80}")
            report_lines.append("")
            
            for i, m in enumerate(mismatches, 1):
                timestamp = m['detected_timestamp']
                start = m.get('start_timestamp')
                end = m.get('end_timestamp')
                
                mtype = m.get('mismatch_type', 'unknown')
                mtype_name = {
                    'outcome_mismatch': 'OUTCOME MISMATCH',
                    'false_positive': 'FALSE POSITIVE',
                    'false_negative': 'FALSE NEGATIVE'
                }.get(mtype, mtype.upper())
                
                report_lines.append(f"  Mismatch #{i} [{mtype_name}]:")
                report_lines.append(f"    Timestamp: {timestamp:.2f}s" if timestamp else "    Timestamp: N/A")
                if start and end:
                    report_lines.append(f"    Time Range: {start:.2f}s - {end:.2f}s")
                
                if mtype == 'outcome_mismatch':
                    report_lines.append(f"    Detected: {m['detected_outcome']} ({m.get('detected_classification', 'UNKNOWN')})")
                    report_lines.append(f"    Ground Truth: {m['ground_truth_outcome']} ({m.get('ground_truth_classification', 'UNKNOWN')})")
                    report_lines.append(f"    Outcome Reason: {m.get('outcome_reason', 'unknown')}")
                elif mtype == 'false_positive':
                    report_lines.append(f"    Detected: {m.get('detected_outcome', 'N/A')} ({m.get('detected_classification', 'UNKNOWN')})")
                    report_lines.append(f"    Ground Truth: NOT IN GROUND TRUTH")
                    report_lines.append(f"    Outcome Reason: {m.get('outcome_reason', 'unknown')}")
                elif mtype == 'false_negative':
                    report_lines.append(f"    Detected: NOT DETECTED")
                    report_lines.append(f"    Ground Truth: {m.get('ground_truth_outcome', 'N/A')} ({m.get('ground_truth_classification', 'UNKNOWN')})")
                    if m.get('start_timestamp') and m.get('end_timestamp'):
                        report_lines.append(f"    Expected Range: {m['start_timestamp']:.2f}s - {m['end_timestamp']:.2f}s")
                
                # Add detection details
                detected_shot = m.get('detected_shot', {})
                if detected_shot and isinstance(detected_shot, dict):
                    overlap = detected_shot.get('avg_overlap_percentage', 0)
                    confidence = detected_shot.get('decision_confidence', 0)
                    entry_angle = detected_shot.get('entry_angle')
                    if overlap > 0 or confidence > 0 or entry_angle:
                        report_lines.append(f"    Detection Details:")
                        if overlap > 0:
                            report_lines.append(f"      - Avg Overlap: {overlap:.2f}%")
                        if confidence > 0:
                            report_lines.append(f"      - Decision Confidence: {confidence:.2f}")
                        if entry_angle:
                            report_lines.append(f"      - Entry Angle: {entry_angle:.2f}°")
                
                # Add ground truth note if available
                gt_shot = m.get('ground_truth_shot', {})
                if gt_shot and isinstance(gt_shot, dict) and gt_shot.get('note'):
                    report_lines.append(f"    GT Note: {gt_shot['note']}")
                
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    def generate_summary_report(self, patterns: Dict[str, Any]) -> str:
        """Generate summary statistics and pattern analysis."""
        report_lines = []
        
        report_lines.append("=" * 80)
        report_lines.append("SHOT DETECTION MISMATCH ANALYSIS - SUMMARY REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Overall statistics
        report_lines.append("OVERALL STATISTICS")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Videos Analyzed: {len(self.video_stats)}")
        report_lines.append(f"Total Incorrect Matches: {len(self.all_mismatches)}")
        report_lines.append("")
        
        # Mismatch type distribution
        report_lines.append("MISMATCH TYPE DISTRIBUTION")
        report_lines.append("-" * 80)
        for mtype, count in sorted(patterns.get('mismatch_types', {}).items(), key=lambda x: x[1], reverse=True):
            mtype_name = {
                'outcome_mismatch': 'Wrong Outcome (Made/Missed)',
                'false_positive': 'False Positive (Detected but not in GT)',
                'false_negative': 'False Negative (In GT but not detected)'
            }.get(mtype, mtype)
            report_lines.append(f"  {mtype_name:<40} {count:>5} times")
        report_lines.append("")
        
        # Video-wise statistics
        report_lines.append("VIDEO-WISE STATISTICS")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Video':<50} {'Mismatches':<15} {'Accuracy':<15}")
        report_lines.append("-" * 80)
        for video_name, stats in sorted(self.video_stats.items()):
            mismatches = stats['total_mismatches']
            accuracy = stats['overall_accuracy']
            report_lines.append(f"{video_name:<50} {mismatches:<15} {accuracy:.2f}%")
        report_lines.append("")
        
        # Outcome mismatch patterns
        report_lines.append("OUTCOME MISMATCH PATTERNS")
        report_lines.append("-" * 80)
        for pattern, count in sorted(patterns.get('outcome_patterns', {}).items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {pattern:<30} {count:>5} times")
        report_lines.append("")
        
        # Shot type error analysis
        report_lines.append("SHOT TYPE ERROR ANALYSIS (Ground Truth Classification)")
        report_lines.append("-" * 80)
        for shot_type, count in sorted(patterns.get('shot_type_errors', {}).items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {shot_type:<30} {count:>5} errors")
        report_lines.append("")
        
        # Classification mismatch patterns
        report_lines.append("CLASSIFICATION MISMATCH PATTERNS")
        report_lines.append("-" * 80)
        for pattern, count in sorted(patterns.get('classification_patterns', {}).items(), key=lambda x: x[1], reverse=True)[:10]:
            report_lines.append(f"  {pattern:<50} {count:>5} times")
        report_lines.append("")
        
        # Outcome reason analysis
        report_lines.append("DETECTION OUTCOME REASONS (Why did detection fail?)")
        report_lines.append("-" * 80)
        for reason, count in sorted(patterns.get('outcome_reasons', {}).items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {reason:<40} {count:>5} times")
        report_lines.append("")
        
        # Angle distribution
        report_lines.append("ANGLE-WISE ERROR DISTRIBUTION")
        report_lines.append("-" * 80)
        for angle, count in sorted(patterns.get('angle_distribution', {}).items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {angle:<30} {count:>5} errors")
        report_lines.append("")
        
        return "\n".join(report_lines)
    
    def generate_recommendations(self, patterns: Dict[str, Any]) -> str:
        """Generate recommendations based on analysis."""
        report_lines = []
        
        report_lines.append("=" * 80)
        report_lines.append("RECOMMENDATIONS FOR IMPROVEMENT")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Analyze mismatch types
        mismatch_types = patterns.get('mismatch_types', {})
        outcome_mismatches = mismatch_types.get('outcome_mismatch', 0)
        false_positives = mismatch_types.get('false_positive', 0)
        false_negatives = mismatch_types.get('false_negative', 0)
        
        report_lines.append("KEY FINDINGS:")
        report_lines.append("-" * 80)
        report_lines.append(f"1. Outcome Mismatches (Wrong Made/Missed): {outcome_mismatches}")
        report_lines.append(f"2. False Positives (Detected but not in GT): {false_positives}")
        report_lines.append(f"3. False Negatives (In GT but not detected): {false_negatives}")
        report_lines.append("")
        
        # Analyze outcome patterns
        outcome_patterns = patterns.get('outcome_patterns', {})
        made_as_missed = outcome_patterns.get('made -> missed', 0)
        missed_as_made = outcome_patterns.get('missed -> made', 0)
        
        report_lines.append("OUTCOME MISMATCH ANALYSIS:")
        report_lines.append("-" * 80)
        
        if made_as_missed > 0:
            report_lines.append(f"  • Made shots incorrectly detected as missed: {made_as_missed}")
            report_lines.append("    - Overlap detection may be too strict")
            report_lines.append("    - Consider lowering thresholds for perfect_overlap classification")
            report_lines.append("    - Review shots with insufficient_overlap reason")
            report_lines.append("")
        
        if missed_as_made > 0:
            report_lines.append(f"  • Missed shots incorrectly detected as made: {missed_as_made}")
            report_lines.append("    - Overlap detection may be too lenient")
            report_lines.append("    - Consider tightening thresholds for overlap classification")
            report_lines.append("    - Pay special attention to rim bounces and steep entry angles")
            report_lines.append("    - Review shots with perfect_overlap_steep_entry reason")
            report_lines.append("")
        
        # False positive analysis
        if false_positives > 0:
            report_lines.append("FALSE POSITIVE ANALYSIS:")
            report_lines.append("-" * 80)
            report_lines.append(f"  • False positives detected: {false_positives}")
            report_lines.append("    - System is detecting shots that don't exist in ground truth")
            report_lines.append("    - These may be:")
            report_lines.append("      * Ball movements near hoop that aren't actual shots")
            report_lines.append("      * Noise in ball detection")
            report_lines.append("      * Incorrect hoop detection triggering shot detection")
            report_lines.append("    - Recommendations:")
            report_lines.append("      * Improve shot validation logic")
            report_lines.append("      * Add stricter pre-detection filters")
            report_lines.append("      * Review timestamp ranges for false positives")
            report_lines.append("")
        
        # False negative analysis
        if false_negatives > 0:
            report_lines.append("FALSE NEGATIVE ANALYSIS:")
            report_lines.append("-" * 80)
            report_lines.append(f"  • False negatives detected: {false_negatives}")
            report_lines.append("    - System is missing shots that exist in ground truth")
            report_lines.append("    - These may be:")
            report_lines.append("      * Shots with low overlap that should be detected")
            report_lines.append("      * Fast shots that pass through detection window")
            report_lines.append("      * Shots with unusual trajectories")
            report_lines.append("    - Recommendations:")
            report_lines.append("      * Lower detection thresholds")
            report_lines.append("      * Improve ball tracking for fast shots")
            report_lines.append("      * Expand detection time windows")
            report_lines.append("      * Review missed shot patterns in timestamp report")
            report_lines.append("")
        
        # Shot type analysis
        shot_type_errors = patterns.get('shot_type_errors', {})
        if shot_type_errors:
            sorted_errors = sorted(shot_type_errors.items(), key=lambda x: x[1], reverse=True)
            report_lines.append("SHOT TYPE ERROR ANALYSIS:")
            report_lines.append("-" * 80)
            report_lines.append(f"  • Most error-prone shot types:")
            for i, (shot_type, count) in enumerate(sorted_errors[:5], 1):
                report_lines.append(f"    {i}. {shot_type}: {count} errors")
            report_lines.append("  - Focus manual review on these shot types")
            report_lines.append("  - Consider shot-type-specific threshold adjustments")
            report_lines.append("")
        
        # Outcome reason analysis
        outcome_reasons = patterns.get('outcome_reasons', {})
        if outcome_reasons:
            sorted_reasons = sorted(outcome_reasons.items(), key=lambda x: x[1], reverse=True)
            report_lines.append("DETECTION FAILURE REASON ANALYSIS:")
            report_lines.append("-" * 80)
            report_lines.append("  • Most common failure reasons:")
            for i, (reason, count) in enumerate(sorted_reasons[:5], 1):
                report_lines.append(f"    {i}. {reason}: {count} times")
            report_lines.append("  - This indicates where the detection logic needs refinement")
            report_lines.append("  - Prioritize improvements based on frequency")
            report_lines.append("")
        
        # Angle-specific recommendations
        angle_distribution = patterns.get('angle_distribution', {})
        if angle_distribution:
            sorted_angles = sorted(angle_distribution.items(), key=lambda x: x[1], reverse=True)
            report_lines.append("ANGLE-SPECIFIC ANALYSIS:")
            report_lines.append("-" * 80)
            report_lines.append("  • Angles with most errors:")
            for i, (angle, count) in enumerate(sorted_angles[:3], 1):
                report_lines.append(f"    {i}. {angle}: {count} errors")
            report_lines.append("  - Consider angle-specific calibration or thresholds")
            report_lines.append("  - Review camera angle setup for problematic angles")
            report_lines.append("")
        
        report_lines.append("GENERAL RECOMMENDATIONS:")
        report_lines.append("-" * 80)
        report_lines.append("1. Manual Review:")
        report_lines.append("   - Use the timestamp report to manually review each mismatch")
        report_lines.append("   - Pay special attention to high-frequency error patterns")
        report_lines.append("   - Verify ground truth annotations for questionable cases")
        report_lines.append("")
        report_lines.append("2. Threshold Tuning:")
        report_lines.append("   - Adjust overlap thresholds based on shot type patterns")
        report_lines.append("   - Consider different thresholds for made vs missed detection")
        report_lines.append("   - Test threshold changes on subset of videos before full deployment")
        report_lines.append("")
        report_lines.append("3. Entry Angle Analysis:")
        report_lines.append("   - Review entry angles for missed shots detected as made")
        report_lines.append("   - Improve steep entry angle handling")
        report_lines.append("   - Add angle-based validation rules")
        report_lines.append("")
        report_lines.append("4. Rim Bounce Detection:")
        report_lines.append("   - Improve rim bounce detection to reduce false positives")
        report_lines.append("   - Use rim bounce as strong indicator of missed shot")
        report_lines.append("   - Enhance bounce detection with trajectory analysis")
        report_lines.append("")
        report_lines.append("5. Post-Hoop Analysis:")
        report_lines.append("   - Enhance post-hoop movement analysis for better accuracy")
        report_lines.append("   - Use ball trajectory after hoop as validation signal")
        report_lines.append("   - Improve consistency scoring for downward movement")
        report_lines.append("")
        report_lines.append("6. Detection Validation:")
        report_lines.append("   - Add pre-detection filters to reduce false positives")
        report_lines.append("   - Improve shot validation logic before final classification")
        report_lines.append("   - Consider multi-frame consistency requirements")
        report_lines.append("")
        report_lines.append("7. Coverage Improvement:")
        report_lines.append("   - Expand detection time windows for fast shots")
        report_lines.append("   - Improve ball tracking for shots with low visibility")
        report_lines.append("   - Add recovery mechanisms for missed detections")
        report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_results(self, output_file: str = "mismatch_analysis_report.txt"):
        """Generate and save comprehensive report."""
        print("Analyzing all videos...")
        self.analyze_all_videos()
        
        print(f"Found {len(self.all_mismatches)} total mismatches")
        print("Analyzing patterns...")
        patterns = self.analyze_patterns()
        
        print("Generating reports...")
        report_parts = [
            self.generate_summary_report(patterns),
            self.generate_timestamp_report(),
            self.generate_recommendations(patterns),
        ]
        
        full_report = "\n\n".join(report_parts)
        
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            f.write(full_report)
        
        print(f"\nReport saved to: {output_path.absolute()}")
        print(f"Total mismatches analyzed: {len(self.all_mismatches)}")
        
        # Also save JSON for programmatic access
        json_output = output_path.with_suffix('.json')
        json_data = {
            'total_mismatches': len(self.all_mismatches),
            'mismatches': self.all_mismatches,
            'patterns': patterns,
            'video_stats': self.video_stats,
        }
        with open(json_output, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"JSON data saved to: {json_output.absolute()}")
        
        return full_report

if __name__ == "__main__":
    analyzer = MismatchAnalyzer()
    report = analyzer.save_results("MISMATCH_ANALYSIS_REPORT.txt")
    print("\n" + "="*80)
    print("Analysis complete! Check the report file for detailed findings.")
    print("="*80)

