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
                 skip_video: bool = False):
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

        # Convert paths to absolute, accounting for subproject structure
        # near_video is relative to near angle project (e.g., "input/09-23/game1_nearleft.mp4")
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

        # Convert paths to absolute, accounting for subproject structure
        # far_video is relative to far angle project (e.g., "input/09-23/Game-1/game1_farright.mp4")
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

        # Matching window: ±2 seconds
        time_window = 2.0

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

    def fuse_matched_pair(self, match: Dict) -> Dict:
        """
        Feature-based fusion for matched near+far pair
        Returns fused shot detection with combined confidence
        """
        near = match['near_shot']
        far = match['far_shot']

        # Extract features from both angles
        near_conf = near.get('detection_confidence', 0.5)
        far_conf = far.get('detection_confidence', 0.5)

        near_outcome = near.get('outcome', 'undetermined')
        far_outcome = far.get('outcome', 'undetermined')

        # Feature 1: Outcome agreement
        outcome_agrees = (near_outcome == far_outcome)

        # Feature 2: Detection confidence (average)
        avg_confidence = (near_conf + far_conf) / 2.0

        # Feature 3: Near angle overlap quality (better for proximity shots)
        near_overlap = near.get('avg_overlap_percentage', 0)
        near_weighted_score = near.get('weighted_overlap_score', 0)

        # Feature 4: Far angle line intersection confidence
        far_score = far.get('line_intersection_score', 0)

        # Fusion Decision Logic (Balanced F1 optimization)
        fusion_confidence = 0.0
        final_outcome = 'undetermined'
        fusion_method = ''

        if outcome_agrees:
            # Both angles agree - high confidence
            fusion_confidence = min(0.95, avg_confidence * 1.15)
            final_outcome = near_outcome
            fusion_method = 'agreement'
        else:
            # Angles disagree - use feature-based arbitration

            # Weight by confidence and angle-specific reliability
            near_weight = near_conf * (1 + near_overlap / 100.0)
            far_weight = far_conf * (1 + far_score / 10.0)

            if near_weight > far_weight:
                final_outcome = near_outcome
                fusion_confidence = near_conf * 0.85  # Penalty for disagreement
                fusion_method = 'near_dominant'
            else:
                final_outcome = far_outcome
                fusion_confidence = far_conf * 0.85
                fusion_method = 'far_dominant'

        # Build fused shot
        fused_shot = {
            'timestamp_seconds': near['timestamp_seconds'],  # Use near timestamp as reference
            'outcome': final_outcome,
            'fusion_method': fusion_method,
            'fusion_confidence': fusion_confidence,
            'outcome_agreement': outcome_agrees,
            'time_diff': match['time_diff'],
            'near_detection': {
                'outcome': near_outcome,
                'confidence': near_conf,
                'overlap': near_overlap,
                'method': near.get('detection_method', 'unknown')
            },
            'far_detection': {
                'outcome': far_outcome,
                'confidence': far_conf,
                'score': far_score,
                'method': far.get('detection_method', 'unknown')
            }
        }

        return fused_shot

    def process_unmatched(self, unmatched: List[Dict], source: str) -> List[Dict]:
        """
        Decide whether to keep unmatched detections
        Balanced approach: keep high-confidence unmatched shots
        """
        kept = []

        for shot in unmatched:
            confidence = shot.get('detection_confidence', 0.5)

            # Keep if confidence > 0.75 (high confidence in single angle)
            if confidence > 0.75:
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

        print(f"   Kept {len(kept)}/{len(unmatched)} unmatched {source} shots (conf > 0.75)")
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
                'fusion_version': 'v1_feature_based'
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
        """
        print("\n🎬 Stitching Videos...")

        # Open both videos
        near_cap = cv2.VideoCapture(near_video_file)
        far_cap = cv2.VideoCapture(far_video_file)

        # Get video properties
        fps = near_cap.get(cv2.CAP_PROP_FPS)
        width = int(near_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(near_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

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
                'fusion_version': 'v1_feature_based'
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
        skip_video=args.skip_video
    )

    fusion.run()


if __name__ == '__main__':
    main()
