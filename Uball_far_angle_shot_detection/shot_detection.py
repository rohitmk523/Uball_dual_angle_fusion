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

    # Far angle specific parameters - MAXIMUM COVERAGE PRIORITY
    HOOP_ZONE_WIDTH = 120         # Very large zone to catch all shots including free throws
    HOOP_ZONE_VERTICAL = 130      # Very large vertical zone

    # Shot detection thresholds - MAXIMIZE DETECTION
    MIN_FRAMES_IN_ZONE = 1        # Even 1 frame counts as shot attempt
    MIN_VERTICAL_MOVEMENT = 15    # Very low threshold for free throws and flat shots
    MIN_BALL_HOOP_OVERLAP = 1.0   # Minimum % overlap between ball and hoop bbox

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
                               hoop_y: int, hoop_x: int = None) -> Dict:
        """Detect if ball passed vertically through hoop zone AND was within horizontal zone

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

        # Check if ball crossed hoop vertically AND was within hoop zone horizontally
        first_y = ball_positions[0][1]
        last_y = ball_positions[-1][1]
        crossed_y_level = first_y < hoop_y < last_y

        # IMPORTANT: Also check horizontal proximity AND crossing
        # Ball must CROSS hoop X position (not just approach it)
        # This prevents false positives from balls passing BESIDE the hoop
        crossed_vertically = False
        if crossed_y_level and hoop_x is not None:
            # Check if ball CROSSED the hoop X position horizontally
            # (went from one side to the other, within zone width)
            x_positions = [pos[0] for pos in ball_positions]
            min_x = min(x_positions)
            max_x = max(x_positions)

            # Ball must have crossed hoop X (hoop_x must be between min and max)
            # AND ball must have been close enough (within HOOP_ZONE_WIDTH)
            crossed_hoop_x = min_x <= hoop_x <= max_x
            was_close_enough = min(abs(min_x - hoop_x), abs(max_x - hoop_x)) <= self.HOOP_ZONE_WIDTH

            if crossed_hoop_x and was_close_enough:
                crossed_vertically = True
        elif crossed_y_level:
            # If hoop_x not provided, fall back to old behavior
            crossed_vertically = True

        # PHASE 2 FIX: Enhanced vertical crossing for high-arc shots (3-pointers)
        # For high-arc shots, ball may start below hoop Y due to perspective in far angle
        # Check for high-arc pattern: high upward + high downward + passes reasonably close to hoop Y
        if not crossed_vertically and hoop_x is not None:
            # High arc shot: >=140px upward AND >=150px downward
            is_high_arc = upward_movement >= 140 and downward_movement >= 150

            # Check if ball passes reasonably near hoop Y (±50px tolerance for perspective)
            passes_near_hoop_y = any(abs(pos[1] - hoop_y) <= 50 for pos in ball_positions)

            if is_high_arc and passes_near_hoop_y:
                # Also verify horizontal proximity
                x_positions = [pos[0] for pos in ball_positions]
                min_x = min(x_positions)
                max_x = max(x_positions)
                crossed_hoop_x = min_x <= hoop_x <= max_x
                was_close_enough = min(abs(min_x - hoop_x), abs(max_x - hoop_x)) <= self.HOOP_ZONE_WIDTH

                if crossed_hoop_x and was_close_enough:
                    crossed_vertically = True

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

    def detect_horizontal_rim_bounce(self, ball_positions: List, hoop_x: int) -> bool:
        """Detect if ball bounced off rim/backboard horizontally

        BALANCED FIX: Made STRICTER to avoid false positives on clean swishes.
        Only flags OBVIOUS horizontal bounces with large movement.

        Args:
            ball_positions: List of (x, y) ball positions
            hoop_x: Hoop center X coordinate

        Returns:
            True if horizontal rim bounce detected
        """
        if len(ball_positions) < 5:
            return False

        x_positions = [pos[0] for pos in ball_positions]

        # Calculate total horizontal range
        max_x = max(x_positions)
        min_x = min(x_positions)
        x_range = max_x - min_x

        # STRICTER: Only flag if VERY large range (>120px)
        # Clean swishes can have 50-80px horizontal movement
        if x_range > 120:
            return True

        # Count SIGNIFICANT direction changes (>15px moves, not 10px)
        # Require MORE changes (>5, not 3) to be confident it's a bounce
        direction_changes = 0
        for i in range(2, len(x_positions)):
            prev_direction = x_positions[i-1] - x_positions[i-2]
            curr_direction = x_positions[i] - x_positions[i-1]

            # Much stricter: >15px changes
            if prev_direction * curr_direction < 0 and abs(curr_direction) > 15:
                direction_changes += 1

        # Require more than 5 significant direction changes
        if direction_changes > 5:
            return True

        return False

    def _calculate_bbox_overlap(self, ball_bbox, hoop_bbox):
        """Calculate overlap percentage between ball and hoop bounding boxes

        Args:
            ball_bbox: (x1, y1, x2, y2) ball bounding box
            hoop_bbox: (x1, y1, x2, y2) hoop bounding box

        Returns:
            float: Percentage of ball bbox that overlaps with hoop bbox
        """
        ball_x1, ball_y1, ball_x2, ball_y2 = ball_bbox
        hoop_x1, hoop_y1, hoop_x2, hoop_y2 = hoop_bbox

        # Calculate overlap area
        x_overlap = max(0, min(ball_x2, hoop_x2) - max(ball_x1, hoop_x1))
        y_overlap = max(0, min(ball_y2, hoop_y2) - max(ball_y1, hoop_y1))
        overlap_area = x_overlap * y_overlap

        # Calculate ball area
        ball_area = (ball_x2 - ball_x1) * (ball_y2 - ball_y1)

        if ball_area == 0:
            return 0.0

        overlap_percentage = (overlap_area / ball_area) * 100
        return overlap_percentage

    def _validate_shot_entry_direction(self, trajectory):
        """Validate that ball approaches hoop from above or side, not from below

        This eliminates rebounds being counted as shots

        Args:
            trajectory: List of (x, y) ball positions

        Returns:
            bool: True if valid shot approach
        """
        if len(trajectory) < 2:
            return False

        first_point = trajectory[0]
        hoop_y = self.hoop_bbox[1] if self.hoop_bbox else self.hoop_position[1]

        # Ball must start above the hoop (at least 50px above)
        # This ensures we're tracking a shot coming down, not a rebound going up
        if first_point[1] < hoop_y - 50:
            return True

        return False

    def _line_crosses_hoop_vertically(self, p1, p2, hoop_box):
        """Check if line segment from p1 to p2 crosses through hoop box vertically

        Args:
            p1: (x, y) start point
            p2: (x, y) end point
            hoop_box: (x1, y1, x2, y2) hoop bounding box

        Returns:
            bool: True if line crosses hoop box from top to bottom
        """
        x1, y1 = p1
        x2, y2 = p2
        hoop_x1, hoop_y1, hoop_x2, hoop_y2 = hoop_box

        # Check if line segment goes downward (y2 > y1)
        if y2 <= y1:
            return False

        # Check if both points' X coordinates are within or crossing the hoop X bounds
        x_min = min(x1, x2)
        x_max = max(x1, x2)

        # Line must horizontally overlap with hoop box
        if x_max < hoop_x1 or x_min > hoop_x2:
            return False

        # Check if line crosses through the hoop Y bounds (top to bottom)
        # Line should enter from above (y1 <= hoop_y2) and exit below (y2 >= hoop_y1)
        crosses_top = y1 <= hoop_y2
        crosses_bottom = y2 >= hoop_y1

        return crosses_top and crosses_bottom

    def classify_shot(self, shot_sequence: Dict) -> Dict:
        """Classify shot as MADE or MISSED - LINE INTERSECTION LOGIC

        Improved approach:
        1. Check if trajectory LINE passes through the hoop bounding box vertically
        2. Count line segments that cross through the hoop (minimum 1 for swish)
        3. Count frames where ball is inside hoop box
        4. Combine both metrics for confidence
        5. If trajectory crosses through hoop downward → MADE, else → MISSED

        Args:
            shot_sequence: Dictionary containing shot data

        Returns:
            Classification results
        """
        ball_positions = shot_sequence['ball_positions']
        ball_sizes = shot_sequence.get('ball_sizes', [])  # Ball bbox areas for depth check
        hoop_x = shot_sequence['hoop_position'][0]
        hoop_y = shot_sequence['hoop_position'][1]
        frames_in_zone = len(shot_sequence['frames_in_zone'])

        # Calculate average ball size for depth estimation
        avg_ball_size = sum(ball_sizes) / len(ball_sizes) if ball_sizes else 0

        # Get hoop bounding box (using stored hoop_bbox if available)
        if self.hoop_bbox is not None:
            hoop_x1, hoop_y1, hoop_x2, hoop_y2 = self.hoop_bbox
        else:
            # Fallback: estimate hoop box from center (assume ~60px width/height)
            hoop_x1 = hoop_x - 30
            hoop_x2 = hoop_x + 30
            hoop_y1 = hoop_y - 30
            hoop_y2 = hoop_y + 30

        hoop_box = (hoop_x1, hoop_y1, hoop_x2, hoop_y2)

        # Calculate vertical movement metrics first (needed for all checks)
        downward = 0
        upward = 0
        for i in range(1, len(ball_positions)):
            y_diff = ball_positions[i][1] - ball_positions[i-1][1]
            if y_diff > 0:
                downward += y_diff
            else:
                upward += abs(y_diff)

        total_movement = downward + upward
        consistency = downward / total_movement if total_movement > 0 else 0

        # Calculate NET vertical displacement (final Y - start Y)
        # Positive = ball went down (MADE), Negative = ball bounced back up (MISSED)
        if len(ball_positions) >= 2:
            start_y = ball_positions[0][1]
            end_y = ball_positions[-1][1]
            net_vertical_displacement = end_y - start_y  # Positive = down, Negative = up
        else:
            net_vertical_displacement = 0

        # Rule 1: Too few frames - not a real shot attempt
        if frames_in_zone < self.MIN_FRAMES_IN_ZONE:
            outcome = 'missed'
            reason = f'insufficient_frames ({frames_in_zone})'
            confidence = 0.6
            points_inside = 0
            total_points = len(ball_positions)
            line_crossings = 0
            percentage_inside = 0.0

        # REMOVED: Don't check MIN_VERTICAL_MOVEMENT - free throws can be very flat
        # Proceed to trajectory analysis for all shots with enough frames

        else:
            # Metric 1: Count trajectory LINE SEGMENTS that cross through hoop box
            line_crossings = 0
            total_segments = 0

            for i in range(1, len(ball_positions)):
                p1 = ball_positions[i-1]
                p2 = ball_positions[i]
                total_segments += 1

                if self._line_crosses_hoop_vertically(p1, p2, hoop_box):
                    line_crossings += 1

            # Metric 2: Count tracking points inside hoop bounding box WITH DEPTH CHECK
            points_inside = 0
            points_inside_with_depth = 0  # Points inside at correct depth
            total_points = len(ball_positions)

            # Track ball size stats for debugging
            inside_ball_sizes = []
            outside_ball_sizes = []

            for i, ball_center in enumerate(ball_positions):
                ball_x, ball_y = ball_center
                is_inside = hoop_x1 <= ball_x <= hoop_x2 and hoop_y1 <= ball_y <= hoop_y2

                if is_inside:
                    points_inside += 1
                    if ball_sizes and i < len(ball_sizes):
                        inside_ball_sizes.append(ball_sizes[i])

                    # Depth check: if ball is larger than average, it's IN FRONT of hoop
                    if ball_sizes and i < len(ball_sizes):
                        ball_size = ball_sizes[i]
                        # Ball should be similar or smaller size when passing through hoop
                        # If >20% larger (tightened from 30%), it's likely in front of hoop
                        if avg_ball_size > 0 and ball_size <= avg_ball_size * 1.2:
                            points_inside_with_depth += 1
                else:
                    if ball_sizes and i < len(ball_sizes):
                        outside_ball_sizes.append(ball_sizes[i])

            # Calculate percentages
            percentage_inside = (points_inside / total_points * 100) if total_points > 0 else 0

            # Additional depth metric: compare average ball size inside vs outside
            avg_inside_size = sum(inside_ball_sizes) / len(inside_ball_sizes) if inside_ball_sizes else 0
            avg_outside_size = sum(outside_ball_sizes) / len(outside_ball_sizes) if outside_ball_sizes else 0

            # If ball is larger INSIDE than OUTSIDE, it's passing IN FRONT
            ball_size_ratio_inside_outside = avg_inside_size / avg_outside_size if avg_outside_size > 0 else 1.0

            # Decision Logic: Check for EXTREME bounces first, then made indicators

            # Calculate upward/downward ratio
            up_down_ratio = upward / downward if downward > 0 else 0

            # Rule 1: EXTREME upward movement = MISSED (hard bounce out)
            # Increased threshold to 300px - made shots can have 250-290px bounce
            if upward > 300:
                outcome = 'missed'
                reason = f'extreme_rim_bounce ({upward:.0f}px upward, bounced out hard)'
                confidence = 0.95

            # Rule 2: High up/down ratio = MISSED (bounced back out)
            # Made shots go DOWN more than UP, but allow some tolerance
            # With depth check, we can relax this slightly to 1.15
            elif upward > 100 and up_down_ratio > 1.15:
                outcome = 'missed'
                reason = f'rim_bounce_out ({upward:.0f}px upward, {up_down_ratio:.2f} ratio, bounced back out)'
                confidence = 0.90

            # Rule 3: Line crosses through hoop = MADE
            # Relaxed net_disp check: only reject EXTREME negative displacement (ball way back up)
            # Allow -50 to +∞ because tracking window is limited
            elif (line_crossings >= 2 or (line_crossings >= 1 and points_inside_with_depth >= 2)) and net_vertical_displacement > -50:
                outcome = 'made'
                reason = f'trajectory_through_hoop ({line_crossings} line crossings, {points_inside_with_depth} points inside at depth'
                if upward > 100:
                    reason += f', {upward:.0f}px rim bounce'
                reason += ')'

                # Confidence based on both metrics:
                # - Base: 0.75 for strong made indicators
                # - Bonus: +0.05 per additional crossing (up to 3)
                # - Bonus: +0.10 if 3+ points inside at depth
                confidence = 0.75
                confidence += min(0.10, (line_crossings - 1) * 0.05)
                if points_inside_with_depth >= 3:
                    confidence += 0.10
                confidence = min(0.95, confidence)

            # Rule 3x: Line crosses and points inside BUT ball bounced WAY back up
            # Only reject if ball ended MUCH higher (>50px up) = clear rim bounce out
            elif (line_crossings >= 1 and points_inside >= 2) and net_vertical_displacement <= -50:
                outcome = 'missed'
                reason = f'rim_bounce_back_out ({line_crossings} crossings, but ball bounced way back up, net_disp={net_vertical_displacement:.0f}px)'
                confidence = 0.85

            # Rule 3b: Ball larger INSIDE than OUTSIDE = passing IN FRONT of hoop
            # If ball is 10%+ larger when "inside" hoop bbox, it's actually in front (closer to camera)
            elif line_crossings >= 1 and points_inside >= 2 and ball_size_ratio_inside_outside > 1.1:
                outcome = 'missed'
                reason = f'ball_in_front_of_hoop ({line_crossings} crossings, but ball {ball_size_ratio_inside_outside:.2f}x larger inside vs outside)'
                confidence = 0.90

            # Rule 3c: Line crosses but points inside are at wrong depth (in front of hoop)
            # Ball passed through 2D hoop bbox but was actually in front
            elif line_crossings >= 1 and points_inside >= 2 and points_inside_with_depth < 2:
                outcome = 'missed'
                reason = f'ball_in_front_of_hoop ({line_crossings} crossings, {points_inside} points but only {points_inside_with_depth} at correct depth)'
                confidence = 0.85

            # Rule 4: Line crosses but ball barely inside hoop
            # With 2+ crossings and 1 point, likely a made shot (fast swish)
            # With 1 crossing and 1 point, could be grazed
            elif line_crossings == 1 and points_inside == 1:
                outcome = 'missed'
                reason = f'trajectory_grazed_hoop ({line_crossings} crossing, only {points_inside} point inside)'
                confidence = 0.70

            # Rule 5: Detect strong rim bounce with NO trajectory through hoop = missed
            elif upward > 150 and line_crossings == 0:
                outcome = 'missed'
                reason = f'rim_bounce_detected ({upward:.0f}px upward movement, no line crossings)'
                confidence = 0.90

            # Rule 6: Detect light rim contact (small upward movement = likely missed)
            elif upward > 20 and points_inside < 2 and line_crossings == 0:
                outcome = 'missed'
                reason = f'rim_contact_detected ({upward:.0f}px upward, {points_inside} points inside)'
                confidence = 0.80

            # Rule 7: No line crossings = clearly missed
            else:
                outcome = 'missed'
                reason = f'trajectory_beside_hoop ({line_crossings} line crossings, {percentage_inside:.1f}% inside)'

                # High confidence miss if no crossings
                confidence = 0.85
                # Reduce confidence if some points inside (might be close)
                if points_inside > 0:
                    confidence = max(0.70, 0.85 - (points_inside * 0.03))

        # Set crossed_vertically flag
        crossed_vertically = line_crossings > 0 if 'line_crossings' in locals() else False

        return {
            'outcome': outcome,
            'outcome_reason': reason,
            'decision_confidence': confidence,
            'frames_in_zone': frames_in_zone,
            'vertical_passage': crossed_vertically,
            'downward_movement': downward,
            'upward_movement': upward,
            'trajectory_consistency': consistency,
            'points_inside_hoop_box': points_inside,
            'total_trajectory_points': total_points,
            'percentage_inside_hoop': percentage_inside,
            'line_crossings_through_hoop': line_crossings
        }

    def update_shot_tracking(self, detections: Dict):
        """Update shot tracking based on current detections

        Args:
            detections: Current frame detections from detect_objects()
        """
        ball = detections.get('ball')
        hoop = detections.get('hoop')

        # Update trajectory with ball size for depth estimation
        if ball is not None:
            self.ball_trajectory.append({
                'frame': self.frame_count,
                'position': ball['center'],
                'bbox': ball['bbox'],
                'ball_size': ball['width'] * ball['height'],  # Ball area for depth check
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
                        'ball_sizes': [ball['width'] * ball['height']],  # Track ball area for depth
                        'hoop_position': hoop_center,
                        'last_frame_in_zone': self.frame_count
                    }
                else:
                    # Continue existing sequence
                    self.current_shot_sequence['frames_in_zone'].append(self.frame_count)
                    self.current_shot_sequence['ball_positions'].append(ball_center)
                    self.current_shot_sequence['ball_sizes'].append(ball['width'] * ball['height'])
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
