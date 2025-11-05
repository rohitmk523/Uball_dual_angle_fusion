#!/usr/bin/env python3
"""
Test Enhanced Shot Detection System

This script helps test and compare the improved shot detection algorithm
against previous results.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

def load_session_data(json_path):
    """Load session data from JSON file"""
    with open(json_path, 'r') as f:
        return json.load(f)

def compare_sessions(old_session, new_session):
    """Compare two detection sessions"""
    
    old_shots = old_session.get('shots', [])
    new_shots = new_session.get('shots', [])
    
    old_stats = old_session.get('statistics', {})
    new_stats = new_session.get('statistics', {})
    
    print("="*80)
    print("SESSION COMPARISON")
    print("="*80)
    
    print(f"\n📊 OVERALL STATISTICS")
    print(f"{'Metric':<30} {'Old':<15} {'New':<15} {'Change':<15}")
    print("-"*80)
    
    total_old = old_stats.get('total_shots', 0)
    total_new = new_stats.get('total_shots', 0)
    print(f"{'Total Shots':<30} {total_old:<15} {total_new:<15} {total_new - total_old:+d}")
    
    made_old = old_stats.get('made_shots', 0)
    made_new = new_stats.get('made_shots', 0)
    print(f"{'Made Shots':<30} {made_old:<15} {made_new:<15} {made_new - made_old:+d}")
    
    missed_old = old_stats.get('missed_shots', 0)
    missed_new = new_stats.get('missed_shots', 0)
    print(f"{'Missed Shots':<30} {missed_old:<15} {missed_new:<15} {missed_new - missed_old:+d}")
    
    # Shooting percentage
    pct_old = (made_old / total_old * 100) if total_old > 0 else 0
    pct_new = (made_new / total_new * 100) if total_new > 0 else 0
    print(f"{'Shooting %':<30} {pct_old:.1f}%{'':<10} {pct_new:.1f}%{'':<10} {pct_new - pct_old:+.1f}%")
    
    print(f"\n🔍 OUTCOME CHANGES")
    print("-"*80)
    
    # Match shots by timestamp
    matched_different = []
    matched_same = []
    new_only = []
    old_only = []
    
    # Simple timestamp matching (±2 seconds)
    for new_shot in new_shots:
        new_ts = new_shot.get('timestamp_seconds', 0)
        new_outcome = new_shot.get('outcome', '')
        
        matched = False
        for old_shot in old_shots:
            old_ts = old_shot.get('timestamp_seconds', 0)
            old_outcome = old_shot.get('outcome', '')
            
            if abs(new_ts - old_ts) <= 2.0:
                matched = True
                if old_outcome != new_outcome:
                    matched_different.append({
                        'timestamp': new_ts,
                        'old_outcome': old_outcome,
                        'new_outcome': new_outcome,
                        'old_reason': old_shot.get('outcome_reason', 'N/A'),
                        'new_reason': new_shot.get('outcome_reason', 'N/A'),
                        'new_confidence': new_shot.get('decision_confidence', 0),
                        'entry_angle': new_shot.get('entry_angle'),
                        'rim_bounce_conf': new_shot.get('rim_bounce_confidence', 0)
                    })
                else:
                    matched_same.append(new_ts)
                break
        
        if not matched:
            new_only.append({
                'timestamp': new_ts,
                'outcome': new_outcome,
                'reason': new_shot.get('outcome_reason', 'N/A')
            })
    
    # Find shots only in old
    for old_shot in old_shots:
        old_ts = old_shot.get('timestamp_seconds', 0)
        matched = any(abs(new_shot.get('timestamp_seconds', 0) - old_ts) <= 2.0 for new_shot in new_shots)
        if not matched:
            old_only.append({
                'timestamp': old_ts,
                'outcome': old_shot.get('outcome', ''),
                'reason': old_shot.get('outcome_reason', 'N/A')
            })
    
    print(f"\nMatched (Same Outcome): {len(matched_same)}")
    print(f"Matched (Different Outcome): {len(matched_different)}")
    print(f"New Detections Only: {len(new_only)}")
    print(f"Old Detections Only: {len(old_only)}")
    
    if matched_different:
        print(f"\n📝 OUTCOME CHANGES ({len(matched_different)} shots)")
        print("-"*80)
        for i, change in enumerate(matched_different[:10], 1):  # Show first 10
            print(f"\n{i}. Time: {change['timestamp']:.1f}s")
            print(f"   Old: {change['old_outcome']:<7} ({change['old_reason']})")
            print(f"   New: {change['new_outcome']:<7} ({change['new_reason']})")
            print(f"   Confidence: {change['new_confidence']:.2f}")
            if change['entry_angle'] is not None:
                print(f"   Entry Angle: {change['entry_angle']:.1f}°")
            print(f"   Rim Bounce: {change['rim_bounce_conf']:.2f}")
        
        if len(matched_different) > 10:
            print(f"\n   ... and {len(matched_different) - 10} more")
    
    if new_only:
        print(f"\n🆕 NEW DETECTIONS ({len(new_only)} shots)")
        print("-"*80)
        for i, shot in enumerate(new_only[:5], 1):
            print(f"{i}. Time: {shot['timestamp']:.1f}s - {shot['outcome']} ({shot['reason']})")
        if len(new_only) > 5:
            print(f"   ... and {len(new_only) - 5} more")
    
    if old_only:
        print(f"\n❌ REMOVED DETECTIONS ({len(old_only)} shots)")
        print("-"*80)
        for i, shot in enumerate(old_only[:5], 1):
            print(f"{i}. Time: {shot['timestamp']:.1f}s - {shot['outcome']} ({shot['reason']})")
        if len(old_only) > 5:
            print(f"   ... and {len(old_only) - 5} more")
    
    print("\n" + "="*80)
    
    return {
        'matched_same': len(matched_same),
        'matched_different': len(matched_different),
        'new_only': len(new_only),
        'old_only': len(old_only),
        'outcome_changes': matched_different
    }

def analyze_enhanced_features(session_data):
    """Analyze the enhanced detection features"""
    
    shots = session_data.get('shots', [])
    
    if not shots:
        print("No shots found in session")
        return
    
    # Check if enhanced features are present
    sample_shot = shots[0]
    has_enhanced = 'entry_angle' in sample_shot
    
    if not has_enhanced:
        print("⚠️ This session does not contain enhanced features")
        return
    
    print("\n" + "="*80)
    print("ENHANCED FEATURES ANALYSIS")
    print("="*80)
    
    # Analyze entry angles
    entry_angles = [s.get('entry_angle') for s in shots if s.get('entry_angle') is not None]
    if entry_angles:
        avg_entry = sum(entry_angles) / len(entry_angles)
        print(f"\n📐 ENTRY ANGLE STATISTICS")
        print(f"   Average: {avg_entry:.1f}°")
        print(f"   Min: {min(entry_angles):.1f}°")
        print(f"   Max: {max(entry_angles):.1f}°")
        
        steep_entries = sum(1 for a in entry_angles if a >= 45)
        print(f"   Steep entries (≥45°): {steep_entries} ({steep_entries/len(entry_angles)*100:.1f}%)")
    
    # Analyze rim bounce detection
    rim_bounces = [s for s in shots if s.get('is_rim_bounce', False)]
    print(f"\n🏀 RIM BOUNCE DETECTION")
    print(f"   Detected: {len(rim_bounces)} shots")
    
    if rim_bounces:
        avg_bounce_conf = sum(s.get('rim_bounce_confidence', 0) for s in rim_bounces) / len(rim_bounces)
        print(f"   Average confidence: {avg_bounce_conf:.2f}")
        
        # Breakdown by outcome
        made_with_bounce = sum(1 for s in rim_bounces if s.get('outcome') == 'made')
        missed_with_bounce = sum(1 for s in rim_bounces if s.get('outcome') == 'missed')
        print(f"   Classified as made: {made_with_bounce}")
        print(f"   Classified as missed: {missed_with_bounce}")
    
    # Analyze weighted scores
    weighted_scores = [s.get('weighted_overlap_score', 0) for s in shots]
    if weighted_scores:
        print(f"\n📊 WEIGHTED OVERLAP SCORES")
        print(f"   Average: {sum(weighted_scores)/len(weighted_scores):.2f}")
        print(f"   High quality (≥4.0): {sum(1 for s in weighted_scores if s >= 4.0)}")
        print(f"   Fast swoosh range (3.0-4.0): {sum(1 for s in weighted_scores if 3.0 <= s < 4.0)}")
    
    # Analyze decision confidence
    decision_confidences = [s.get('decision_confidence', 0) for s in shots]
    if decision_confidences:
        print(f"\n🎯 DECISION CONFIDENCE")
        print(f"   Average: {sum(decision_confidences)/len(decision_confidences):.2f}")
        high_conf = sum(1 for c in decision_confidences if c >= 0.8)
        med_conf = sum(1 for c in decision_confidences if 0.6 <= c < 0.8)
        low_conf = sum(1 for c in decision_confidences if c < 0.6)
        print(f"   High (≥0.8): {high_conf} ({high_conf/len(decision_confidences)*100:.1f}%)")
        print(f"   Medium (0.6-0.8): {med_conf} ({med_conf/len(decision_confidences)*100:.1f}%)")
        print(f"   Low (<0.6): {low_conf} ({low_conf/len(decision_confidences)*100:.1f}%)")
    
    # Analyze outcome reasons
    print(f"\n📝 OUTCOME REASONS")
    outcome_reasons = {}
    for shot in shots:
        reason = shot.get('outcome_reason', 'unknown')
        outcome_reasons[reason] = outcome_reasons.get(reason, 0) + 1
    
    for reason, count in sorted(outcome_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"   {reason}: {count}")
    
    print("\n" + "="*80)

def main():
    parser = argparse.ArgumentParser(description='Test Enhanced Shot Detection System')
    parser.add_argument('--old', type=str, help='Path to old session JSON')
    parser.add_argument('--new', type=str, required=True, help='Path to new session JSON')
    parser.add_argument('--analyze', action='store_true', help='Analyze enhanced features')
    
    args = parser.parse_args()
    
    # Load new session
    new_session = load_session_data(args.new)
    
    if args.analyze:
        analyze_enhanced_features(new_session)
    
    if args.old:
        # Load old session
        old_session = load_session_data(args.old)
        
        # Compare sessions
        comparison = compare_sessions(old_session, new_session)
        
        # Save comparison report
        report = {
            'comparison_date': datetime.now().isoformat(),
            'old_session': args.old,
            'new_session': args.new,
            'summary': comparison
        }
        
        report_path = Path(args.new).parent / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Comparison report saved: {report_path}")

if __name__ == "__main__":
    main()

