#!/usr/bin/env python3
"""
Basketball Shot Detection Comparison Tool

This script compares the original shot detection approach with the enhanced
trajectory analysis + multi-frame context approach.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, Any, List

def load_session_data(filename: str) -> Dict[str, Any]:
    """Load shot session data from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        return {}

def analyze_detection_accuracy(shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze detection accuracy metrics"""
    if not shots:
        return {"error": "No shot data available"}
    
    total_shots = len(shots)
    made_shots = sum(1 for shot in shots if shot['outcome'] == 'made')
    missed_shots = sum(1 for shot in shots if shot['outcome'] == 'missed')
    undetermined = sum(1 for shot in shots if shot['outcome'] == 'undetermined')
    
    # Confidence analysis
    confidences = [shot.get('shot_confidence', shot.get('enhanced_confidence', 0)) for shot in shots]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    # Overlap analysis
    overlaps = [shot.get('max_overlap_percentage', 0) for shot in shots]
    avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0
    perfect_overlaps = sum(1 for overlap in overlaps if overlap >= 100.0)
    
    return {
        "total_shots": total_shots,
        "made_shots": made_shots,
        "missed_shots": missed_shots,
        "undetermined_shots": undetermined,
        "shooting_percentage": (made_shots / (made_shots + missed_shots) * 100) if (made_shots + missed_shots) > 0 else 0,
        "average_confidence": avg_confidence,
        "average_overlap": avg_overlap,
        "perfect_overlap_count": perfect_overlaps,
        "perfect_overlap_percentage": (perfect_overlaps / total_shots * 100) if total_shots > 0 else 0
    }

def analyze_enhanced_features(shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze enhanced trajectory and context features"""
    enhanced_shots = [shot for shot in shots if 'trajectory_analysis' in shot]
    
    if not enhanced_shots:
        return {"error": "No enhanced analysis data available"}
    
    # Trajectory analysis
    direction_consistencies = [shot['trajectory_analysis'].get('direction_consistency', 0) for shot in enhanced_shots]
    upward_bounces = sum(1 for shot in enhanced_shots if shot['trajectory_analysis'].get('has_upward_bounce', False))
    clean_downward = sum(1 for shot in enhanced_shots if shot['trajectory_analysis'].get('shows_clean_downward_motion', False))
    
    # Context patterns
    context_patterns = {}
    for shot in enhanced_shots:
        if 'context_analysis' in shot and 'overall_pattern' in shot['context_analysis']:
            pattern = shot['context_analysis']['overall_pattern']
            context_patterns[pattern] = context_patterns.get(pattern, 0) + 1
    
    return {
        "enhanced_shots_count": len(enhanced_shots),
        "average_direction_consistency": sum(direction_consistencies) / len(direction_consistencies) if direction_consistencies else 0,
        "upward_bounce_detections": upward_bounces,
        "clean_downward_motions": clean_downward,
        "context_patterns": context_patterns,
        "trajectory_smoothness": sum(shot['trajectory_analysis'].get('trajectory_smoothness', 0) for shot in enhanced_shots) / len(enhanced_shots) if enhanced_shots else 0
    }

def compare_shot_decisions(original_shots: List[Dict[str, Any]], enhanced_shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare shot decisions between original and enhanced approaches"""
    # Match shots by timestamp (within 5 seconds)
    matches = []
    unmatched_original = []
    unmatched_enhanced = []
    
    for orig_shot in original_shots:
        orig_time = orig_shot.get('frame_time', 0)
        best_match = None
        min_time_diff = float('inf')
        
        for enh_shot in enhanced_shots:
            enh_time = enh_shot.get('frame_time', 0)
            time_diff = abs(orig_time - enh_time)
            
            if time_diff < 5.0 and time_diff < min_time_diff:  # Within 5 seconds
                min_time_diff = time_diff
                best_match = enh_shot
        
        if best_match:
            matches.append({
                'original': orig_shot,
                'enhanced': best_match,
                'time_difference': min_time_diff
            })
            enhanced_shots.remove(best_match)
        else:
            unmatched_original.append(orig_shot)
    
    unmatched_enhanced = enhanced_shots.copy()
    
    # Analyze decision differences
    agreement = 0
    disagreement = 0
    original_to_enhanced_changes = {"made_to_missed": 0, "missed_to_made": 0, "to_undetermined": 0, "from_undetermined": 0}
    
    for match in matches:
        orig_outcome = match['original']['outcome']
        enh_outcome = match['enhanced']['outcome']
        
        if orig_outcome == enh_outcome:
            agreement += 1
        else:
            disagreement += 1
            
            if orig_outcome == 'made' and enh_outcome == 'missed':
                original_to_enhanced_changes["made_to_missed"] += 1
            elif orig_outcome == 'missed' and enh_outcome == 'made':
                original_to_enhanced_changes["missed_to_made"] += 1
            elif enh_outcome == 'undetermined':
                original_to_enhanced_changes["to_undetermined"] += 1
            elif orig_outcome == 'undetermined':
                original_to_enhanced_changes["from_undetermined"] += 1
    
    return {
        "matched_shots": len(matches),
        "unmatched_original": len(unmatched_original),
        "unmatched_enhanced": len(unmatched_enhanced),
        "agreement": agreement,
        "disagreement": disagreement,
        "agreement_percentage": (agreement / len(matches) * 100) if matches else 0,
        "decision_changes": original_to_enhanced_changes
    }

def generate_comparison_report(original_file: str, enhanced_file: str) -> str:
    """Generate comprehensive comparison report"""
    print("Loading session data...")
    original_data = load_session_data(original_file)
    enhanced_data = load_session_data(enhanced_file)
    
    if not original_data or not enhanced_data:
        return "❌ Failed to load session data"
    
    original_shots = original_data.get('shots', [])
    enhanced_shots = enhanced_data.get('shots', [])
    
    print("Analyzing detection accuracy...")
    original_analysis = analyze_detection_accuracy(original_shots)
    enhanced_analysis = analyze_detection_accuracy(enhanced_shots)
    
    print("Analyzing enhanced features...")
    enhanced_features = analyze_enhanced_features(enhanced_shots)
    
    print("Comparing shot decisions...")
    decision_comparison = compare_shot_decisions(original_shots.copy(), enhanced_shots.copy())
    
    # Generate report
    report = f"""
BASKETBALL SHOT DETECTION COMPARISON REPORT
==========================================

ORIGINAL APPROACH ANALYSIS:
---------------------------
Total Shots: {original_analysis['total_shots']}
Made: {original_analysis['made_shots']}
Missed: {original_analysis['missed_shots']}
Undetermined: {original_analysis['undetermined_shots']}
Shooting %: {original_analysis['shooting_percentage']:.1f}%
Average Confidence: {original_analysis['average_confidence']:.3f}
Average Overlap: {original_analysis['average_overlap']:.1f}%
Perfect Overlaps: {original_analysis['perfect_overlap_count']} ({original_analysis['perfect_overlap_percentage']:.1f}%)

ENHANCED APPROACH ANALYSIS:
---------------------------
Total Shots: {enhanced_analysis['total_shots']}
Made: {enhanced_analysis['made_shots']}
Missed: {enhanced_analysis['missed_shots']}
Undetermined: {enhanced_analysis['undetermined_shots']}
Shooting %: {enhanced_analysis['shooting_percentage']:.1f}%
Average Confidence: {enhanced_analysis['average_confidence']:.3f}
Average Overlap: {enhanced_analysis['average_overlap']:.1f}%
Perfect Overlaps: {enhanced_analysis['perfect_overlap_count']} ({enhanced_analysis['perfect_overlap_percentage']:.1f}%)

ENHANCED FEATURES ANALYSIS:
---------------------------
Enhanced Shots: {enhanced_features.get('enhanced_shots_count', 0)}
Avg Direction Consistency: {enhanced_features.get('average_direction_consistency', 0):.3f}
Upward Bounce Detections: {enhanced_features.get('upward_bounce_detections', 0)}
Clean Downward Motions: {enhanced_features.get('clean_downward_motions', 0)}
Avg Trajectory Smoothness: {enhanced_features.get('trajectory_smoothness', 0):.3f}

Context Patterns:"""
    
    if 'context_patterns' in enhanced_features:
        for pattern, count in enhanced_features['context_patterns'].items():
            report += f"\n  {pattern}: {count}"
    
    report += f"""

DECISION COMPARISON:
-------------------
Matched Shots: {decision_comparison['matched_shots']}
Agreement: {decision_comparison['agreement']} ({decision_comparison['agreement_percentage']:.1f}%)
Disagreement: {decision_comparison['disagreement']}
Unmatched Original: {decision_comparison['unmatched_original']}
Unmatched Enhanced: {decision_comparison['unmatched_enhanced']}

Decision Changes:
  Made→Missed: {decision_comparison['decision_changes']['made_to_missed']}
  Missed→Made: {decision_comparison['decision_changes']['missed_to_made']}
  To Undetermined: {decision_comparison['decision_changes']['to_undetermined']}
  From Undetermined: {decision_comparison['decision_changes']['from_undetermined']}

SUMMARY:
--------"""
    
    # Calculate improvements
    shot_diff = enhanced_analysis['total_shots'] - original_analysis['total_shots']
    accuracy_diff = enhanced_analysis['shooting_percentage'] - original_analysis['shooting_percentage']
    confidence_diff = enhanced_analysis['average_confidence'] - original_analysis['average_confidence']
    
    report += f"""
Shot Detection Change: {shot_diff:+d} shots
Shooting % Change: {accuracy_diff:+.1f}%
Confidence Change: {confidence_diff:+.3f}
Agreement Rate: {decision_comparison['agreement_percentage']:.1f}%

The enhanced approach with trajectory analysis and multi-frame context
{'improved' if shot_diff >= 0 or accuracy_diff > 0 else 'changed'} shot detection compared to the original method.
"""
    
    return report

def main():
    parser = argparse.ArgumentParser(description='Compare basketball shot detection approaches')
    parser.add_argument('--original', type=str, required=True,
                       help='Path to original session JSON file')
    parser.add_argument('--enhanced', type=str, required=True,
                       help='Path to enhanced session JSON file')
    parser.add_argument('--output', type=str,
                       help='Output file for comparison report')
    
    args = parser.parse_args()
    
    # Validate input files
    original_path = Path(args.original)
    enhanced_path = Path(args.enhanced)
    
    if not original_path.exists():
        print(f"❌ Original session file not found: {original_path}")
        return
    
    if not enhanced_path.exists():
        print(f"❌ Enhanced session file not found: {enhanced_path}")
        return
    
    print("🔍 Generating comparison report...")
    report = generate_comparison_report(str(original_path), str(enhanced_path))
    
    # Output report
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"✓ Comparison report saved: {output_path}")
    else:
        print(report)

if __name__ == "__main__":
    main()