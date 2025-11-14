#!/usr/bin/env python3
"""
Simplified Far Angle Shot Detection - Line Intersection Logic

NEW SIMPLIFIED LOGIC:
1. Track a vertical line through the center of the ball
2. Check if that line intersects with the hoop's bounding box
3. Check ball-to-hoop size ratio (if ratio correct, ball is at hoop depth, not in front)
4. Decision: line intersects + correct ratio = MADE

We DON'T check if ball bbox is inside hoop - ONLY if the line through ball center intersects hoop bbox
"""

import cv2
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from ultralytics import YOLO
from collections import deque
import logging
import argparse


class SimplifiedShotAnalyzer:
    """Simplified shot analyzer using line intersection logic"""

    # Zone parameters - V5: STRICTER to eliminate false positives
    # Analysis showed: 156 detections vs 77 GT = 50.6% false positive rate
    # V5 goal: Reduce false positives by tightening zone and increasing min frames
    HOOP_ZONE_WIDTH = 80        # TIGHTENED from 100 (back to V3 that worked for Game 1)
    HOOP_ZONE_VERTICAL = 95     # TIGHTENED from 115 (even stricter than V3's 100)
    MIN_FRAMES_IN_ZONE = 8      # INCREASED from 3 (eliminate quick passes/dribbles)

    # Ball-to-hoop size ratio thresholds - STRICTER to ensure ball is at hoop depth
    # Analysis showed: Made shots avg=0.231 (0.165-0.340), Missed avg=0.391 (0.324-0.490)
    # V5: Further tightened to reduce false positives
    MIN_BALL_HOOP_RATIO = 0.18  # STRICTER from 0.17
    MAX_BALL_HOOP_RATIO = 0.28  # STRICTER from 0.30

    # Confidence thresholds
    BASKETBALL_CONFIDENCE = 0.35
    HOOP_CONFIDENCE = 0.5

    # Shot sequence grouping
    SHOT_SEQUENCE_TIMEOUT = 3.0
    POST_SHOT_TRACKING_FRAMES = 20
    TRAJECTORY_LENGTH = 30

    def __init__(self, model_path: str):
        """Initialize the simplified shot analyzer"""
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Load YOLO model
        self.logger.info(f"Loading YOLO model from: {model_path}")
        self.model = YOLO(model_path)

        # Initialize tracking
        self.detected_shots = []
        self.current_shot_sequence = None
        self.frames_since_last_shot = 0
        self.frame_count = 0
        self.fps = 30

        # Trajectory tracking
        self.ball_trajectory = deque(maxlen=self.TRAJECTORY_LENGTH)
        self.hoop_position = None
        self.hoop_bbox = None
        self.hoop_size = None  # Store hoop bbox area

        # Statistics
        self.stats = {
            'total_shots': 0,
            'made_shots': 0,
            'missed_shots': 0
        }

        self.logger.info("SimplifiedShotAnalyzer initialized - Line Intersection Logic")

    def detect_objects(self, frame: np.ndarray) -> Dict:
        """Run YOLO inference and extract detections"""
        results = self.model(frame, verbose=False, conf=0.3)

        detections = {
            'ball': None,
            'hoop': None,
            'all_balls': [],
            'all_hoops': []
        }

        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes

            for i in range(len(boxes)):
                cls = int(boxes.cls[i])
                conf = float(boxes.conf[i])
                x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()

                box_data = {
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'confidence': conf,
                    'center': (int((x1 + x2) / 2), int((y1 + y2) / 2)),
                    'size': int((x2 - x1) * (y2 - y1))  # bbox area
                }

                # Class 0 = basketball, Class 1 = hoop
                if cls == 0 and conf >= self.BASKETBALL_CONFIDENCE:
                    detections['all_balls'].append(box_data)
                elif cls == 1 and conf >= self.HOOP_CONFIDENCE:
                    detections['all_hoops'].append(box_data)

            # Select highest confidence detections
            if detections['all_balls']:
                detections['ball'] = max(detections['all_balls'], key=lambda x: x['confidence'])
            if detections['all_hoops']:
                detections['hoop'] = max(detections['all_hoops'], key=lambda x: x['confidence'])

        return detections

    def _check_line_crosses_hoop_boundary(self, ball_center: Tuple[int, int], prev_ball_center: Tuple[int, int],
                                          hoop_bbox: Tuple[int, int, int, int]) -> Dict:
        """
        Check if ball's vertical line crosses hoop boundaries and track which boundary

        Args:
            ball_center: (x, y) current ball center
            prev_ball_center: (x, y) previous ball center
            hoop_bbox: (x1, y1, x2, y2) hoop bounding box

        Returns:
            Dict with crossing info: {
                'crosses': bool,
                'crosses_top': bool,
                'crosses_bottom': bool,
                'moving_down': bool,
                'inside_horizontally': bool
            }
        """
        ball_x, ball_y = ball_center
        prev_x, prev_y = prev_ball_center
        hoop_x1, hoop_y1, hoop_x2, hoop_y2 = hoop_bbox

        # Check if ball is inside hoop horizontally (X coordinate)
        inside_horizontally = hoop_x1 <= ball_x <= hoop_x2

        # Check if ball is moving downward
        moving_down = ball_y > prev_y

        # Check if ball crosses TOP boundary of hoop (entering from above)
        # Ball crosses top if: previous Y was above top, current Y is at/below top
        crosses_top = prev_y < hoop_y1 and ball_y >= hoop_y1 and inside_horizontally

        # Check if ball crosses BOTTOM boundary of hoop (exiting through bottom)
        # Ball crosses bottom if: previous Y was above bottom, current Y is at/below bottom
        crosses_bottom = prev_y < hoop_y2 and ball_y >= hoop_y2 and inside_horizontally

        return {
            'crosses': crosses_top or crosses_bottom,
            'crosses_top': crosses_top,
            'crosses_bottom': crosses_bottom,
            'moving_down': moving_down,
            'inside_horizontally': inside_horizontally
        }

    def extract_spatial_features(self, ball_bbox, hoop_bbox, trajectory):
        """
        Extract spatial and trajectory features for fusion

        Args:
            ball_bbox: (x1, y1, x2, y2) ball bounding box
            hoop_bbox: (x1, y1, x2, y2) hoop bounding box
            trajectory: list of ball position dicts with 'center' key

        Returns:
            dict: Spatial feature dictionary
        """
        if not ball_bbox or not hoop_bbox:
            return {}

        # Calculate centers
        ball_center = ((ball_bbox[0] + ball_bbox[2]) / 2, (ball_bbox[1] + ball_bbox[3]) / 2)
        hoop_center = ((hoop_bbox[0] + hoop_bbox[2]) / 2, (hoop_bbox[1] + hoop_bbox[3]) / 2)

        # Calculate relative position
        horizontal_offset = ball_center[0] - hoop_center[0]
        vertical_offset = ball_center[1] - hoop_center[1]
        distance = np.sqrt(horizontal_offset**2 + vertical_offset**2)

        # Calculate ball size
        ball_width = ball_bbox[2] - ball_bbox[0]
        ball_height = ball_bbox[3] - ball_bbox[1]
        ball_size = max(ball_width, ball_height)

        # Calculate movement direction from trajectory
        lateral_velocity = 0.0
        ball_moving_left = False
        ball_moving_right = False

        if trajectory and len(trajectory) >= 2:
            # Get recent positions (last 5 or all if less)
            recent_positions = trajectory[-5:] if len(trajectory) >= 5 else trajectory

            if len(recent_positions) >= 2:
                # Extract x coordinates from center
                x_coords = [pos['center'][0] for pos in recent_positions]

                # Calculate lateral movement
                dx = x_coords[-1] - x_coords[0]
                lateral_velocity = dx / len(recent_positions)

                # Determine direction (threshold of 1.0 pixel per frame)
                ball_moving_left = lateral_velocity < -1.0
                ball_moving_right = lateral_velocity > 1.0

        return {
            "ball_hoop_horizontal_offset": horizontal_offset,
            "ball_hoop_vertical_offset": vertical_offset,
            "ball_distance_to_hoop": distance,
            "ball_moving_left": ball_moving_left,
            "ball_moving_right": ball_moving_right,
            "lateral_velocity": lateral_velocity,
            "ball_size": ball_size,
        }

    def classify_shot(self, shot_sequence: Dict) -> Dict:
        """
        Classify shot using SIMPLIFIED LINE INTERSECTION LOGIC

        Logic:
        1. For each ball position, check if vertical line through ball center intersects hoop bbox
        2. For positions where line intersects, check ball-to-hoop size ratio
        3. If ratio is correct (ball at hoop depth, not in front), count as valid intersection
        4. Decision: If enough valid intersections → MADE, else → MISSED

        Args:
            shot_sequence: Dictionary containing shot data

        Returns:
            Classification results
        """
        ball_positions = shot_sequence['ball_positions']
        ball_sizes = shot_sequence.get('ball_sizes', [])
        hoop_position = shot_sequence['hoop_position']
        frames_in_zone = len(shot_sequence['frames_in_zone'])

        # Get hoop bounding box and size
        if self.hoop_bbox is not None:
            hoop_x1, hoop_y1, hoop_x2, hoop_y2 = self.hoop_bbox
            hoop_size = self.hoop_size or ((hoop_x2 - hoop_x1) * (hoop_y2 - hoop_y1))
        else:
            # Fallback: estimate hoop box
            hoop_x, hoop_y = hoop_position
            hoop_x1, hoop_y1 = hoop_x - 30, hoop_y - 30
            hoop_x2, hoop_y2 = hoop_x + 30, hoop_y + 30
            hoop_size = 60 * 60

        hoop_bbox = (hoop_x1, hoop_y1, hoop_x2, hoop_y2)

        # Track boundary crossings and movement
        crosses_top_count = 0
        crosses_bottom_count = 0
        valid_top_crossings = 0  # Top crossings with correct depth and downward movement
        valid_bottom_crossings = 0  # Bottom crossings with correct depth
        size_ratios = []

        # Track first bottom crossing index to check for bounce back
        first_bottom_crossing_idx = None

        for i in range(1, len(ball_positions)):
            prev_center = ball_positions[i-1]
            curr_center = ball_positions[i]

            # Check boundary crossings
            crossing_info = self._check_line_crosses_hoop_boundary(curr_center, prev_center, hoop_bbox)

            if crossing_info['crosses_top']:
                crosses_top_count += 1

                # Valid top crossing: moving downward + correct size ratio
                if crossing_info['moving_down']:
                    if i < len(ball_sizes) and hoop_size > 0:
                        ball_size = ball_sizes[i]
                        size_ratio = ball_size / hoop_size
                        size_ratios.append(size_ratio)

                        if self.MIN_BALL_HOOP_RATIO <= size_ratio <= self.MAX_BALL_HOOP_RATIO:
                            valid_top_crossings += 1

            if crossing_info['crosses_bottom']:
                crosses_bottom_count += 1

                # Track first bottom crossing for bounce detection
                if first_bottom_crossing_idx is None:
                    first_bottom_crossing_idx = i

                # Valid bottom crossing: correct size ratio
                if i < len(ball_sizes) and hoop_size > 0:
                    ball_size = ball_sizes[i]
                    size_ratio = ball_size / hoop_size

                    if self.MIN_BALL_HOOP_RATIO <= size_ratio <= self.MAX_BALL_HOOP_RATIO:
                        valid_bottom_crossings += 1

        # Calculate metrics
        avg_size_ratio = sum(size_ratios) / len(size_ratios) if size_ratios else 0
        total_points = len(ball_positions)

        # DETECT RIM BOUNCE OUT: Check for upward movement after bottom crossing
        bounced_back_out = False
        bounce_upward = 0

        if valid_bottom_crossings >= 1 and first_bottom_crossing_idx is not None:
            # Check movement after first bottom crossing
            if first_bottom_crossing_idx < len(ball_positions) - 1:
                bottom_y = ball_positions[first_bottom_crossing_idx][1]

                # Check if ball moved significantly upward after crossing bottom
                for j in range(first_bottom_crossing_idx + 1, len(ball_positions)):
                    current_y = ball_positions[j][1]
                    upward_movement = bottom_y - current_y  # Negative Y = upward

                    if upward_movement > bounce_upward:
                        bounce_upward = upward_movement

                # If ball moved up 50+ pixels after crossing bottom → bounced out
                # V2: Increased from 30px - stricter rim bounce detection
                # (in-and-out or rim roll out)
                if bounce_upward > 50:
                    bounced_back_out = True

        # DECISION LOGIC:
        # 1. Must cross TOP boundary while moving DOWN with correct depth → entering hoop
        # 2. If ALSO crosses BOTTOM boundary → went through completely → higher confidence
        # 3. Check for rim bounce out (ball went through but bounced back up)
        # V2: Added stricter validation for "entered_from_top" cases

        if valid_top_crossings >= 1:
            # Check for rim bounce out FIRST (overrides made decision)
            if bounced_back_out:
                outcome = 'missed'
                reason = f'rim_bounce_out (passed through but bounced back up {bounce_upward:.0f}px, in-and-out)'
                confidence = 0.90
            else:
                outcome = 'made'

                # Check if also crossed bottom (complete pass-through)
                if valid_bottom_crossings >= 1:
                    reason = f'complete_pass_through (top={valid_top_crossings}, bottom={valid_bottom_crossings}, ratio={avg_size_ratio:.3f})'
                    confidence = 0.95  # Very high confidence - entered and exited
                else:
                    # V2: For "entered_from_top" cases without bottom crossing,
                    # reduce confidence slightly to be more conservative
                    reason = f'entered_from_top (top={valid_top_crossings}, ratio={avg_size_ratio:.3f})'
                    confidence = 0.75  # REDUCED from 0.80 - more conservative without bottom confirmation
        else:
            # No valid top crossings
            if crosses_top_count >= 1:
                outcome = 'missed'
                reason = f'wrong_depth_or_direction (top_crosses={crosses_top_count} but wrong depth/direction, ratio={avg_size_ratio:.3f})'
                confidence = 0.85
            else:
                outcome = 'missed'
                reason = f'no_top_crossing (never entered from top)'
                confidence = 0.90

        return {
            'outcome': outcome,
            'outcome_reason': reason,
            'decision_confidence': confidence,
            'frames_in_zone': frames_in_zone,
            'valid_top_crossings': valid_top_crossings,
            'valid_bottom_crossings': valid_bottom_crossings,
            'crosses_top_count': crosses_top_count,
            'crosses_bottom_count': crosses_bottom_count,
            'avg_size_ratio': avg_size_ratio,
            'total_trajectory_points': total_points,
            'bounced_back_out': bounced_back_out,
            'bounce_upward_pixels': bounce_upward
        }

    def update_shot_tracking(self, detections: Dict):
        """Update shot tracking based on current detections"""
        ball = detections.get('ball')
        hoop = detections.get('hoop')

        # Update trajectory with ball size
        if ball is not None:
            self.ball_trajectory.append({
                'frame': self.frame_count,
                'center': ball['center'],
                'size': ball['size']
            })

        # Update hoop position and bbox
        if hoop is not None:
            self.hoop_position = hoop['center']
            self.hoop_bbox = hoop['bbox']
            self.hoop_size = hoop['size']

        if ball is None or hoop is None:
            self.frames_since_last_shot += 1
            if self.current_shot_sequence is not None:
                timeout_frames = int(self.SHOT_SEQUENCE_TIMEOUT * self.fps)
                if self.frames_since_last_shot > timeout_frames:
                    self._finalize_shot_sequence()
            return

        # Check if ball is in hoop zone
        ball_x, ball_y = ball['center']
        hoop_x, hoop_y = hoop['center']

        dx = abs(ball_x - hoop_x)
        dy = abs(ball_y - hoop_y)

        in_zone = dx <= self.HOOP_ZONE_WIDTH and dy <= self.HOOP_ZONE_VERTICAL

        if in_zone:
            self.frames_since_last_shot = 0

            if self.current_shot_sequence is None:
                # Start new shot sequence
                self.current_shot_sequence = {
                    'start_frame': self.frame_count,
                    'ball_positions': [],
                    'ball_sizes': [],
                    'hoop_position': hoop['center'],
                    'frames_in_zone': []
                }

            # Add to current sequence
            self.current_shot_sequence['ball_positions'].append(ball['center'])
            self.current_shot_sequence['ball_sizes'].append(ball['size'])
            self.current_shot_sequence['frames_in_zone'].append(self.frame_count)
            self.current_shot_sequence['end_frame'] = self.frame_count

        else:
            self.frames_since_last_shot += 1
            if self.current_shot_sequence is not None:
                timeout_frames = int(self.SHOT_SEQUENCE_TIMEOUT * self.fps)
                if self.frames_since_last_shot > timeout_frames:
                    self._finalize_shot_sequence()

    def _finalize_shot_sequence(self):
        """Finalize and classify current shot sequence"""
        if self.current_shot_sequence is None:
            return

        # Only process if we have minimum frames
        if len(self.current_shot_sequence['frames_in_zone']) >= self.MIN_FRAMES_IN_ZONE:
            # Classify shot
            classification = self.classify_shot(self.current_shot_sequence)

            # Calculate timestamp
            start_frame = self.current_shot_sequence['start_frame']
            end_frame = self.current_shot_sequence['end_frame']
            timestamp = (start_frame + end_frame) / 2 / self.fps

            # Extract spatial features for fusion
            # Get ball bbox from last position in zone
            ball_bbox = None
            if self.current_shot_sequence['ball_positions']:
                last_ball_center = self.current_shot_sequence['ball_positions'][-1]
                last_ball_size = self.current_shot_sequence['ball_sizes'][-1] if self.current_shot_sequence['ball_sizes'] else 0

                if last_ball_size > 0:
                    # Estimate bbox from center and size
                    ball_radius = int(np.sqrt(last_ball_size) / 2)
                    ball_bbox = (
                        last_ball_center[0] - ball_radius,
                        last_ball_center[1] - ball_radius,
                        last_ball_center[0] + ball_radius,
                        last_ball_center[1] + ball_radius
                    )

            # Convert ball_trajectory deque to list for spatial feature extraction
            trajectory_list = list(self.ball_trajectory)

            spatial_features = self.extract_spatial_features(
                ball_bbox=ball_bbox,
                hoop_bbox=self.hoop_bbox,
                trajectory=trajectory_list
            )

            # Create shot record
            shot = {
                'timestamp_seconds': round(timestamp, 1),
                'start_frame': start_frame,
                'end_frame': end_frame,
                'outcome': classification['outcome'],
                'outcome_reason': classification['outcome_reason'],
                'confidence': classification['decision_confidence'],
                'valid_top_crossings': classification['valid_top_crossings'],
                'valid_bottom_crossings': classification['valid_bottom_crossings'],
                'avg_size_ratio': classification['avg_size_ratio'],
                'bounced_back_out': classification['bounced_back_out'],
                'bounce_upward_pixels': classification['bounce_upward_pixels'],
                'frames_in_zone': len(self.current_shot_sequence['frames_in_zone']),
                'spatial_features': spatial_features
            }

            self.detected_shots.append(shot)

            # Update stats
            self.stats['total_shots'] += 1
            if classification['outcome'] == 'made':
                self.stats['made_shots'] += 1
            else:
                self.stats['missed_shots'] += 1

            self.logger.info(f"Shot detected at {timestamp:.1f}s: {classification['outcome'].upper()} "
                           f"({classification['outcome_reason']}, conf={classification['decision_confidence']:.2f})")

        # Reset sequence
        self.current_shot_sequence = None

    def draw_overlay(self, frame: np.ndarray, detections: Dict) -> np.ndarray:
        """Draw detection overlay on frame"""
        annotated = frame.copy()

        # Draw ball
        if detections.get('ball'):
            ball = detections['ball']
            x1, y1, x2, y2 = ball['bbox']
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(annotated, ball['center'], 5, (0, 255, 0), -1)

        # Draw hoop
        if detections.get('hoop'):
            hoop = detections['hoop']
            x1, y1, x2, y2 = hoop['bbox']
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)

            # Draw hoop zone
            hoop_x, hoop_y = hoop['center']
            zone_x1 = hoop_x - self.HOOP_ZONE_WIDTH
            zone_x2 = hoop_x + self.HOOP_ZONE_WIDTH
            zone_y1 = hoop_y - self.HOOP_ZONE_VERTICAL
            zone_y2 = hoop_y + self.HOOP_ZONE_VERTICAL
            cv2.rectangle(annotated, (zone_x1, zone_y1), (zone_x2, zone_y2), (255, 255, 0), 1)

        # Draw trajectory
        if len(self.ball_trajectory) > 1:
            points = [entry['center'] for entry in self.ball_trajectory]
            for i in range(1, len(points)):
                cv2.line(annotated, points[i-1], points[i], (255, 0, 255), 2)

        # Draw stats
        cv2.putText(annotated, f"Shots: {self.stats['total_shots']} | Made: {self.stats['made_shots']} | Missed: {self.stats['missed_shots']}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return annotated

    def save_results(self, output_path: str):
        """Save detection results to JSON"""
        results = {
            'stats': self.stats,
            'shots': self.detected_shots
        }

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        self.logger.info(f"Results saved to {output_path}")


def test_timestamps(video_path: str, model_path: str, test_timestamps: List[float],
                   ground_truth_path: Optional[str] = None):
    """
    Test specific timestamps to validate the new logic

    Args:
        video_path: Path to video file
        model_path: Path to YOLO model
        test_timestamps: List of timestamps to test (in seconds)
        ground_truth_path: Optional path to ground truth JSON
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Testing {len(test_timestamps)} timestamps: {test_timestamps}")

    # Load ground truth if provided
    ground_truth = {}
    if ground_truth_path and Path(ground_truth_path).exists():
        with open(ground_truth_path) as f:
            gt_data = json.load(f)
            for shot in gt_data:
                ts = shot['timestamp_seconds']
                ground_truth[ts] = shot['outcome']
        logger.info(f"Loaded ground truth with {len(ground_truth)} shots")

    # Initialize analyzer
    analyzer = SimplifiedShotAnalyzer(model_path)

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Failed to open video")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    analyzer.fps = fps

    logger.info(f"Video FPS: {fps}")

    # Test each timestamp
    for ts in test_timestamps:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing timestamp: {ts}s")

        # Calculate frame range (±3 seconds around timestamp)
        center_frame = int(ts * fps)
        start_frame = max(0, center_frame - int(3 * fps))
        end_frame = center_frame + int(3 * fps)

        # Reset analyzer for this test
        analyzer.detected_shots = []
        analyzer.current_shot_sequence = None
        analyzer.stats = {'total_shots': 0, 'made_shots': 0, 'missed_shots': 0}

        # Process frames
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        for frame_num in range(start_frame, end_frame):
            ret, frame = cap.read()
            if not ret:
                break

            analyzer.frame_count = frame_num
            detections = analyzer.detect_objects(frame)
            analyzer.update_shot_tracking(detections)

        # Finalize any pending sequences
        if analyzer.current_shot_sequence is not None:
            analyzer._finalize_shot_sequence()

        # Report results
        logger.info(f"Detected {len(analyzer.detected_shots)} shot(s)")
        for shot in analyzer.detected_shots:
            logger.info(f"  {shot['timestamp_seconds']}s: {shot['outcome'].upper()} "
                       f"(top={shot['valid_top_crossings']}, "
                       f"bottom={shot['valid_bottom_crossings']}, "
                       f"ratio={shot['avg_size_ratio']:.3f}, "
                       f"conf={shot['confidence']:.2f})")
            logger.info(f"    Reason: {shot['outcome_reason']}")

        # Compare with ground truth
        if ts in ground_truth:
            gt_outcome = ground_truth[ts]
            logger.info(f"  Ground truth: {gt_outcome.upper()}")

            # Find closest detected shot
            if analyzer.detected_shots:
                closest = min(analyzer.detected_shots, key=lambda s: abs(s['timestamp_seconds'] - ts))
                match = "✓" if closest['outcome'] == gt_outcome else "✗"
                logger.info(f"  Match: {match}")

    cap.release()
    logger.info(f"\n{'='*60}")
    logger.info("Timestamp testing complete!")


def process_full_game(video_path: str, model_path: str, output_dir: str,
                     ground_truth_path: Optional[str] = None,
                     start_time: Optional[float] = None,
                     end_time: Optional[float] = None):
    """
    Process full game with new logic

    Args:
        video_path: Path to video file
        model_path: Path to YOLO model
        output_dir: Output directory for results
        ground_truth_path: Optional path to ground truth JSON
        start_time: Optional start time in seconds
        end_time: Optional end time in seconds
    """
    logger = logging.getLogger(__name__)
    logger.info("Processing full game with simplified line intersection logic")

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize analyzer
    analyzer = SimplifiedShotAnalyzer(model_path)

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Failed to open video")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    analyzer.fps = fps

    logger.info(f"Video: {width}x{height} @ {fps:.2f} FPS, {total_frames} frames")

    # Calculate frame range
    start_frame = int(start_time * fps) if start_time else 0
    end_frame = int(end_time * fps) if end_time else total_frames

    # Setup video writer
    output_video_path = output_dir / "detected_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

    # Seek to start
    if start_frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    # Process frames
    logger.info(f"Processing frames {start_frame} to {end_frame}")
    processed = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_frame > end_frame:
                break

            analyzer.frame_count = current_frame
            detections = analyzer.detect_objects(frame)
            analyzer.update_shot_tracking(detections)

            annotated = analyzer.draw_overlay(frame, detections)
            out.write(annotated)

            processed += 1
            if processed % 100 == 0:
                progress = (current_frame - start_frame) / (end_frame - start_frame) * 100
                logger.info(f"Progress: {progress:.1f}% ({processed} frames)")

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    finally:
        cap.release()
        out.release()

    # Finalize any pending sequences
    if analyzer.current_shot_sequence is not None:
        analyzer._finalize_shot_sequence()

    # Save results
    results_path = output_dir / "detection_results.json"
    analyzer.save_results(str(results_path))

    # Compare with ground truth if provided
    if ground_truth_path and Path(ground_truth_path).exists():
        logger.info("\nComparing with ground truth...")
        with open(ground_truth_path) as f:
            gt_data = json.load(f)

        gt_dict = {shot['timestamp_seconds']: shot['outcome'] for shot in gt_data}

        matches = 0
        total = 0

        for shot in analyzer.detected_shots:
            ts = shot['timestamp_seconds']
            # Find closest ground truth (within 2 seconds)
            closest_gt = None
            min_diff = float('inf')

            for gt_ts in gt_dict.keys():
                diff = abs(ts - gt_ts)
                if diff < min_diff and diff <= 2.0:
                    min_diff = diff
                    closest_gt = gt_ts

            if closest_gt:
                total += 1
                if shot['outcome'] == gt_dict[closest_gt]:
                    matches += 1

        accuracy = (matches / total * 100) if total > 0 else 0
        logger.info(f"Accuracy: {matches}/{total} = {accuracy:.1f}%")

    logger.info(f"\n{'='*60}")
    logger.info("Processing complete!")
    logger.info(f"Detected shots: {analyzer.stats['total_shots']}")
    logger.info(f"Made: {analyzer.stats['made_shots']}")
    logger.info(f"Missed: {analyzer.stats['missed_shots']}")
    logger.info(f"Output video: {output_video_path}")
    logger.info(f"Results: {results_path}")


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='Simplified Far Angle Shot Detection - Line Intersection Logic')

    parser.add_argument('--mode', type=str, required=True, choices=['test', 'full'],
                       help='Mode: test (specific timestamps) or full (entire game)')
    parser.add_argument('--video', type=str, required=True, help='Path to video file')
    parser.add_argument('--model', type=str, required=True, help='Path to YOLO model')
    parser.add_argument('--timestamps', type=str, help='Comma-separated timestamps for test mode (e.g., "26.8,63.1,91.7")')
    parser.add_argument('--ground_truth', type=str, help='Path to ground truth JSON')
    parser.add_argument('--output_dir', type=str, help='Output directory for full mode')
    parser.add_argument('--start_time', type=float, help='Start time in seconds')
    parser.add_argument('--end_time', type=float, help='End time in seconds')

    args = parser.parse_args()

    if args.mode == 'test':
        if not args.timestamps:
            print("Error: --timestamps required for test mode")
            return

        timestamps = [float(t.strip()) for t in args.timestamps.split(',')]
        test_timestamps(args.video, args.model, timestamps, args.ground_truth)

    elif args.mode == 'full':
        if not args.output_dir:
            print("Error: --output_dir required for full mode")
            return

        process_full_game(args.video, args.model, args.output_dir,
                         args.ground_truth, args.start_time, args.end_time)


if __name__ == "__main__":
    main()
