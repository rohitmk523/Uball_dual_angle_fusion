#!/usr/bin/env python3
"""
Far Angle Basketball Shot Detection

This module implements shot detection logic optimized for far angle camera views.
Uses zone-based tracking and vertical passage detection instead of IoU overlap.
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


class ShotAnalyzer:
    """Analyzes basketball shots from far angle camera perspective"""

    # Far angle specific parameters
    HOOP_ZONE_WIDTH = 80          # Pixels on each side of hoop center X
    HOOP_ZONE_VERTICAL = 100      # Vertical zone height around hoop Y

    # Shot detection thresholds - OPTIMIZED FOR FAR ANGLE ADVANTAGES
    MIN_FRAMES_IN_ZONE = 5        # Minimum frames to be considered a shot attempt
    MIN_VERTICAL_MOVEMENT = 60    # Minimum downward pixels for made shot

    # RIM BOUNCE DETECTION (FAR ANGLE ADVANTAGE #1) - OPTIMIZED
    # Based on actual rim bounce analysis: avg 24 frames, 177px upward, 1.47x up/down ratio
    RIM_BOUNCE_MIN_FRAMES = 20    # Lowered from 30 (actual avg: 24 frames)
    RIM_BOUNCE_UPWARD_MIN = 35    # Significant upward movement (actual avg: 177px)
    RIM_BOUNCE_RATIO = 1.2        # Upward/downward ratio threshold (actual avg: 1.47)

    # CLEAN SWISH DETECTION (FAR ANGLE ADVANTAGE #2) - WORKING PERFECTLY
    # Based on actual clean makes: avg 5px upward, 0.975 consistency
    SWISH_MAX_UPWARD = 20         # Minimal upward for clean make (actual avg: 5px)
    SWISH_MIN_CONSISTENCY = 0.85  # Very smooth trajectory (actual avg: 0.975)

    # General trajectory thresholds
    MIN_CONSISTENCY = 0.60        # Raised from 0.55 to reduce false positives

    # Confidence thresholds
    BASKETBALL_CONFIDENCE = 0.35
    HOOP_CONFIDENCE = 0.5

    # Shot sequence grouping
    SHOT_SEQUENCE_TIMEOUT = 3.0   # seconds
    POST_SHOT_TRACKING_FRAMES = 20

    # Visualization
    TRAJECTORY_LENGTH = 30        # Number of points to show in trajectory

    def __init__(self, model_path: str):
        """Initialize the shot analyzer

        Args:
            model_path: Path to trained YOLO model
        """
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        # Load YOLO model
        self.logger.info(f"Loading YOLO model from: {model_path}")
        self.model = YOLO(model_path)

        # Initialize tracking variables
        self.detected_shots = []
        self.current_shot_sequence = None
        self.frames_since_last_shot = 0
        self.frame_count = 0
        self.fps = 30  # Will be updated when processing video

        # Trajectory tracking
        self.ball_trajectory = deque(maxlen=self.TRAJECTORY_LENGTH)
        self.hoop_position = None
        self.hoop_bbox = None

        # Statistics
        self.stats = {
            'total_shots': 0,
            'made_shots': 0,
            'missed_shots': 0,
            'undetermined_shots': 0
        }

        self.logger.info("ShotAnalyzer initialized for far angle detection")

    def detect_objects(self, frame: np.ndarray) -> Dict:
        """Run YOLO inference on frame and extract detections

        Args:
            frame: Input video frame

        Returns:
            Dictionary containing ball and hoop detections
        """
        results = self.model(frame, verbose=False)[0]

        detections = {
            'ball': None,
            'hoop': None,
            'frame': self.frame_count
        }

        # Parse YOLO results
        for box in results.boxes:
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = results.names[class_id]

            # Get bounding box coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            width = x2 - x1
            height = y2 - y1

            # Detect basketball (case-insensitive)
            if class_name.lower() == 'basketball' and confidence >= self.BASKETBALL_CONFIDENCE:
                if detections['ball'] is None or confidence > detections['ball']['confidence']:
                    detections['ball'] = {
                        'bbox': (x1, y1, x2, y2),
                        'center': (center_x, center_y),
                        'width': width,
                        'height': height,
                        'confidence': confidence
                    }

            # Detect hoop (case-insensitive, matches both 'hoop' and 'basketball hoop')
            elif 'hoop' in class_name.lower() and confidence >= self.HOOP_CONFIDENCE:
                if detections['hoop'] is None or confidence > detections['hoop']['confidence']:
                    detections['hoop'] = {
                        'bbox': (x1, y1, x2, y2),
                        'center': (center_x, center_y),
                        'width': width,
                        'height': height,
                        'confidence': confidence
                    }
                    # Update hoop position tracking
                    self.hoop_position = (center_x, center_y)
                    self.hoop_bbox = (x1, y1, x2, y2)

        return detections

    def is_ball_in_hoop_zone(self, ball_center: Tuple[int, int],
                            hoop_center: Tuple[int, int]) -> bool:
        """Check if ball center is within hoop vertical zone

        Args:
            ball_center: (x, y) tuple of ball center
            hoop_center: (x, y) tuple of hoop center

        Returns:
            True if ball is in zone
        """
        if ball_center is None or hoop_center is None:
            return False

        x_in_zone = abs(ball_center[0] - hoop_center[0]) <= self.HOOP_ZONE_WIDTH
        y_in_zone = abs(ball_center[1] - hoop_center[1]) <= self.HOOP_ZONE_VERTICAL

        return x_in_zone and y_in_zone

    def detect_vertical_passage(self, ball_positions: List[Tuple[int, int]],
                               hoop_y: int) -> Dict:
        """Detect if ball passed vertically through hoop zone

        Checks:
        1. Ball starts above hoop (y < hoop_y)
        2. Ball ends below hoop (y > hoop_y)
        3. Ball maintains horizontal alignment during passage

        Args:
            ball_positions: List of (x, y) ball positions
            hoop_y: Y coordinate of hoop center

        Returns:
            Dictionary with passage analysis
        """
        if len(ball_positions) < 2:
            return {
                'passed_through': False,
                'downward_movement': 0,
                'upward_movement': 0,
                'consistency': 0,
                'crossed_vertically': False
            }

        # Calculate vertical movements
        downward_movement = 0
        upward_movement = 0

        for i in range(1, len(ball_positions)):
            y_prev = ball_positions[i-1][1]
            y_curr = ball_positions[i][1]
            y_diff = y_curr - y_prev

            if y_diff > 0:  # Downward movement (y increases downward in image)
                downward_movement += y_diff
            else:  # Upward movement
                upward_movement += abs(y_diff)

        # Calculate trajectory consistency
        total_movement = downward_movement + upward_movement
        consistency = downward_movement / total_movement if total_movement > 0 else 0

        # Check if ball crossed hoop vertically
        first_y = ball_positions[0][1]
        last_y = ball_positions[-1][1]
        crossed_vertically = first_y < hoop_y < last_y

        # Passed through if crossed vertically with sufficient downward movement
        passed_through = (
            crossed_vertically and
            downward_movement >= self.MIN_VERTICAL_MOVEMENT and
            consistency >= self.MIN_CONSISTENCY
        )

        return {
            'passed_through': passed_through,
            'downward_movement': downward_movement,
            'upward_movement': upward_movement,
            'consistency': consistency,
            'crossed_vertically': crossed_vertically
        }

    def classify_shot(self, shot_sequence: Dict) -> Dict:
        """Classify shot as MADE or MISSED - FOCUSED ON FAR ANGLE ADVANTAGES

        FAR ANGLE ADVANTAGE #1 - Rim Bounce Detection:
          Ball bouncing on rim then dropping = MISSED
          (Near angle struggles with this)

        FAR ANGLE ADVANTAGE #2 - Clean Swish Detection:
          Ball going straight through without touching = MADE
          (Near angle sometimes misses these)

        Args:
            shot_sequence: Dictionary containing shot data

        Returns:
            Classification results
        """
        ball_positions = shot_sequence['ball_positions']
        hoop_y = shot_sequence['hoop_position'][1]
        frames_in_zone = len(shot_sequence['frames_in_zone'])

        # Analyze vertical passage
        passage_analysis = self.detect_vertical_passage(ball_positions, hoop_y)

        downward = passage_analysis['downward_movement']
        upward = passage_analysis['upward_movement']
        consistency = passage_analysis['consistency']
        crossed_vertically = passage_analysis['crossed_vertically']

        # === OPTIMIZED DECISION LOGIC - RIM BOUNCE FIRST ===

        # Rule 1: Too few frames - not a real shot attempt
        if frames_in_zone < self.MIN_FRAMES_IN_ZONE:
            outcome = 'missed'
            reason = f'insufficient_frames ({frames_in_zone})'
            confidence = 0.6

        # Rule 2: Insufficient downward movement - didn't go through
        elif downward < self.MIN_VERTICAL_MOVEMENT:
            outcome = 'missed'
            reason = f'insufficient_downward ({downward:.0f}px)'
            confidence = 0.75

        # ===== FAR ANGLE ADVANTAGE #1: RIM BOUNCE DETECTION (PRIORITY) =====
        # Optimized based on analysis: avg 24 frames, 177px upward, 1.47x ratio
        # Check BEFORE vertical crossing to catch rim bounces that near angle misses
        elif frames_in_zone >= self.RIM_BOUNCE_MIN_FRAMES and upward >= self.RIM_BOUNCE_UPWARD_MIN:
            outcome = 'missed'
            reason = f'rim_bounce_frames (frames:{frames_in_zone}, up:{upward:.0f}px)'
            confidence = 0.95

        # NEW: Rim bounce by Up/Down ratio - even if fewer frames
        elif downward > 0 and upward / downward > self.RIM_BOUNCE_RATIO:
            outcome = 'missed'
            reason = f'rim_bounce_ratio (up:{upward:.0f}px > down:{downward:.0f}px, ratio:{upward/downward:.2f})'
            confidence = 0.90

        # Rule 3: Didn't cross hoop vertically (after rim bounce checks)
        elif not crossed_vertically:
            outcome = 'missed'
            reason = 'no_vertical_crossing'
            confidence = 0.75

        # ===== FAR ANGLE ADVANTAGE #2: CLEAN SWISH DETECTION =====
        # Clean make - minimal upward, smooth trajectory - MADE
        elif upward <= self.SWISH_MAX_UPWARD and consistency >= self.SWISH_MIN_CONSISTENCY:
            outcome = 'made'
            reason = f'clean_swish (up:{upward:.0f}px, cons:{consistency:.2f})'
            confidence = 0.95

        # Rule 6: General made shot - good consistency, crossed vertically
        elif consistency >= self.MIN_CONSISTENCY and crossed_vertically:
            outcome = 'made'
            reason = f'made_shot (cons:{consistency:.2f})'
            confidence = min(0.85, 0.7 + consistency * 0.2)

        # Rule 7: High upward movement - likely rim bounce or miss
        elif upward > downward * 0.6:
            outcome = 'missed'
            reason = f'high_upward (up:{upward:.0f}px vs down:{downward:.0f}px)'
            confidence = 0.80

        # Default: Insufficient consistency or unclear pattern
        else:
            outcome = 'missed'
            reason = f'low_consistency ({consistency:.2f})'
            confidence = 0.70

        return {
            'outcome': outcome,
            'outcome_reason': reason,
            'decision_confidence': confidence,
            'frames_in_zone': frames_in_zone,
            'vertical_passage': crossed_vertically,
            'downward_movement': downward,
            'upward_movement': upward,
            'trajectory_consistency': consistency
        }

    def update_shot_tracking(self, detections: Dict):
        """Update shot tracking based on current detections

        Args:
            detections: Current frame detections from detect_objects()
        """
        ball = detections.get('ball')
        hoop = detections.get('hoop')

        # Update trajectory
        if ball is not None:
            self.ball_trajectory.append({
                'frame': self.frame_count,
                'position': ball['center'],
                'in_zone': False
            })

        # Check if ball is in hoop zone
        if ball is not None and hoop is not None:
            ball_center = ball['center']
            hoop_center = hoop['center']
            in_zone = self.is_ball_in_hoop_zone(ball_center, hoop_center)

            # Update trajectory marker
            if len(self.ball_trajectory) > 0:
                self.ball_trajectory[-1]['in_zone'] = in_zone

            # Start or continue shot sequence
            if in_zone:
                if self.current_shot_sequence is None:
                    # Start new shot sequence
                    self.current_shot_sequence = {
                        'start_frame': self.frame_count,
                        'frames_in_zone': [self.frame_count],
                        'ball_positions': [ball_center],
                        'hoop_position': hoop_center,
                        'last_frame_in_zone': self.frame_count
                    }
                else:
                    # Continue existing sequence
                    self.current_shot_sequence['frames_in_zone'].append(self.frame_count)
                    self.current_shot_sequence['ball_positions'].append(ball_center)
                    self.current_shot_sequence['last_frame_in_zone'] = self.frame_count

                self.frames_since_last_shot = 0
            else:
                # Ball not in zone
                if self.current_shot_sequence is not None:
                    self.frames_since_last_shot += 1
        else:
            # Missing detection
            if self.current_shot_sequence is not None:
                self.frames_since_last_shot += 1

        # Finalize shot if timeout reached
        if self.current_shot_sequence is not None:
            timeout_frames = int(self.SHOT_SEQUENCE_TIMEOUT * self.fps)
            if self.frames_since_last_shot > timeout_frames:
                self._finalize_shot()

    def _finalize_shot(self):
        """Finalize and classify the current shot sequence"""
        if self.current_shot_sequence is None:
            return

        # Classify the shot
        classification = self.classify_shot(self.current_shot_sequence)

        # Calculate timestamp
        timestamp_seconds = self.current_shot_sequence['start_frame'] / self.fps

        # Build shot record
        shot_record = {
            'timestamp_seconds': timestamp_seconds,
            'frame': self.current_shot_sequence['start_frame'],
            'outcome': classification['outcome'],
            'outcome_reason': classification['outcome_reason'],
            'decision_confidence': classification['decision_confidence'],
            'detection_confidence': np.mean([
                pos[0] for pos in self.current_shot_sequence['ball_positions']
            ]) if self.current_shot_sequence['ball_positions'] else 0.0,

            # Far angle specific data
            'frames_in_zone': classification['frames_in_zone'],
            'vertical_passage': classification['vertical_passage'],
            'downward_movement': classification['downward_movement'],
            'upward_movement': classification['upward_movement'],
            'trajectory_consistency': classification['trajectory_consistency'],

            # Position data
            'ball_final_position': list(self.current_shot_sequence['ball_positions'][-1]),
            'hoop_position': list(self.current_shot_sequence['hoop_position']),
            'zone_width': self.HOOP_ZONE_WIDTH,

            # Trajectory
            'trajectory': [
                {
                    'frame': self.current_shot_sequence['frames_in_zone'][i],
                    'x': int(pos[0]),
                    'y': int(pos[1])
                }
                for i, pos in enumerate(self.current_shot_sequence['ball_positions'])
            ]
        }

        # Add to detected shots
        self.detected_shots.append(shot_record)

        # Update statistics
        self.stats['total_shots'] += 1
        if classification['outcome'] == 'made':
            self.stats['made_shots'] += 1
        elif classification['outcome'] == 'missed':
            self.stats['missed_shots'] += 1
        else:
            self.stats['undetermined_shots'] += 1

        # Log detection
        self.logger.info(
            f"Shot detected at {timestamp_seconds:.1f}s: {classification['outcome'].upper()} "
            f"(confidence: {classification['decision_confidence']:.2f}, "
            f"reason: {classification['outcome_reason']})"
        )

        # Reset for next shot
        self.current_shot_sequence = None
        self.frames_since_last_shot = 0

    def draw_overlay(self, frame: np.ndarray, detections: Dict) -> np.ndarray:
        """Draw detection overlay on frame

        Args:
            frame: Input frame
            detections: Current detections

        Returns:
            Annotated frame
        """
        annotated = frame.copy()

        ball = detections.get('ball')
        hoop = detections.get('hoop')

        # Draw hoop zone (vertical column)
        if hoop is not None:
            hoop_center = hoop['center']
            zone_color = (100, 255, 100)  # Green

            # Draw semi-transparent zone rectangle
            overlay = annotated.copy()
            zone_x1 = hoop_center[0] - self.HOOP_ZONE_WIDTH
            zone_x2 = hoop_center[0] + self.HOOP_ZONE_WIDTH
            zone_y1 = hoop_center[1] - self.HOOP_ZONE_VERTICAL
            zone_y2 = hoop_center[1] + self.HOOP_ZONE_VERTICAL

            cv2.rectangle(overlay, (zone_x1, zone_y1), (zone_x2, zone_y2),
                         zone_color, -1)
            cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, annotated)

            # Draw zone border
            cv2.rectangle(annotated, (zone_x1, zone_y1), (zone_x2, zone_y2),
                         zone_color, 2)

            # Draw hoop bounding box
            x1, y1, x2, y2 = hoop['bbox']
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated, f"Hoop {hoop['confidence']:.2f}",
                       (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                       (0, 255, 0), 2)

        # Draw ball
        if ball is not None:
            x1, y1, x2, y2 = ball['bbox']
            ball_center = ball['center']

            # Check if ball is in zone
            in_zone = False
            if hoop is not None:
                in_zone = self.is_ball_in_hoop_zone(ball_center, hoop['center'])

            # Color based on zone status
            ball_color = (0, 255, 255) if in_zone else (0, 255, 255)  # Yellow

            cv2.rectangle(annotated, (x1, y1), (x2, y2), ball_color, 2)
            cv2.circle(annotated, ball_center, 5, ball_color, -1)
            cv2.putText(annotated, f"Ball {ball['confidence']:.2f}",
                       (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                       ball_color, 2)

        # Draw ball trajectory
        if len(self.ball_trajectory) > 1:
            points = [pos['position'] for pos in self.ball_trajectory]
            for i in range(1, len(points)):
                # Color based on zone status
                in_zone = self.ball_trajectory[i]['in_zone']
                color = (0, 255, 0) if in_zone else (255, 255, 255)  # Green in zone, white otherwise
                cv2.line(annotated, points[i-1], points[i], color, 2)

        # Draw stats overlay (top-left corner)
        timestamp_seconds = self.frame_count / self.fps
        stats_y = 30
        stats_text = [
            f"Frame: {self.frame_count} | Time: {timestamp_seconds:.1f}s",
            f"Total Shots: {self.stats['total_shots']}",
            f"Made: {self.stats['made_shots']} | Missed: {self.stats['missed_shots']}"
        ]

        for i, text in enumerate(stats_text):
            y_pos = stats_y + (i * 30)
            # Background rectangle for readability
            (text_width, text_height), _ = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(annotated, (10, y_pos - 20),
                         (20 + text_width, y_pos + 5), (0, 0, 0), -1)
            cv2.putText(annotated, text, (15, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Show shot detection indicator
        if self.current_shot_sequence is not None:
            frames_in_zone = len(self.current_shot_sequence['frames_in_zone'])
            cv2.putText(annotated, f"TRACKING SHOT (Frames: {frames_in_zone})",
                       (15, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                       (0, 255, 255), 2)

        # Show recent shot result
        if len(self.detected_shots) > 0 and self.frames_since_last_shot < 60:
            last_shot = self.detected_shots[-1]
            outcome = last_shot['outcome'].upper()
            color = (0, 255, 0) if outcome == 'MADE' else (0, 0, 255)
            cv2.putText(annotated, f"LAST SHOT: {outcome}",
                       (15, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                       color, 3)

        return annotated

    def save_session_data(self, output_path: str, video_info: Dict = None):
        """Save session data to JSON file

        Args:
            output_path: Path for output JSON file
            video_info: Optional video metadata
        """
        # Finalize any pending shot
        if self.current_shot_sequence is not None:
            self._finalize_shot()

        session_data = {
            'video_path': video_info.get('video_path', '') if video_info else '',
            'model_path': video_info.get('model_path', '') if video_info else '',
            'fps': self.fps,
            'frame_count': self.frame_count,
            'duration_seconds': self.frame_count / self.fps if self.fps > 0 else 0,
            'processing_timestamp': datetime.now().isoformat(),
            'detection_version': 'far_angle_v1',

            'stats': self.stats,
            'shots': self.detected_shots,

            'session_info': {
                'detection_method': 'far_angle_zone_based',
                'model_path': video_info.get('model_path', '') if video_info else '',
                'start_time': video_info.get('start_time', '') if video_info else ''
            }
        }

        # Save to file
        output_file = Path(output_path)
        with open(output_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        self.logger.info(f"Session data saved to: {output_file}")
        self.logger.info(f"Total shots detected: {self.stats['total_shots']}")
        self.logger.info(f"Made: {self.stats['made_shots']}, Missed: {self.stats['missed_shots']}")

        return str(output_file)
