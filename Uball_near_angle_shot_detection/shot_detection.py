#!/usr/bin/env python3
"""
Basketball Shot Detection and Analysis

This module provides comprehensive basketball shot detection, tracking, and classification
capabilities using YOLOv11 for object detection and trajectory analysis for shot outcomes.

Features:
- Real-time basketball and hoop detection
- Shot trajectory tracking
- Made/missed shot classification with confidence scoring
- JSON logging of all shots and classifications
- Overlay display with shot counters
"""

import cv2
import numpy as np
import json
import time
from datetime import datetime
from pathlib import Path
from collections import deque
import math
from scipy.ndimage import gaussian_filter1d
from filterpy.kalman import KalmanFilter

# Fix for PyTorch 2.6+ weights_only security change
import torch
try:
    from ultralytics.nn.tasks import DetectionModel
    torch.serialization.add_safe_globals([DetectionModel])
except (AttributeError, ImportError):
    pass

from ultralytics import YOLO

class ShotTracker:
    """Tracks individual shot trajectories and determines outcomes"""
    
    def __init__(self, shot_id, initial_position):
        self.shot_id = shot_id
        self.trajectory = deque(maxlen=30)  # Store last 30 positions
        self.trajectory.append(initial_position)
        self.start_time = time.time()
        self.status = "active"  # active, completed, lost
        self.outcome = None     # made, missed, undetermined
        self.confidence = 0.0
        self.peak_reached = False
        self.frames_since_peak = 0
        self.hoop_proximity_threshold = 80
        self.min_trajectory_length = 10
        
    def update_position(self, position):
        """Update ball position and analyze trajectory"""
        self.trajectory.append(position)
        
        # Check if trajectory peak has been reached
        if len(self.trajectory) >= 5:
            self._check_trajectory_peak()
            
        # Check for shot completion
        if self.peak_reached:
            self.frames_since_peak += 1
            if self.frames_since_peak > 15:  # Wait frames after peak
                self._determine_shot_outcome()
                
    def _check_trajectory_peak(self):
        """Check if ball has reached trajectory peak"""
        if len(self.trajectory) < 5:
            return
            
        recent_y = [pos[1] for pos in list(self.trajectory)[-5:]]
        
        # Peak detected if ball starts moving down after going up
        if not self.peak_reached:
            if len(recent_y) >= 3:
                # Check if there's an upward then downward trend
                mid_point = len(recent_y) // 2
                early_y = sum(recent_y[:mid_point]) / mid_point
                later_y = sum(recent_y[mid_point:]) / (len(recent_y) - mid_point)
                
                if early_y > later_y and abs(early_y - later_y) > 5:
                    self.peak_reached = True
                    
    def _determine_shot_outcome(self):
        """Determine if shot was made or missed based on trajectory"""
        if len(self.trajectory) < self.min_trajectory_length:
            self.outcome = "undetermined"
            self.confidence = 0.0
            self.status = "completed"
            return
            
        # Get final position and trajectory direction
        final_pos = self.trajectory[-1]
        trajectory_list = list(self.trajectory)
        
        # Calculate trajectory slope in final phase
        if len(trajectory_list) >= 5:
            final_positions = trajectory_list[-5:]
            x_coords = [pos[0] for pos in final_positions]
            y_coords = [pos[1] for pos in final_positions]
            
            # Calculate if ball is moving toward or away from basket area
            final_velocity_y = y_coords[-1] - y_coords[0]
            
            # Basic heuristic: if ball trajectory ends in expected hoop area
            # This would need hoop position for accurate determination
            # For now, using trajectory characteristics
            
            if final_velocity_y > 0:  # Ball moving downward at end
                self.outcome = "made"
                self.confidence = 0.7
            else:
                self.outcome = "missed"
                self.confidence = 0.6
        else:
            self.outcome = "undetermined"
            self.confidence = 0.0
            
        self.status = "completed"
        
    def determine_outcome_with_hoop(self, hoop_position):
        """Determine shot outcome using hoop position"""
        if not self.peak_reached or len(self.trajectory) < self.min_trajectory_length:
            return
            
        final_pos = self.trajectory[-1]
        distance_to_hoop = math.sqrt(
            (final_pos[0] - hoop_position[0])**2 + 
            (final_pos[1] - hoop_position[1])**2
        )
        
        # Analyze trajectory relative to hoop
        trajectory_list = list(self.trajectory)
        
        # Check if ball passed through or near hoop area
        min_distance_to_hoop = float('inf')
        for pos in trajectory_list:
            dist = math.sqrt(
                (pos[0] - hoop_position[0])**2 + 
                (pos[1] - hoop_position[1])**2
            )
            min_distance_to_hoop = min(min_distance_to_hoop, dist)
            
        # Determine outcome based on proximity to hoop
        if min_distance_to_hoop < self.hoop_proximity_threshold:
            # Ball passed near/through hoop
            if distance_to_hoop < self.hoop_proximity_threshold * 1.5:
                self.outcome = "made"
                self.confidence = 0.85
            else:
                self.outcome = "made"
                self.confidence = 0.75
        else:
            self.outcome = "missed"
            self.confidence = 0.8
            
        self.status = "completed"

class ShotAnalyzer:
    """Main class for basketball shot detection and analysis"""
    
    def __init__(self, model_path='runs/detect/basketball_yolo11n3/weights/best.pt', confidence_threshold=0.78, min_overlap_threshold=1.0):
        """Initialize shot analyzer with YOLO model and configurable thresholds"""
        self.model = YOLO(model_path)
        self.model_path = model_path
        
        # Enable GPU acceleration for MacBook M-series chips
        import torch
        if torch.backends.mps.is_available():
            self.device = 'mps'
            print(f"🚀 Using MacBook GPU (MPS) acceleration")
        elif torch.cuda.is_available():
            self.device = 'cuda'
            print(f"🚀 Using CUDA GPU acceleration")
        else:
            self.device = 'cpu'
            print("ℹ️ Using CPU")
        
        # Move model to device
        self.model.to(self.device)
        
        # Detection thresholds
        self.basketball_confidence = 0.35
        self.hoop_confidence = 0.5
        
        # Improved shot detection with box overlap
        self.hoop_area = None
        self.hoop_center = None
        self.hoop_size = None
        self.hoop_bbox = None
        
        # Shot sequence grouping to prevent multiple detections
        self.shot_sequence_active = False
        self.shot_sequence_start_time = None
        self.shot_sequence_overlaps = []  # Store all overlaps in current sequence
        self.shot_sequence_timeout = 3.0  # 3 seconds to group overlaps into one shot
        self.current_overlap_percentage = 0
        
        # Enhanced trajectory tracking
        self.ball_trajectory_buffer = deque(maxlen=60)  # Store 2 seconds of ball positions at 30fps
        self.pre_hoop_trajectory = []  # Trajectory before hoop interaction
        self.post_hoop_trajectory = []  # Trajectory after hoop interaction
        self.post_hoop_tracking_frames = 0
        self.post_hoop_tracking_active = False
        self.post_hoop_max_frames = 20  # Track for 20 frames after overlap ends
        
        # Configurable thresholds for robustness
        self.confidence_threshold = confidence_threshold  # Threshold for made vs missed (0.78 default)
        self.min_overlap_threshold = min_overlap_threshold  # Minimum overlap to consider as shot (1.0% default)
        
        # Additional robustness features
        self.recent_shots = []  # Track recent shots to prevent duplicates
        self.duplicate_prevention_window = 2.0  # seconds
        
        # Statistics
        self.stats = {
            'made_shots': 0,
            'missed_shots': 0,
            'total_shots': 0,
            'undetermined_shots': 0
        }
        
        # Logging
        self.shot_log = []
        self.session_start = datetime.now()
        
        # Simple video timing (frame-based)
        self.video_fps = None
        self.current_frame_number = 0
        
    def set_video_timing(self, fps, start_frame=0):
        """Set video timing parameters for frame-based timestamps"""
        self.video_fps = fps
        self.current_frame_number = start_frame
            
    def update_frame_number(self, frame_number):
        """Update current frame number for timestamp calculation"""
        self.current_frame_number = frame_number
        
    def get_video_timestamp_seconds(self):
        """Calculate current video timestamp in seconds"""
        if self.video_fps is not None:
            return self.current_frame_number / self.video_fps
        else:
            return 0.0
        
    def detect_objects(self, frame):
        """Detect basketball and hoop in frame"""
        results = self.model(frame, conf=0.3, verbose=False, device=self.device)
        
        detections = {
            'basketball': [],
            'basketball_hoop': []
        }
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    
                    # Determine object type based on model
                    if 'best.pt' in str(self.model_path) or 'custom' in str(self.model_path):
                        # Custom model classes: 0=Basketball, 1=Basketball Hoop
                        if class_id == 0 and confidence >= self.basketball_confidence:
                            detections['basketball'].append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'center': [center_x, center_y],
                                'confidence': confidence
                            })
                        elif class_id == 1 and confidence >= self.hoop_confidence:
                            detections['basketball_hoop'].append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'center': [center_x, center_y],
                                'confidence': confidence
                            })
                    else:
                        # Pre-trained model (look for sports balls)
                        class_name = self.model.names[class_id].lower()
                        if 'ball' in class_name and confidence >= self.basketball_confidence:
                            detections['basketball'].append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'center': [center_x, center_y],
                                'confidence': confidence,
                                'class_name': class_name
                            })
                            
        return detections
        
    def update_shot_tracking(self, detections):
        """Enhanced shot detection: 1 frame with 100% overlap = made, otherwise missed"""
        basketball_positions = [ball['center'] for ball in detections['basketball']]
        hoop_positions = [hoop['center'] for hoop in detections['basketball_hoop']]
        
        # Update hoop area if hoop detected
        if hoop_positions:
            hoop = detections['basketball_hoop'][0]  # Use first detected hoop
            self.hoop_center = hoop['center']
            self.hoop_bbox = hoop['bbox']  # Store actual hoop bbox for overlap detection
            self.hoop_size = max(self.hoop_bbox[2] - self.hoop_bbox[0], 
                               self.hoop_bbox[3] - self.hoop_bbox[1])
            
            # Define hoop shooting area (expanded around hoop)
            margin = int(self.hoop_size * 0.8)  # 80% of hoop size as margin
            x1 = self.hoop_bbox[0] - margin
            y1 = self.hoop_bbox[1] - margin  
            x2 = self.hoop_bbox[2] + margin
            y2 = self.hoop_bbox[3] + margin
            self.hoop_area = [x1, y1, x2, y2]
            
        current_time = time.time()
        
        # Check for shot sequence timeout
        if (self.shot_sequence_active and 
            self.shot_sequence_start_time and 
            current_time - self.shot_sequence_start_time > self.shot_sequence_timeout):
            self._finalize_shot_sequence()
        
        # Check each basketball for overlap with hoop
        if basketball_positions and self.hoop_area and self.hoop_bbox:
            for ball in detections['basketball']:
                ball_center = ball['center']
                ball_bbox = ball['bbox']
                ball_size = max(ball_bbox[2] - ball_bbox[0], ball_bbox[3] - ball_bbox[1])
                
                # Check if ball is in shooting zone
                in_shooting_zone = (self.hoop_area[0] <= ball_center[0] <= self.hoop_area[2] and 
                                  self.hoop_area[1] <= ball_center[1] <= self.hoop_area[3])
                
                if in_shooting_zone:
                    # Basic size validation to filter out false detections
                    size_ratio = ball_size / self.hoop_size
                    
                    # Reasonable size range (not too small, not too large)
                    valid_size = 0.35 <= size_ratio <= 0.85
                    
                    if valid_size:
                        
                        # Check overlap percentage between ball and hoop
                        overlap_percentage = self._check_box_overlap(ball_bbox, self.hoop_bbox)
                        self.current_overlap_percentage = overlap_percentage
                        
                        # Group overlaps into shot sequences - configurable overlap threshold
                        if overlap_percentage >= self.min_overlap_threshold:
                            if not self.shot_sequence_active:
                                # Start new shot sequence
                                self.shot_sequence_active = True
                                self.shot_sequence_start_time = current_time
                                self.shot_sequence_overlaps = []
                                
                            # Add overlap to current sequence with Y position for rim bounce detection
                            overlap_data = {
                                'overlap_percentage': overlap_percentage,
                                'confidence': ball['confidence'],
                                'ball_position': ball_center,
                                'ball_y': ball_center[1],  # Store Y for upward bounce detection
                                'size_ratio': size_ratio
                            }
                            self.shot_sequence_overlaps.append(overlap_data)
                            
        # If no overlaps detected and sequence is active, check for timeout soon
        else:
            if (self.shot_sequence_active and 
                self.shot_sequence_start_time and 
                current_time - self.shot_sequence_start_time > 1.0):  # 1 second mini-timeout
                self._finalize_shot_sequence()
            
    def _check_box_overlap(self, ball_bbox, hoop_bbox):
        """Calculate overlap percentage between ball and hoop bounding boxes"""
        # ball_bbox and hoop_bbox are [x1, y1, x2, y2]
        ball_x1, ball_y1, ball_x2, ball_y2 = ball_bbox
        hoop_x1, hoop_y1, hoop_x2, hoop_y2 = hoop_bbox
        
        # Calculate intersection area
        overlap_x = max(0, min(ball_x2, hoop_x2) - max(ball_x1, hoop_x1))
        overlap_y = max(0, min(ball_y2, hoop_y2) - max(ball_y1, hoop_y1))
        intersection_area = overlap_x * overlap_y
        
        # Calculate ball area
        ball_area = (ball_x2 - ball_x1) * (ball_y2 - ball_y1)
        
        # Return overlap percentage
        if ball_area > 0:
            overlap_percentage = (intersection_area / ball_area) * 100
            return overlap_percentage
        return 0
    
    def _calculate_shot_confidence(self, shot_overlaps, max_overlap):
        """Calculate confidence score based on overlap quality and frame count"""
        if not shot_overlaps:
            return 0.0
            
        # More conservative base confidence - require higher overlap for high base confidence
        if max_overlap >= 100.0:
            base_confidence = 0.7  # Start lower even for perfect overlap
        elif max_overlap >= 95.0:
            base_confidence = 0.5
        elif max_overlap >= 90.0:
            base_confidence = 0.3
        else:
            base_confidence = max_overlap / 100.0 * 0.3  # Very low for <90% overlap
        
        # Count frames with different overlap thresholds
        frames_100_percent = sum(1 for overlap in shot_overlaps if overlap['overlap_percentage'] >= 100.0)
        frames_95_percent = sum(1 for overlap in shot_overlaps if overlap['overlap_percentage'] >= 95.0)
        frames_80_percent = sum(1 for overlap in shot_overlaps if overlap['overlap_percentage'] >= 80.0)
        total_frames = len(shot_overlaps)
        
        # Much more demanding confidence bonuses - require exceptional quality for made shots
        frame_bonus = 0.0
        if frames_100_percent >= 5:  # Require 5+ perfect frames for highest bonus
            frame_bonus += 0.15 + (frames_100_percent - 5) * 0.02  # Smaller bonuses
        elif frames_100_percent >= 3:  # 3-4 perfect frames = good
            frame_bonus += 0.10
        elif frames_100_percent >= 2:  # Two perfect frames = moderate
            frame_bonus += 0.06
        elif frames_100_percent == 1:  # Single 100% frame = small bonus
            frame_bonus += 0.03
            
        if frames_95_percent >= 6:  # Require many high-overlap frames
            frame_bonus += 0.08
        elif frames_95_percent >= 4:  # Some bonus for 4-5 high frames
            frame_bonus += 0.04
        elif frames_95_percent >= 2:  # Minimal bonus for 2-3 high frames
            frame_bonus += 0.02
            
        # Sequence quality bonus - much more demanding
        if total_frames >= 8 and frames_80_percent / total_frames >= 0.8:  # Very demanding
            frame_bonus += 0.04
        elif total_frames >= 6 and frames_80_percent / total_frames >= 0.75:
            frame_bonus += 0.02
            
        # Size ratio consistency bonus - very demanding
        size_ratios = [overlap['size_ratio'] for overlap in shot_overlaps]
        avg_size_ratio = sum(size_ratios) / len(size_ratios)
        if 0.5 <= avg_size_ratio <= 0.6:  # Very tight ideal range
            frame_bonus += 0.05
        elif 0.45 <= avg_size_ratio <= 0.65:  # Good range
            frame_bonus += 0.02
            
        # Final confidence calculation (cap at 1.0)
        final_confidence = min(1.0, base_confidence + frame_bonus)
        return final_confidence

    def _is_duplicate_shot(self, current_time, ball_position):
        """Check if this shot is a duplicate of a recent shot"""
        for recent_shot in self.recent_shots:
            time_diff = current_time - recent_shot['time']
            if time_diff <= self.duplicate_prevention_window:
                # Check if ball position is similar to recent shot
                pos_diff = abs(ball_position[0] - recent_shot['position'][0]) + abs(ball_position[1] - recent_shot['position'][1])
                if pos_diff < 50:  # Within 50 pixels
                    return True
        return False
    
    def _calculate_entry_angle(self, trajectory_points, hoop_center):
        """Calculate ball entry angle relative to hoop (vertical = 90°, horizontal = 0°)"""
        if len(trajectory_points) < 3:
            return None
            
        # Get last few points before hoop
        recent_points = trajectory_points[-5:] if len(trajectory_points) >= 5 else trajectory_points
        
        if len(recent_points) < 2:
            return None
            
        # Calculate velocity vector (direction of ball movement)
        first_point = recent_points[0]['ball_position']
        last_point = recent_points[-1]['ball_position']
        
        dx = last_point[0] - first_point[0]
        dy = last_point[1] - first_point[1]  # Positive = downward
        
        # Calculate angle from horizontal (0° = horizontal, 90° = straight down)
        if dx == 0:
            angle = 90.0 if dy > 0 else -90.0
        else:
            angle_rad = math.atan2(dy, abs(dx))
            angle = math.degrees(angle_rad)
            
        # Normalize to 0-90° range (we care about steepness, not direction)
        angle = abs(angle)
        
        return angle
    
    def _analyze_post_hoop_trajectory(self, overlap_frames):
        """Analyze ball behavior after hoop interaction"""
        if not overlap_frames or len(overlap_frames) < 2:
            return {
                'ball_continues_down': False,
                'ball_bounces_back': False,
                'ball_disappears': False,
                'confidence': 0.0
            }
        
        # Get Y positions throughout the overlap sequence
        y_positions = [frame['ball_y'] for frame in overlap_frames]
        
        # Analyze trend
        first_y = y_positions[0]
        last_y = y_positions[-1]
        
        # Check for consistent downward movement (made shot)
        downward_movement = last_y - first_y
        
        # Check for upward bounce (missed shot - rim bounce)
        upward_movement = first_y - last_y
        
        # Calculate velocity consistency
        if len(y_positions) >= 3:
            # Check if movement is consistently in one direction
            deltas = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]
            positive_deltas = sum(1 for d in deltas if d > 2)  # Downward
            negative_deltas = sum(1 for d in deltas if d < -2)  # Upward
            
            total_deltas = len(deltas)
            downward_consistency = positive_deltas / total_deltas if total_deltas > 0 else 0
            upward_consistency = negative_deltas / total_deltas if total_deltas > 0 else 0
        else:
            downward_consistency = 0.5
            upward_consistency = 0.5
        
        return {
            'ball_continues_down': downward_movement > 15 and downward_consistency > 0.6,
            'ball_bounces_back': upward_movement > 15 and upward_consistency > 0.5,
            'downward_movement': downward_movement,
            'upward_movement': upward_movement,
            'downward_consistency': downward_consistency,
            'upward_consistency': upward_consistency
        }
    
    def _enhanced_rim_bounce_detection(self, overlap_frames, entry_angle, post_hoop_analysis):
        """Multi-factor rim bounce detection"""
        if not overlap_frames:
            return False, 0.0
        
        bounce_score = 0.0
        max_score = 5.0
        
        # Factor 1: Upward movement during overlap (strongest indicator)
        if post_hoop_analysis.get('ball_bounces_back', False):
            bounce_score += 2.0
        
        # Factor 2: Low entry angle (ball approaching from side)
        if entry_angle is not None and entry_angle < 35:  # Less than 35° from horizontal
            bounce_score += 1.5
        
        # Factor 3: Low overlap percentage (grazing the rim)
        max_overlap = max(f['overlap_percentage'] for f in overlap_frames)
        if max_overlap < 80:
            bounce_score += 1.0
        elif max_overlap < 95:
            bounce_score += 0.5
        
        # Factor 4: Erratic movement pattern
        if len(overlap_frames) >= 3:
            overlaps = [f['overlap_percentage'] for f in overlap_frames]
            # Check for sudden drops in overlap (ball bouncing off)
            drops = sum(1 for i in range(len(overlaps)-1) if overlaps[i] - overlaps[i+1] > 30)
            if drops >= 2:
                bounce_score += 0.5
        
        # Determine if it's a rim bounce
        is_bounce = bounce_score >= 2.5
        confidence = bounce_score / max_score
        
        return is_bounce, confidence

    def _finalize_shot_sequence(self):
        """Enhanced shot sequence finalization with multi-factor analysis"""
        if not self.shot_sequence_overlaps:
            return
            
        # Check for duplicate shots
        current_time = time.time()
        max_overlap_position = max(self.shot_sequence_overlaps, key=lambda x: x['overlap_percentage'])['ball_position']
        
        if self._is_duplicate_shot(current_time, max_overlap_position):
            # Reset sequence without logging
            self.shot_sequence_active = False
            self.shot_sequence_start_time = None
            self.shot_sequence_overlaps = []
            return
            
        # === ENHANCED ANALYSIS ===
        
        # Calculate overlap statistics
        max_overlap = max(overlap['overlap_percentage'] for overlap in self.shot_sequence_overlaps)
        avg_overlap = sum(overlap['overlap_percentage'] for overlap in self.shot_sequence_overlaps) / len(self.shot_sequence_overlaps)
        
        max_overlap_data = next(overlap for overlap in self.shot_sequence_overlaps 
                               if overlap['overlap_percentage'] == max_overlap)
        
        # Count frames with different overlap thresholds
        frames_with_100_percent = sum(1 for overlap in self.shot_sequence_overlaps 
                                    if overlap['overlap_percentage'] >= 100.0)
        frames_with_95_percent = sum(1 for overlap in self.shot_sequence_overlaps 
                                   if overlap['overlap_percentage'] >= 95.0)
        frames_with_90_percent = sum(1 for overlap in self.shot_sequence_overlaps 
                                   if overlap['overlap_percentage'] >= 90.0)
        
        total_overlap_frames = len(self.shot_sequence_overlaps)
        
        # Calculate entry angle
        entry_angle = self._calculate_entry_angle(self.shot_sequence_overlaps, self.hoop_center)
        
        # Analyze post-hoop trajectory
        post_hoop_analysis = self._analyze_post_hoop_trajectory(self.shot_sequence_overlaps)
        
        # Enhanced rim bounce detection
        is_rim_bounce, bounce_confidence = self._enhanced_rim_bounce_detection(
            self.shot_sequence_overlaps, 
            entry_angle, 
            post_hoop_analysis
        )
        
        # Calculate weighted overlap score (addresses fast shot blind spot)
        weighted_overlap_score = (
            frames_with_100_percent * 1.0 +
            (frames_with_95_percent - frames_with_100_percent) * 0.8 +
            (frames_with_90_percent - frames_with_95_percent) * 0.5
        )
        
        # === ENHANCED DECISION LOGIC V3 ===
        # Physics-based improvements from misclassification analysis
        
        outcome = "missed"  # Default
        outcome_reason = "insufficient_evidence"
        decision_confidence = 0.0
        
        # FIX 1: Enhanced Rim Bounce for Steep Entries
        # Physics: Made shots with steep entry (>70°) should NOT bounce upward
        steep_entry_bounce_back = (
            entry_angle is not None and entry_angle >= 70 and 
            post_hoop_analysis['ball_bounces_back']
        )
        
        # Decision Factor 1: Very High Overlap (Certain Made Shots)
        # Requires minimum 4+ frames at 100% OR 7+ frames at 95%+ to be confident
        if frames_with_100_percent >= 6 or (frames_with_100_percent >= 4 and frames_with_95_percent >= 7):
            # Check for rim bounce override (including steep entry bounce-back)
            if steep_entry_bounce_back:
                # FIX 1: Steep entries that bounce back are rim bounces
                outcome = "missed"
                outcome_reason = "steep_entry_bounce_back"
                decision_confidence = 0.85
            elif is_rim_bounce and bounce_confidence > 0.7 and not post_hoop_analysis['ball_continues_down']:
                outcome = "missed"
                outcome_reason = "rim_bounce_high_confidence"
                decision_confidence = bounce_confidence
            else:
                outcome = "made"
                outcome_reason = "perfect_overlap_layup"
                decision_confidence = 0.95
        
        # Decision Factor 2: Strong Rim Bounce Indicators (Certain Missed Shots)
        elif steep_entry_bounce_back:
            # FIX 1: Steep entry bounce-back is a clear miss
            outcome = "missed"
            outcome_reason = "steep_entry_bounce_back"
            decision_confidence = 0.85
        elif is_rim_bounce and bounce_confidence >= 0.6:
            outcome = "missed"
            outcome_reason = "rim_bounce_detected"
            decision_confidence = bounce_confidence
        
        # Decision Factor 3: Good Overlap + Positive Indicators (Made Shots)
        # Includes 3+ frames at 100%
        elif frames_with_100_percent >= 3 and not is_rim_bounce:
            # FIX 2: Enhanced downward continuation weight
            downward_consistency = post_hoop_analysis.get('downward_consistency', 0)
            
            # Additional checks for confidence
            if entry_angle is not None and entry_angle >= 40:  # Steep entry
                outcome = "made"
                outcome_reason = "perfect_overlap_steep_entry"
                decision_confidence = 0.85
            elif post_hoop_analysis['ball_continues_down'] and downward_consistency >= 0.8:
                # FIX 2: Strong downward continuation = higher confidence
                outcome = "made"
                outcome_reason = "perfect_overlap_continues_down_strong"
                decision_confidence = 0.88
            elif post_hoop_analysis['ball_continues_down']:
                outcome = "made"
                outcome_reason = "perfect_overlap_continues_down"
                decision_confidence = 0.82
            else:
                outcome = "made"
                outcome_reason = "perfect_overlap"
                decision_confidence = 0.75
        
        # Decision Factor 3b: Fast Clean Swish (NEW - FIX 3)
        # 2 frames at 100% with strong downward continuation
        elif frames_with_100_percent >= 2 and not is_rim_bounce:
            downward_consistency = post_hoop_analysis.get('downward_consistency', 0)
            
            # FIX 3: Allow 2 frames if downward continuation is very strong
            if post_hoop_analysis['ball_continues_down'] and downward_consistency >= 0.8:
                outcome = "made"
                outcome_reason = "fast_clean_swish"
                decision_confidence = 0.75
            else:
                # Not enough evidence with only 2 frames and weak downward
                outcome = "missed"
                outcome_reason = "insufficient_overlap"
                decision_confidence = 0.65
        
        # Decision Factor 4: Fast Clean Swish (Weighted Score System)
        # Addresses blind spot for very fast shots
        elif weighted_overlap_score >= 3.5 and not is_rim_bounce:
            downward_consistency = post_hoop_analysis.get('downward_consistency', 0)
            
            # FIX 2: Enhanced downward weight for fast shots
            if post_hoop_analysis['ball_continues_down'] and downward_consistency >= 0.8:
                # Very strong downward = likely made
                outcome = "made"
                outcome_reason = "fast_swoosh_clean_strong"
                decision_confidence = 0.75
            elif (entry_angle is not None and entry_angle >= 35) or post_hoop_analysis['ball_continues_down']:
                outcome = "made"
                outcome_reason = "fast_swoosh_clean"
                decision_confidence = 0.70
            else:
                # Ambiguous fast shot - need more evidence
                outcome = "missed"
                outcome_reason = "fast_swoosh_ambiguous"
                decision_confidence = 0.55
        
        # Decision Factor 5: Moderate Overlap (Ambiguous Cases)
        elif frames_with_95_percent >= 4 and avg_overlap >= 85:
            downward_consistency = post_hoop_analysis.get('downward_consistency', 0)
            
            # FIX 2: Use downward consistency for tiebreaker
            if post_hoop_analysis['ball_continues_down'] and downward_consistency >= 0.8:
                outcome = "made"
                outcome_reason = "moderate_overlap_strong_downward"
                decision_confidence = 0.70
            elif entry_angle is not None and entry_angle >= 45 and post_hoop_analysis['ball_continues_down']:
                outcome = "made"
                outcome_reason = "moderate_overlap_good_indicators"
                decision_confidence = 0.65
            else:
                outcome = "missed"
                outcome_reason = "moderate_overlap_insufficient"
                decision_confidence = 0.60
        
        # Decision Factor 6: Low Overlap (Missed Shots)
        else:
            outcome = "missed"
            outcome_reason = "insufficient_overlap"
            decision_confidence = 0.80
        
        # Update statistics
        if outcome == "made":
            self.stats['made_shots'] += 1
        else:
            self.stats['missed_shots'] += 1
            
        self.stats['total_shots'] += 1
        
        # Log the shot with enhanced analysis data
        shot_data = {
            'timestamp_seconds': self.get_video_timestamp_seconds(),
            'outcome': outcome,
            'outcome_reason': outcome_reason,
            'decision_confidence': decision_confidence,
            'detection_confidence': max_overlap_data['confidence'],
            'max_overlap_percentage': max_overlap,
            'avg_overlap_percentage': avg_overlap,
            'frames_with_100_percent': frames_with_100_percent,
            'frames_with_95_percent': frames_with_95_percent,
            'frames_with_90_percent': frames_with_90_percent,
            'weighted_overlap_score': weighted_overlap_score,
            'total_overlaps_in_sequence': len(self.shot_sequence_overlaps),
            'ball_position': max_overlap_data['ball_position'],
            'hoop_center': self.hoop_center,
            'is_rim_bounce': is_rim_bounce,
            'rim_bounce_confidence': bounce_confidence,
            'entry_angle': entry_angle,
            'post_hoop_analysis': post_hoop_analysis,
            'detection_method': 'enhanced_multi_factor_v3'
        }
        self.shot_log.append(shot_data)
        
        # Add to recent shots for duplicate prevention
        self.recent_shots.append({
            'time': current_time,
            'position': max_overlap_data['ball_position'],
            'outcome': outcome
        })
        
        # Clean up old recent shots (keep only within duplicate prevention window)
        self.recent_shots = [shot for shot in self.recent_shots 
                           if current_time - shot['time'] <= self.duplicate_prevention_window]
        
        # Reset sequence tracking
        self.shot_sequence_active = False
        self.shot_sequence_start_time = None
        self.shot_sequence_overlaps = []
        
    def draw_overlay(self, frame, detections):
        """Draw clean detection overlay and shot statistics"""
        height, width = frame.shape[:2]
        overlay = frame.copy()
        
        # Draw hoop detection and area
        for hoop in detections['basketball_hoop']:
            x1, y1, x2, y2 = hoop['bbox']
            confidence = hoop['confidence']
            
            # Draw clean hoop box
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw hoop area if defined
            if self.hoop_area:
                area_color = (0, 255, 0)
                cv2.rectangle(overlay, (self.hoop_area[0], self.hoop_area[1]), 
                            (self.hoop_area[2], self.hoop_area[3]), area_color, 1)
                
                # Label the shooting zone
                cv2.putText(overlay, "SHOOTING ZONE", 
                          (self.hoop_area[0], self.hoop_area[1] - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, area_color, 1)
            
        # Draw basketball detection with fixed color box and confidence
        for ball in detections['basketball']:
            x1, y1, x2, y2 = ball['bbox']
            center = ball['center']
            confidence = ball['confidence']
            
            # Fixed color bounding box for ball (orange)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 165, 255), 2)
            
            # Confidence label on box
            label = f"Ball: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(overlay, (x1, y1 - label_size[1] - 8), 
                         (x1 + label_size[0] + 4, y1), (0, 165, 255), -1)
            cv2.putText(overlay, label, (x1 + 2, y1 - 4), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Check if ball is in shooting zone
            if (self.hoop_area and 
                self.hoop_area[0] <= center[0] <= self.hoop_area[2] and 
                self.hoop_area[1] <= center[1] <= self.hoop_area[3]):
                # Highlight ball in shooting zone with thicker border
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 0), 3)
                
                # Check for box overlap with hoop
                if self.hoop_bbox:
                    overlap_pct = self._check_box_overlap(ball['bbox'], self.hoop_bbox)
                    if overlap_pct > 0:
                        # Simple color coding: 95% = green (made), anything else = red (missed)
                        if overlap_pct >= 95.0:
                            color = (0, 255, 0)  # Green for 95%+ overlap (made)
                            label = f"MADE: {overlap_pct:.0f}%"
                        else:
                            color = (0, 0, 255)  # Red for partial overlap (missed)
                            label = f"MISS: {overlap_pct:.0f}%"
                            
                        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 4)
                        cv2.putText(overlay, label, (x1, y2 + 15), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
        # Draw clean statistics overlay
        self._draw_clean_stats_overlay(overlay)
        
        return overlay
        
    def _draw_clean_stats_overlay(self, frame):
        """Draw clean, minimal shot statistics overlay"""
        height, width = frame.shape[:2]
        
        # Calculate shooting percentage
        total_determined = self.stats['made_shots'] + self.stats['missed_shots']
        shooting_pct = (self.stats['made_shots'] / total_determined * 100) if total_determined > 0 else 0
        
        # Position overlay in top-right corner
        x_offset = width - 200
        y_offset = 20
        
        # Semi-transparent background
        overlay_bg = np.zeros((80, 180, 3), dtype=np.uint8)
        alpha = 0.3
        
        # Create overlay region
        overlay_region = frame[y_offset:y_offset+80, x_offset:x_offset+180]
        frame[y_offset:y_offset+80, x_offset:x_offset+180] = cv2.addWeighted(
            overlay_region, 1-alpha, overlay_bg, alpha, 0)
        
        # Clean, minimal text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        
        # Shot statistics
        cv2.putText(frame, f"MADE: {self.stats['made_shots']}", 
                   (x_offset + 10, y_offset + 20), font, font_scale, (0, 255, 0), thickness)
        cv2.putText(frame, f"MISSED: {self.stats['missed_shots']}", 
                   (x_offset + 10, y_offset + 40), font, font_scale, (0, 100, 255), thickness)
        cv2.putText(frame, f"TOTAL: {self.stats['total_shots']}", 
                   (x_offset + 10, y_offset + 60), font, font_scale, (255, 255, 255), thickness)
        
        # Show shot sequence tracking info
        if self.shot_sequence_active:
            overlaps_count = len(self.shot_sequence_overlaps)
            max_overlap = max([o['overlap_percentage'] for o in self.shot_sequence_overlaps]) if self.shot_sequence_overlaps else 0
            frames_95 = sum(1 for o in self.shot_sequence_overlaps if o['overlap_percentage'] >= 95.0)
            
            cv2.putText(frame, f"SEQUENCE: {overlaps_count} overlaps", 
                       (x_offset + 10, y_offset + 80), font, font_scale, (255, 255, 0), thickness)
            
            if max_overlap >= 95.0 and frames_95 >= 2:
                cv2.putText(frame, f"95%+: {frames_95} frames - MADE", 
                           (x_offset + 10, y_offset + 100), font, font_scale, (0, 255, 0), thickness)
            elif max_overlap >= 95.0:
                cv2.putText(frame, f"95%+: {frames_95} frames - NEED 2+", 
                           (x_offset + 10, y_offset + 100), font, font_scale, (255, 165, 0), thickness)
            else:
                cv2.putText(frame, f"MAX: {max_overlap:.0f}% - MISS", 
                           (x_offset + 10, y_offset + 100), font, font_scale, (0, 0, 255), thickness)
        elif self.current_overlap_percentage > 0:
            if self.current_overlap_percentage >= 95.0:
                cv2.putText(frame, f"OVERLAP: {self.current_overlap_percentage:.0f}% - MADE", 
                           (x_offset + 10, y_offset + 80), font, font_scale, (0, 255, 0), thickness)
            else:
                cv2.putText(frame, f"OVERLAP: {self.current_overlap_percentage:.0f}% - MISS", 
                           (x_offset + 10, y_offset + 80), font, font_scale, (0, 0, 255), thickness)
                   
    def _draw_stats_overlay(self, frame):
        """Compatibility method - delegates to clean overlay"""
        self._draw_clean_stats_overlay(frame)
                       
    def save_session_data(self, filename=None):
        """Save session data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shot_session_{timestamp}.json"
            
        session_data = {
            'session_info': {
                'start_time': self.session_start.isoformat(),
                'end_time': datetime.now().isoformat(),
                'model_path': str(self.model_path),
                'total_duration': time.time() - self.session_start.timestamp()
            },
            'statistics': self.stats,
            'shots': self.shot_log
        }
        
        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2)
            
        print(f"✓ Session data saved to: {filename}")
        return filename