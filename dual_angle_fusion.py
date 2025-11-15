#!/usr/bin/env python3
"""
Dual-Angle Fusion System
Combines near and far angle shot detections for improved accuracy
"""

import json
import subprocess
import argparse
import os
import shutil
from pathlib import Path
from datetime import datetime
import uuid
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional

class DualAngleFusion:
    def __init__(self, near_video: str, far_video: str, game_id: str,
                 near_model: str, far_model: str, offset_file: str,
                 validate: bool = True, angle: str = "LEFT",
                 start_time: Optional[int] = None, end_time: Optional[int] = None,
                 use_existing_near: Optional[str] = None,
                 use_existing_far: Optional[str] = None,
                 skip_video: bool = False,
                 temporal_window: float = 3.0,
                 prioritize_coverage: bool = False):
        self.near_video = near_video
        self.far_video = far_video
        self.game_id = game_id
        self.near_model = near_model
        self.far_model = far_model
        self.offset_file = offset_file
        self.validate = validate
        self.angle = angle
        self.start_time = start_time
        self.end_time = end_time

        # Existing results paths (optional)
        self.use_existing_near = use_existing_near
        self.use_existing_far = use_existing_far

        # Video output flag
        self.skip_video = skip_video

        # Temporal matching configuration
        self.temporal_window = temporal_window
        self.prioritize_coverage = prioritize_coverage

        # Load offset
        with open(offset_file, 'r') as f:
            offset_data = json.load(f)
            self.offset = offset_data['calculated_offset']

        print(f"🔄 Dual-Angle Fusion Initialized")
        print(f"   Near: {near_video}")
        print(f"   Far: {far_video}")
        print(f"   Offset: {self.offset:.4f}s (far ahead of near)")

        if use_existing_near:
            print(f"   📂 Using existing near results: {use_existing_near}")
        if use_existing_far:
            print(f"   📂 Using existing far results: {use_existing_far}")
        if skip_video:
            print(f"   ⚡ Video output skipped (analysis only mode)")
        if temporal_window != 2.0:
            print(f"   ⏱️  Temporal window: ±{temporal_window}s (default: ±2.0s)")
        if prioritize_coverage:
            print(f"   📈 Mode: High Recall (prioritize GT coverage over precision)")

        # Store result directory references
        self.near_result_dir = None
        self.far_result_dir = None

        # Result directory setup
        self.setup_result_directory()

    def setup_result_directory(self):
        """Create result directory matching near/far angle structure"""
        # Extract game info from video path
        # Handle both "input/09-23/game1_nearleft.mp4" and "input/09-23/Game-1/game1_nearleft.mp4"
        video_path = Path(self.near_video)
        video_name = video_path.stem
        parts = video_name.split('_')

        # Generate UUID for this session
        session_uuid = str(uuid.uuid4())

        # Extract date from path (find the MM-DD pattern)
        date_part = None
        for part in video_path.parts:
            if '-' in part and len(part) == 5 and part[:2].isdigit() and part[3:].isdigit():
                date_part = part
                break

        if not date_part:
            date_part = "unknown-date"

        # Extract game number from filename (e.g., "game1" -> "1")
        game_num = parts[0].replace('game', '')

        # Determine angle indicator: R- for RIGHT, L- for LEFT
        angle_indicator = "R-" if self.angle == "RIGHT" else "L-"

        # Format: MM-DD(gameN-ANGLE)_UUID (e.g., "09-23(game1-R-)_uuid")
        dir_name = f"{date_part}(game{game_num}-{angle_indicator})_{session_uuid}"

        # Use absolute path for results directory
        self.result_dir = Path.cwd() / "results" / dir_name
        self.result_dir.mkdir(parents=True, exist_ok=True)

        print(f"📁 Results: {self.result_dir}")

    def run_near_angle_detection(self) -> Tuple[str, str]:
        """
        Run near angle detection, return paths to results
        Note: Results are stored in Uball_near_angle_shot_detection/results/
        """
        print("\n🎯 Running Near Angle Detection...")

        # Record timestamp before running to identify new directory
        # Subtract 2 seconds as buffer to account for timing precision
        results_dir = Path("Uball_near_angle_shot_detection/results")
        before_time = datetime.now().timestamp() - 2.0

        # Convert paths to absolute from current directory
        # near_video is relative to near angle subproject (e.g., "input/09-23/game1_nearleft.mp4")
        abs_near_video = str((Path("Uball_near_angle_shot_detection") / self.near_video).resolve())
        abs_near_model = str(Path(self.near_model).resolve())

        cmd = [
            "python3",
            "main.py",
            "--action", "video",
            "--video_path", abs_near_video,
            "--model", abs_near_model,
            "--game_id", self.game_id,
            "--angle", self.angle
        ]

        if self.start_time is not None:
            cmd.extend(["--start_time", str(self.start_time)])
        if self.end_time is not None:
            cmd.extend(["--end_time", str(self.end_time)])

        if self.validate:
            cmd.append("--validate_accuracy")

        # Run from the near angle detection directory
        result = subprocess.run(cmd, capture_output=True, text=True,
                              cwd="Uball_near_angle_shot_detection")

        if result.returncode != 0:
            raise Exception(f"Near angle detection failed: {result.stderr}")

        # Find directory created AFTER the timestamp (not just the latest overall)
        result_dirs = [d for d in results_dir.glob("*")
                      if d.is_dir() and d.name != '.DS_Store'
                      and os.path.getmtime(d) > before_time]

        if not result_dirs:
            print(f"DEBUG: No new directories found with mtime > {before_time}")
            print(f"DEBUG: subprocess stdout: {result.stdout}")
            print(f"DEBUG: subprocess stderr: {result.stderr}")
            raise Exception("No new result directory created by near angle detection")

        latest_dir = max(result_dirs, key=os.path.getmtime)

        # Store for later use
        self.near_result_dir = latest_dir

        detection_file = latest_dir / "detection_results.json"
        video_file = latest_dir / "processed_video.mp4"

        print(f"   ✅ Near angle complete (stored in near angle subproject): {latest_dir.name}")

        return str(detection_file), str(video_file)

    def run_far_angle_detection(self) -> Tuple[str, str]:
        """
        Run far angle detection, return paths to results
        Note: Results are stored in Uball_far_angle_shot_detection/results/
        """
        print("\n🎯 Running Far Angle Detection...")

        # Record timestamp before running to identify new directory
        # Subtract 2 seconds as buffer to account for timing precision
        results_dir = Path("Uball_far_angle_shot_detection/results")
        before_time = datetime.now().timestamp() - 2.0

        # Convert paths to absolute from current directory
        # far_video is relative to far angle subproject (e.g., "input/09-23/Game-1/game1_farright.mp4")
        abs_far_video = str((Path("Uball_far_angle_shot_detection") / self.far_video).resolve())
        abs_far_model = str(Path(self.far_model).resolve())

        cmd = [
            "python3",
            "main.py",
            "--action", "video",
            "--video_path", abs_far_video,
            "--model", abs_far_model,
            "--game_id", self.game_id,
            "--angle", self.angle
        ]

        if self.start_time is not None:
            cmd.extend(["--start_time", str(self.start_time)])
        if self.end_time is not None:
            cmd.extend(["--end_time", str(self.end_time)])

        if self.validate:
            cmd.append("--validate_accuracy")

        # Run from the far angle detection directory
        result = subprocess.run(cmd, capture_output=True, text=True,
                              cwd="Uball_far_angle_shot_detection")

        if result.returncode != 0:
            raise Exception(f"Far angle detection failed: {result.stderr}")

        # Find directory created AFTER the timestamp (not just the latest overall)
        result_dirs = [d for d in results_dir.glob("*")
                      if d.is_dir() and d.name != '.DS_Store'
                      and os.path.getmtime(d) > before_time]

        if not result_dirs:
            print(f"DEBUG: No new directories found with mtime > {before_time}")
            print(f"DEBUG: subprocess stdout: {result.stdout}")
            print(f"DEBUG: subprocess stderr: {result.stderr}")
            raise Exception("No new result directory created by far angle detection")

        latest_dir = max(result_dirs, key=os.path.getmtime)

        # Store for later use
        self.far_result_dir = latest_dir

        detection_file = latest_dir / "detection_results.json"
        video_file = latest_dir / "processed_video.mp4"

        print(f"   ✅ Far angle complete (stored in far angle subproject): {latest_dir.name}")

        return str(detection_file), str(video_file)

    def match_detections(self, near_shots: List[Dict], far_shots: List[Dict]) -> Dict:
        """
        Match near and far angle detections using temporal window
        Apply offset to synchronize timestamps
        """
        print("\n🔗 Matching Detections...")

        # Apply offset to far angle timestamps
        # Positive offset means far is ahead, so subtract offset from far timestamps
        far_shots_synced = []
        for shot in far_shots:
            synced_shot = shot.copy()
            synced_shot['timestamp_seconds'] = shot['timestamp_seconds'] - self.offset
            synced_shot['original_timestamp'] = shot['timestamp_seconds']
            far_shots_synced.append(synced_shot)

        matches = []
        matched_near = set()
        matched_far = set()

        # Matching window: configurable (default ±3 seconds)
        time_window = self.temporal_window

        for i, near_shot in enumerate(near_shots):
            near_time = near_shot['timestamp_seconds']
            best_match = None
            best_time_diff = float('inf')
            best_far_idx = -1

            for j, far_shot in enumerate(far_shots_synced):
                if j in matched_far:
                    continue

                far_time = far_shot['timestamp_seconds']
                time_diff = abs(near_time - far_time)

                if time_diff <= time_window and time_diff < best_time_diff:
                    best_match = far_shot
                    best_time_diff = time_diff
                    best_far_idx = j

            if best_match:
                matches.append({
                    'near_shot': near_shot,
                    'far_shot': best_match,
                    'time_diff': best_time_diff,
                    'near_idx': i,
                    'far_idx': best_far_idx
                })
                matched_near.add(i)
                matched_far.add(best_far_idx)

        # Collect unmatched shots
        unmatched_near = [near_shots[i] for i in range(len(near_shots)) if i not in matched_near]
        unmatched_far = [far_shots_synced[i] for i in range(len(far_shots_synced)) if i not in matched_far]

        print(f"   Matched: {len(matches)} pairs")
        print(f"   Unmatched Near: {len(unmatched_near)}")
        print(f"   Unmatched Far: {len(unmatched_far)}")

        return {
            'matches': matches,
            'unmatched_near': unmatched_near,
            'unmatched_far': unmatched_far
        }

    # ========== V2 Feature Extraction Helpers ==========

    def check_rim_bounce_agreement(self, near_shot: Dict, far_shot: Dict) -> Dict:
        """
        Both angles should agree on rim bounce detection
        High confidence when both detect bounce or both don't
        """
        near_bounce = near_shot.get('is_rim_bounce', False)
        far_bounce = far_shot.get('bounced_back_out', False)

        # Agreement cases
        if near_bounce and far_bounce:
            return {'agreement': True, 'is_bounce': True, 'confidence': 0.95}
        elif not near_bounce and not far_bounce:
            return {'agreement': True, 'is_bounce': False, 'confidence': 0.9}
        else:
            # Disagreement - trust near angle (better rim visibility)
            return {'agreement': False, 'is_bounce': near_bounce, 'confidence': 0.7}

    def check_entry_angle_consistency(self, near_shot: Dict, far_shot: Dict) -> Dict:
        """
        Entry angles should be similar for the same shot
        Near: measured from side view (entry_angle)
        Far: derived from trajectory (valid_top_crossings)
        """
        near_angle = near_shot.get('entry_angle', None)
        far_top_crossings = far_shot.get('valid_top_crossings', 0)

        # Rough mapping:
        # Near entry_angle > 50° = steep (from above)
        # Near entry_angle < 40° = shallow (line drive)

        if near_angle is not None:
            if near_angle > 50 and far_top_crossings > 0:
                # Steep angle confirmed by far top crossing
                return {'consistent': True, 'confidence_boost': 1.1}
            elif near_angle < 40 and far_top_crossings == 0:
                # Shallow angle confirmed by no top crossing
                return {'consistent': True, 'confidence_boost': 1.05}
            else:
                # Inconsistent angles - potential mismatch
                return {'consistent': False, 'confidence_penalty': 0.9}
        else:
            # No near angle data - neutral
            return {'consistent': None, 'confidence_boost': 1.0}

    def analyze_swoosh_speed(self, near_shot: Dict, far_shot: Dict) -> Dict:
        """
        Fast disappearance = clean make
        Slow/oscillating = rim bounce or miss
        """
        # Near angle: use post_hoop_analysis
        post_hoop = near_shot.get('post_hoop_analysis', {})
        near_continues_down = post_hoop.get('ball_continues_down', False)
        near_downward = post_hoop.get('downward_movement', 0)

        # Far angle: use size_ratio progression and line crossings
        far_size_ratio = far_shot.get('avg_size_ratio', 0)
        far_bottom_crossings = far_shot.get('valid_bottom_crossings', 0)

        # Fast swoosh indicators:
        # - Near: ball continues downward smoothly
        # - Far: size ratio good (ball going through), bottom crossing exists

        if near_continues_down and far_bottom_crossings > 0 and far_size_ratio > 0.6:
            return {'swoosh_quality': 'fast', 'made_confidence': 1.2}
        elif not near_continues_down and far_bottom_crossings == 0:
            return {'swoosh_quality': 'slow', 'missed_confidence': 1.15}
        else:
            return {'swoosh_quality': 'uncertain', 'confidence': 1.0}

    def calculate_fusion_confidence(self, near_shot: Dict, far_shot: Dict) -> Dict:
        """
        Feature-weighted confidence calculation
        Uses existing features from both angle JSON files
        """
        # Base confidence from detection confidences
        near_conf = near_shot.get('detection_confidence', 0.5)
        far_conf = far_shot.get('confidence', far_shot.get('detection_confidence', 0.5))
        base_conf = (near_conf + far_conf) / 2.0

        # Feature weights (sum to 1.0)
        # V3: Rebalanced based on error analysis
        weights = {
            'outcome_agreement': 0.20,        # Reduced (N/A in disagreement cases)
            'rim_bounce_agreement': 0.35,     # INCREASED - most critical for error reduction
            'entry_angle_consistency': 0.12,   # Reduced slightly
            'swoosh_speed': 0.18,             # INCREASED - good made/missed indicator
            'overlap_quality': 0.05,           # Keep same
            'line_intersection': 0.10          # REDUCED - was over-trusted in V2.2
        }

        scores = {}

        # 1. Outcome agreement
        if near_shot.get('outcome') == far_shot.get('outcome'):
            scores['outcome_agreement'] = 1.0
        else:
            scores['outcome_agreement'] = 0.0

        # 2. Rim bounce agreement
        rim_check = self.check_rim_bounce_agreement(near_shot, far_shot)
        scores['rim_bounce_agreement'] = 1.0 if rim_check['agreement'] else 0.5

        # 3. Entry angle consistency
        angle_check = self.check_entry_angle_consistency(near_shot, far_shot)
        if angle_check['consistent'] is True:
            scores['entry_angle_consistency'] = 1.0
        elif angle_check['consistent'] is False:
            scores['entry_angle_consistency'] = 0.4
        else:
            scores['entry_angle_consistency'] = 0.7  # Neutral

        # 4. Swoosh speed
        swoosh = self.analyze_swoosh_speed(near_shot, far_shot)
        if swoosh['swoosh_quality'] == 'fast':
            scores['swoosh_speed'] = 1.0
        elif swoosh['swoosh_quality'] == 'slow':
            scores['swoosh_speed'] = 0.6
        else:
            scores['swoosh_speed'] = 0.8  # Uncertain

        # 5. Overlap quality (near angle)
        near_overlap = near_shot.get('weighted_overlap_score', 0) / 2.0  # Normalize to 0-1
        scores['overlap_quality'] = min(1.0, near_overlap)

        # 6. Line intersection (far angle)
        far_top = far_shot.get('valid_top_crossings', 0)
        far_bottom = far_shot.get('valid_bottom_crossings', 0)
        far_crossings = far_top + far_bottom
        scores['line_intersection'] = min(1.0, far_crossings / 2.0)

        # Calculate weighted score
        weighted_score = sum(weights[k] * scores[k] for k in weights)

        # V2.1: Conservative confidence formula with score-based multipliers
        # Low scores get penalized more, high scores get modest boost
        if weighted_score < 0.5:
            # Poor feature agreement - strong penalty
            multiplier = 0.6 + (weighted_score * 0.3)  # Range: 0.6 to 0.75
        elif weighted_score < 0.7:
            # Medium feature agreement - slight penalty to neutral
            multiplier = 0.75 + (weighted_score - 0.5) * 1.05  # Range: 0.75 to 0.96
        else:
            # Strong feature agreement - modest boost
            multiplier = 0.935 + (weighted_score - 0.7) * 0.55  # Range: 0.935 to 1.1

        final_confidence = base_conf * multiplier

        return {
            'confidence': min(0.99, final_confidence),
            'feature_scores': scores,
            'base_confidence': base_conf,
            'weighted_score': weighted_score
        }

    def classify_shot_type(self, feature_scores: Dict, near_shot: Dict, far_shot: Dict) -> Dict:
        """
        V3.1: Shot type classification for angle-specific reliability weighting
        Returns: {type, reliable_angle, near_boost, far_boost}
        """
        line_int = feature_scores.get('line_intersection', 0)
        swoosh = feature_scores.get('swoosh_speed', 0)
        near_rb = near_shot.get('is_rim_bounce', False)
        far_rb = far_shot.get('bounced_back_out', False)
        overlap = feature_scores.get('overlap_quality', 0)

        # Clean swish: Line cross, fast swoosh, no bounce
        if line_int >= 0.8 and swoosh >= 0.7 and not near_rb and not far_rb:
            return {
                'type': 'clean_swish',
                'reliable_angle': 'both',
                'near_boost': 1.0,
                'far_boost': 1.0
            }

        # Rim make: Line cross, medium/slow swoosh, possible bounce
        if line_int >= 0.8 and swoosh < 0.7 and (near_rb or far_rb):
            return {
                'type': 'rim_make',
                'reliable_angle': 'near',  # Near better at rim contact
                'near_boost': 1.3,
                'far_boost': 0.8
            }

        # Rim bounce out: Some line cross, bounce detected
        if 0.3 <= line_int < 0.8 and (near_rb or far_rb):
            return {
                'type': 'rim_bounce_out',
                'reliable_angle': 'near',  # Near sees bounce better
                'near_boost': 1.4,
                'far_boost': 0.7
            }

        # Near-rim miss: Little/no line cross, good overlap, possible bounce
        if line_int < 0.5 and overlap > 0.5 and (near_rb or far_rb):
            return {
                'type': 'near_rim_miss',
                'reliable_angle': 'near',
                'near_boost': 1.3,
                'far_boost': 0.8
            }

        # Clean miss: No line cross, no bounce
        if line_int < 0.3 and not near_rb and not far_rb:
            return {
                'type': 'clean_miss',
                'reliable_angle': 'both',
                'near_boost': 1.0,
                'far_boost': 1.0
            }

        # Default: uncertain type
        return {
            'type': 'uncertain',
            'reliable_angle': 'both',
            'near_boost': 1.0,
            'far_boost': 1.0
        }

    def cross_angle_validation(self, near_shot: Dict, far_shot: Dict, fused_outcome: str,
                               fused_confidence: float, feature_scores: Dict) -> Tuple[str, float, List[str]]:
        """
        V3.3: Cross-angle consistency validation
        Returns: (adjusted_outcome, adjusted_confidence, flags)
        """
        flags = []
        adjusted_outcome = fused_outcome
        adjusted_confidence = fused_confidence

        near_out = near_shot.get('outcome')
        far_out = far_shot.get('outcome')

        # Flag 1: Far says made with high line cross, but near shows rim bounce
        if (far_out == 'made' and
            feature_scores.get('line_intersection', 0) >= 0.8 and
            near_shot.get('is_rim_bounce', False)):
            flags.append('rim_bounce_vs_line_cross')
            # Strong signal this is a rim bounce out - trust near
            if fused_outcome == 'made':
                adjusted_outcome = 'missed'
                adjusted_confidence *= 0.7

        # Flag 2: Both high confidence but disagree, no clear physical reason
        near_conf = near_shot.get('detection_confidence', 0.5)
        far_conf = far_shot.get('confidence', far_shot.get('detection_confidence', 0.5))
        if (abs(near_conf - far_conf) < 0.1 and
            near_out != far_out and
            not near_shot.get('is_rim_bounce') and
            not far_shot.get('bounced_back_out')):
            flags.append('unexplained_high_conf_disagreement')
            # Use feature tiebreaker - trust swoosh speed
            if feature_scores.get('swoosh_speed', 0) >= 0.8:
                # Fast swoosh suggests made
                if fused_outcome == 'missed':
                    adjusted_outcome = 'made'
                    adjusted_confidence *= 0.85

        return adjusted_outcome, adjusted_confidence, flags

    def resolve_disagreement(self, near_shot: Dict, far_shot: Dict, fusion_scores: Dict) -> Tuple[str, float]:
        """
        V3: Enhanced disagreement resolution with shot type awareness
        Returns: (outcome, confidence)
        """
        feature_scores = fusion_scores['feature_scores']

        # Get individual angle confidences and outcomes
        near_conf = near_shot.get('detection_confidence', 0.5)
        far_conf = far_shot.get('confidence', far_shot.get('detection_confidence', 0.5))
        near_outcome = near_shot.get('outcome', 'undetermined')
        far_outcome = far_shot.get('outcome', 'undetermined')

        # V3.1: Classify shot type for angle-specific reliability
        shot_type = self.classify_shot_type(feature_scores, near_shot, far_shot)

        # V3.2: Calculate weighted votes with adjusted feature support weights
        # Feature support for "made" - rebalanced for V3
        made_feature_support = (
            feature_scores.get('line_intersection', 0) * 0.28 +      # REDUCED from 0.35 (was over-trusted)
            feature_scores.get('swoosh_speed', 0) * 0.35 +           # INCREASED from 0.30 (good signal)
            feature_scores.get('entry_angle_consistency', 0) * 0.20 +
            feature_scores.get('overlap_quality', 0) * 0.17          # INCREASED from 0.15
        )

        # Feature support for "missed" - rebalanced for V3
        missed_feature_support = (
            (1.0 - feature_scores.get('line_intersection', 0)) * 0.32 +  # REDUCED from 0.40
            (1.0 - feature_scores.get('swoosh_speed', 0)) * 0.35 +
            feature_scores.get('rim_bounce_agreement', 0) * 0.33         # INCREASED from 0.25 (critical)
        )

        # Calculate base weighted votes
        near_vote_weight = near_conf * (1.0 + made_feature_support if near_outcome == 'made' else 1.0 + missed_feature_support)
        far_vote_weight = far_conf * (1.0 + made_feature_support if far_outcome == 'made' else 1.0 + missed_feature_support)

        # V3.2: Apply shot-type-specific reliability boosts
        near_vote_weight *= shot_type['near_boost']
        far_vote_weight *= shot_type['far_boost']

        # V3.2: Special case handling for common error patterns
        # Pattern 1: Far says "made" with line cross, but near says "missed"
        if far_outcome == 'made' and near_outcome == 'missed':
            if feature_scores.get('line_intersection', 0) >= 0.8:
                # Check for rim bounce indicators
                if near_shot.get('is_rim_bounce') or far_shot.get('bounced_back_out'):
                    # Likely rim bounce - strongly favor near angle
                    near_vote_weight *= 1.5
                    far_vote_weight *= 0.6
                elif feature_scores.get('swoosh_speed', 0) < 0.5:
                    # Slow swoosh suggests rim contact - favor near
                    near_vote_weight *= 1.3
                    far_vote_weight *= 0.7

        # Pattern 2: Near says "made" but far says "missed"
        elif near_outcome == 'made' and far_outcome == 'missed':
            # Check if near has strong made indicators
            if (feature_scores.get('overlap_quality', 0) > 0.7 and
                feature_scores.get('swoosh_speed', 0) > 0.6):
                # Near has good evidence - boost it
                near_vote_weight *= 1.2

        # V2.2: Conservative rim bounce penalty (keep from V2.2)
        rim_bounce_detected = near_shot.get('is_rim_bounce', False) or far_shot.get('bounced_back_out', False)
        if rim_bounce_detected:
            # Strongly penalize "made" votes when rim bounce detected
            if near_outcome == 'made':
                near_vote_weight *= 0.3
            if far_outcome == 'made':
                far_vote_weight *= 0.3

        # Decide based on weighted votes
        if near_outcome == far_outcome:
            # This shouldn't happen (disagreement function), but handle it
            return near_outcome, (near_conf + far_conf) / 2.0
        elif near_vote_weight > far_vote_weight:
            # Near angle wins
            confidence = near_conf * (0.8 + 0.2 * (near_vote_weight / (near_vote_weight + far_vote_weight)))
            if rim_bounce_detected and near_outcome == 'made':
                confidence *= 0.6
            outcome, confidence = near_outcome, min(0.95, confidence)
        else:
            # Far angle wins
            confidence = far_conf * (0.8 + 0.2 * (far_vote_weight / (near_vote_weight + far_vote_weight)))
            if rim_bounce_detected and far_outcome == 'made':
                confidence *= 0.6
            outcome, confidence = far_outcome, min(0.95, confidence)

        # V3.3: Apply cross-angle validation
        outcome, confidence, flags = self.cross_angle_validation(
            near_shot, far_shot, outcome, confidence, feature_scores
        )

        return outcome, confidence

    # ========== End V2 Feature Helpers ==========

    def fuse_matched_pair(self, match: Dict) -> Dict:
        """
        V2 Feature-based fusion for matched near+far pair
        Uses rich features from both angles for improved accuracy
        """
        near = match['near_shot']
        far = match['far_shot']

        # Calculate feature-based confidence using V2 algorithm
        fusion_analysis = self.calculate_fusion_confidence(near, far)

        # Extract outcomes
        near_outcome = near.get('outcome', 'undetermined')
        far_outcome = far.get('outcome', 'undetermined')

        # Determine final outcome
        if near_outcome == far_outcome:
            # Both angles agree - use agreed outcome with boosted confidence
            final_outcome = near_outcome
            fusion_confidence = fusion_analysis['confidence']
            fusion_method = 'v2_agreement'
        else:
            # Angles disagree - use V2 feature-based resolution
            final_outcome, fusion_confidence = self.resolve_disagreement(near, far, fusion_analysis)
            fusion_method = 'v2_feature_resolution'

        # Extract confidence values
        near_conf = near.get('detection_confidence', 0.5)
        far_conf = far.get('confidence', far.get('detection_confidence', 0.5))

        # Build fused shot with V2 enriched metadata
        fused_shot = {
            'timestamp_seconds': near['timestamp_seconds'],
            'outcome': final_outcome,
            'fusion_method': fusion_method,
            'fusion_confidence': fusion_confidence,
            'outcome_agreement': (near_outcome == far_outcome),
            'time_diff': match['time_diff'],

            # V2 Feature Analysis
            'feature_analysis': {
                'weighted_score': fusion_analysis['weighted_score'],
                'base_confidence': fusion_analysis['base_confidence'],
                'feature_scores': fusion_analysis['feature_scores']
            },

            # Near angle detection details
            'near_detection': {
                'outcome': near_outcome,
                'confidence': near_conf,
                'entry_angle': near.get('entry_angle'),
                'is_rim_bounce': near.get('is_rim_bounce', False),
                'weighted_overlap_score': near.get('weighted_overlap_score', 0),
                'method': near.get('detection_method', 'unknown')
            },

            # Far angle detection details
            'far_detection': {
                'outcome': far_outcome,
                'confidence': far_conf,
                'valid_top_crossings': far.get('valid_top_crossings', 0),
                'valid_bottom_crossings': far.get('valid_bottom_crossings', 0),
                'bounced_back_out': far.get('bounced_back_out', False),
                'avg_size_ratio': far.get('avg_size_ratio', 0),
                'method': far.get('detection_method', 'unknown')
            }
        }

        return fused_shot

    def process_unmatched(self, unmatched: List[Dict], source: str) -> List[Dict]:
        """
        Decide whether to keep unmatched detections
        Two modes:
        - High Precision (default): conf > 0.75 for both near and far
        - High Recall (prioritize_coverage): ALL near shots, conf > 0.65 for far
        """
        kept = []

        # Determine threshold based on mode and source
        if self.prioritize_coverage:
            # High recall mode: prioritize GT coverage
            if source == 'near':
                # Near has best GT coverage (97.4%), keep ALL unmatched shots
                threshold = 0.0  # Keep all
                mode_desc = "all shots (high recall mode)"
            else:
                # Far: lower threshold to catch more real shots
                threshold = 0.65
                mode_desc = f"conf > {threshold} (high recall mode)"
        else:
            # High precision mode (default)
            threshold = 0.75
            mode_desc = f"conf > {threshold}"

        for shot in unmatched:
            confidence = shot.get('detection_confidence', 0.5)

            if confidence > threshold:
                kept.append({
                    'timestamp_seconds': shot['timestamp_seconds'],
                    'outcome': shot.get('outcome', 'undetermined'),
                    'fusion_method': f'single_{source}',
                    'fusion_confidence': confidence * 0.9,  # Slight penalty for being unmatched
                    'outcome_agreement': False,
                    'source': source,
                    f'{source}_detection': {
                        'outcome': shot.get('outcome'),
                        'confidence': confidence,
                        'method': shot.get('detection_method', 'unknown')
                    }
                })

        print(f"   Kept {len(kept)}/{len(unmatched)} unmatched {source} shots ({mode_desc})")
        return kept

    def fuse_detections(self, near_file: str, far_file: str) -> str:
        """Main fusion logic"""
        print("\n🧬 Fusing Detections...")

        # Load detection results
        with open(near_file, 'r') as f:
            near_data = json.load(f)
        with open(far_file, 'r') as f:
            far_data = json.load(f)

        near_shots = near_data['shots']
        far_shots = far_data['shots']

        # Normalize far angle confidence field name
        # Far angle uses "confidence", near angle uses "detection_confidence"
        for shot in far_shots:
            if 'confidence' in shot and 'detection_confidence' not in shot:
                shot['detection_confidence'] = shot['confidence']

        # Match detections
        match_data = self.match_detections(near_shots, far_shots)

        # Fuse matched pairs
        fused_shots = []
        for match in match_data['matches']:
            fused_shot = self.fuse_matched_pair(match)
            fused_shots.append(fused_shot)

        # Process unmatched shots
        unmatched_near_kept = self.process_unmatched(match_data['unmatched_near'], 'near')
        unmatched_far_kept = self.process_unmatched(match_data['unmatched_far'], 'far')

        # Combine all fused shots
        fused_shots.extend(unmatched_near_kept)
        fused_shots.extend(unmatched_far_kept)

        # Sort by timestamp
        fused_shots.sort(key=lambda x: x['timestamp_seconds'])

        # Calculate statistics
        made_count = sum(1 for s in fused_shots if s['outcome'] == 'made')
        missed_count = sum(1 for s in fused_shots if s['outcome'] == 'missed')

        # Build fusion results
        fusion_results = {
            'session_info': {
                'start_time': datetime.now().isoformat(),
                'near_video': self.near_video,
                'far_video': self.far_video,
                'offset': self.offset,
                'fusion_version': 'feature_weighted_v3.0'
            },
            'statistics': {
                'total_shots': len(fused_shots),
                'made_shots': made_count,
                'missed_shots': missed_count,
                'matched_pairs': len(match_data['matches']),
                'unmatched_near_kept': len(unmatched_near_kept),
                'unmatched_far_kept': len(unmatched_far_kept)
            },
            'shots': fused_shots
        }

        # Ensure result directory exists before writing
        self.result_dir.mkdir(parents=True, exist_ok=True)

        # Save detection results (renamed from fusion_results.json)
        output_file = self.result_dir / "detection_results.json"
        with open(output_file, 'w') as f:
            json.dump(fusion_results, f, indent=2)

        print(f"\n📊 Fusion Statistics:")
        print(f"   Total Shots: {len(fused_shots)}")
        print(f"   Made: {made_count} | Missed: {missed_count}")
        print(f"   Matched Pairs: {len(match_data['matches'])}")

        return str(output_file)

    def stitch_videos(self, near_video_file: str, far_video_file: str) -> str:
        """
        Stitch videos: far angle on top, near angle on bottom
        With fusion predictions overlay on top right
        Applies offset to synchronize videos properly
        """
        print("\n🎬 Stitching Videos...")

        # Open both videos
        near_cap = cv2.VideoCapture(near_video_file)
        far_cap = cv2.VideoCapture(far_video_file)

        # Get video properties
        fps = near_cap.get(cv2.CAP_PROP_FPS)
        width = int(near_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(near_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Apply offset synchronization
        # Offset > 0 means far is ahead of near, so skip initial frames in far video
        offset_frames = int(self.offset * fps)
        print(f"   Applying offset: {self.offset:.4f}s = {offset_frames} frames")
        print(f"   (Far angle is ahead, skipping {offset_frames} frames in far video)")

        for _ in range(offset_frames):
            far_cap.read()

        # Ensure result directory exists before writing
        self.result_dir.mkdir(parents=True, exist_ok=True)

        # Output video: stacked vertically (far on top, near on bottom)
        output_height = height * 2
        output_file = self.result_dir / "processed_video.mp4"

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_file), fourcc, fps, (width, output_height))

        frame_count = 0
        while True:
            ret_near, frame_near = near_cap.read()
            ret_far, frame_far = far_cap.read()

            if not ret_near or not ret_far:
                break

            # Stack far on top, near on bottom
            stacked = np.vstack([frame_far, frame_near])

            # TODO: Add overlay predictions on top right

            out.write(stacked)
            frame_count += 1

            if frame_count % 1000 == 0:
                print(f"   Processed {frame_count} frames...")

        near_cap.release()
        far_cap.release()
        out.release()

        print(f"   ✅ Stitched video saved: {output_file.name}")
        return str(output_file)

    def copy_ground_truth(self):
        """Copy ground truth from near angle results"""
        print("\n📋 Copying Ground Truth...")

        if not self.near_result_dir:
            print("   ⚠️  No near result directory found")
            return

        # Ensure result directory exists before writing
        self.result_dir.mkdir(parents=True, exist_ok=True)

        near_gt_file = self.near_result_dir / "ground_truth.json"
        fusion_gt_file = self.result_dir / "ground_truth.json"

        if near_gt_file.exists():
            shutil.copy(near_gt_file, fusion_gt_file)
            print(f"   ✅ Ground truth copied from near angle")
        else:
            print(f"   ⚠️  Ground truth file not found in near angle results")

    def generate_accuracy_analysis(self):
        """Generate accuracy analysis comparing fusion results with ground truth"""
        print("\n📊 Generating Accuracy Analysis...")

        # Load fusion detection results
        detection_file = self.result_dir / "detection_results.json"
        with open(detection_file, 'r') as f:
            fusion_data = json.load(f)

        # Load ground truth
        gt_file = self.result_dir / "ground_truth.json"
        if not gt_file.exists():
            print("   ⚠️  Ground truth not available, skipping accuracy analysis")
            return

        with open(gt_file, 'r') as f:
            gt_data = json.load(f)

        fusion_shots = fusion_data.get('shots', [])
        # Ground truth is a list, not a dict
        gt_shots = gt_data if isinstance(gt_data, list) else gt_data.get('ground_truth_shots', [])

        # Calculate statistics
        matched_correct = []
        matched_incorrect = []
        unmatched_gt = []

        # Match fusion shots with ground truth (±2 second window)
        for gt_shot in gt_shots:
            gt_time = gt_shot['timestamp_seconds']
            gt_outcome = gt_shot['outcome']

            best_match = None
            best_time_diff = float('inf')

            for fusion_shot in fusion_shots:
                fusion_time = fusion_shot['timestamp_seconds']
                time_diff = abs(fusion_time - gt_time)

                if time_diff <= 2.0 and time_diff < best_time_diff:
                    best_match = fusion_shot
                    best_time_diff = time_diff

            if best_match:
                if best_match['outcome'] == gt_outcome:
                    matched_correct.append({
                        'fusion_timestamp': best_match['timestamp_seconds'],
                        'gt_timestamp': gt_time,
                        'outcome': gt_outcome,
                        'time_diff': best_time_diff
                    })
                else:
                    matched_incorrect.append({
                        'fusion_timestamp': best_match['timestamp_seconds'],
                        'gt_timestamp': gt_time,
                        'fusion_outcome': best_match['outcome'],
                        'gt_outcome': gt_outcome,
                        'time_diff': best_time_diff
                    })
            else:
                unmatched_gt.append(gt_shot)

        # Calculate metrics
        total_detected = len(fusion_shots)
        total_gt = len(gt_shots)
        num_matched_correct = len(matched_correct)
        num_matched_incorrect = len(matched_incorrect)
        total_matched = num_matched_correct + num_matched_incorrect

        matched_accuracy = (num_matched_correct / total_matched * 100) if total_matched > 0 else 0
        coverage = (total_matched / total_gt * 100) if total_gt > 0 else 0

        # Build analysis
        analysis = {
            'detection_summary': {
                'total_shots': total_detected,
                'made_shots': sum(1 for s in fusion_shots if s['outcome'] == 'made'),
                'missed_shots': sum(1 for s in fusion_shots if s['outcome'] == 'missed'),
                'shooting_percentage': (sum(1 for s in fusion_shots if s['outcome'] == 'made') / total_detected * 100) if total_detected > 0 else 0
            },
            'ground_truth_summary': {
                'total_shots': total_gt,
                'made_shots': sum(1 for s in gt_shots if s['outcome'] == 'made'),
                'missed_shots': sum(1 for s in gt_shots if s['outcome'] == 'missed'),
                'shooting_percentage': (sum(1 for s in gt_shots if s['outcome'] == 'made') / total_gt * 100) if total_gt > 0 else 0
            },
            'accuracy_analysis': {
                'total_detected_shots': total_detected,
                'matched_correct': num_matched_correct,
                'matched_incorrect': num_matched_incorrect,
                'overall_accuracy_percentage': matched_accuracy,
                'matched_shots_accuracy': matched_accuracy,
                'ground_truth_coverage': coverage
            },
            'detailed_analysis': {
                'matched_correct': matched_correct,
                'matched_incorrect': matched_incorrect,
                'unmatched_ground_truth': unmatched_gt
            }
        }

        # Ensure result directory exists before writing
        self.result_dir.mkdir(parents=True, exist_ok=True)

        # Save analysis
        output_file = self.result_dir / "accuracy_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)

        print(f"   ✅ Accuracy: {matched_accuracy:.1f}% | Coverage: {coverage:.1f}%")

    def generate_session_summary(self):
        """Generate session summary file"""
        print("\n📝 Generating Session Summary...")

        # Load detection results
        detection_file = self.result_dir / "detection_results.json"
        with open(detection_file, 'r') as f:
            fusion_data = json.load(f)

        # Load accuracy analysis if available
        accuracy_file = self.result_dir / "accuracy_analysis.json"
        shot_count_accuracy = 0
        gt_shots = 0

        if accuracy_file.exists():
            with open(accuracy_file, 'r') as f:
                accuracy_data = json.load(f)
                gt_shots = accuracy_data['ground_truth_summary']['total_shots']
                detected_shots = accuracy_data['detection_summary']['total_shots']
                if gt_shots > 0:
                    shot_count_accuracy = (detected_shots / gt_shots) * 100

        summary = {
            'session_info': {
                'uuid': self.result_dir.name,
                'created_at': datetime.now().isoformat(),
                'game_id': self.game_id,
                'near_video_path': self.near_video,
                'far_video_path': self.far_video,
                'offset': self.offset,
                'fusion_version': 'feature_weighted_v3.0'
            },
            'files': {
                'detection_results': 'detection_results.json',
                'ground_truth': 'ground_truth.json',
                'accuracy_analysis': 'accuracy_analysis.json',
                'processed_video': 'processed_video.mp4'
            },
            'quick_summary': {
                'detection_shots': fusion_data['statistics']['total_shots'],
                'ground_truth_shots': gt_shots,
                'shot_count_accuracy': shot_count_accuracy,
                'matched_pairs': fusion_data['statistics']['matched_pairs'],
                'unmatched_near_kept': fusion_data['statistics']['unmatched_near_kept'],
                'unmatched_far_kept': fusion_data['statistics']['unmatched_far_kept']
            }
        }

        # Ensure result directory exists before writing
        self.result_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        output_file = self.result_dir / "session_summary.json"
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"   ✅ Session summary saved")

    def run(self):
        """Execute full fusion pipeline"""
        start_time = datetime.now()

        print("\n" + "="*60)
        print("🎯 DUAL-ANGLE FUSION PIPELINE")
        print("="*60)

        # Step 1: Get detection results (either run or use existing)
        if self.use_existing_near:
            print("\n📂 Using existing near angle results...")
            near_result_path = Path(self.use_existing_near)
            self.near_result_dir = near_result_path
            near_detection_file = str(near_result_path / "detection_results.json")
            near_video_file = str(near_result_path / "processed_video.mp4")
            print(f"   ✅ Near angle: {near_result_path.name}")
        else:
            near_detection_file, near_video_file = self.run_near_angle_detection()

        if self.use_existing_far:
            print("\n📂 Using existing far angle results...")
            far_result_path = Path(self.use_existing_far)
            self.far_result_dir = far_result_path
            far_detection_file = str(far_result_path / "detection_results.json")
            far_video_file = str(far_result_path / "processed_video.mp4")
            print(f"   ✅ Far angle: {far_result_path.name}")
        else:
            far_detection_file, far_video_file = self.run_far_angle_detection()

        # Step 2: Fuse detections
        fusion_file = self.fuse_detections(near_detection_file, far_detection_file)

        # Step 3: Stitch videos (skip if requested)
        if not self.skip_video:
            stitched_video = self.stitch_videos(near_video_file, far_video_file)
        else:
            print("\n⚡ Skipping video stitching (--skip_video enabled)")

        # Step 4: Copy ground truth
        self.copy_ground_truth()

        # Step 5: Generate accuracy analysis if validation requested
        if self.validate:
            self.generate_accuracy_analysis()

        # Step 6: Generate session summary
        self.generate_session_summary()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*60)
        print(f"✅ FUSION COMPLETE ({duration:.1f}s)")
        print(f"   Results: {self.result_dir}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Dual-Angle Basketball Shot Fusion')
    parser.add_argument('--near_video', required=True, help='Path to near angle video')
    parser.add_argument('--far_video', required=True, help='Path to far angle video')
    parser.add_argument('--game_id', required=True, help='Game UUID for ground truth')
    parser.add_argument('--near_model', required=True, help='Near angle YOLO model path')
    parser.add_argument('--far_model', required=True, help='Far angle YOLO model path')
    parser.add_argument('--offset_file', required=True, help='Path to offset JSON file')
    parser.add_argument('--validate_accuracy', action='store_true', help='Validate against ground truth')
    parser.add_argument('--angle', default='LEFT', choices=['LEFT', 'RIGHT'], help='Angle filter for ground truth')
    parser.add_argument('--start_time', type=int, help='Start time in seconds (for quick testing)')
    parser.add_argument('--end_time', type=int, help='End time in seconds (for quick testing)')
    parser.add_argument('--use_existing_near', type=str, help='Path to existing near angle result directory')
    parser.add_argument('--use_existing_far', type=str, help='Path to existing far angle result directory')
    parser.add_argument('--skip_video', action='store_true', help='Skip video stitching (much faster, only generate JSON results)')
    parser.add_argument('--temporal_window', type=float, default=3.0, help='Temporal matching window in seconds (default: 3.0)')
    parser.add_argument('--prioritize_coverage', action='store_true', help='High recall mode: prioritize GT coverage over precision (keeps all unmatched near shots)')

    args = parser.parse_args()

    fusion = DualAngleFusion(
        near_video=args.near_video,
        far_video=args.far_video,
        game_id=args.game_id,
        near_model=args.near_model,
        far_model=args.far_model,
        offset_file=args.offset_file,
        validate=args.validate_accuracy,
        angle=args.angle,
        start_time=args.start_time,
        end_time=args.end_time,
        use_existing_near=args.use_existing_near,
        use_existing_far=args.use_existing_far,
        skip_video=args.skip_video,
        temporal_window=args.temporal_window,
        prioritize_coverage=args.prioritize_coverage
    )

    fusion.run()


if __name__ == '__main__':
    main()
