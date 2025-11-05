# 🏗️ Processing Architecture

Complete overview of how the basketball shot detection system processes videos and classifies shots.

---

## 📋 System Overview

The system processes basketball game videos frame-by-frame, detecting the ball and hoop, tracking ball trajectory, and classifying shots as made or missed using a multi-factor decision logic.

**Core Components:**
1. **Object Detection** - YOLOv11 model for ball/hoop detection
2. **Trajectory Tracking** - Kalman filtering and trajectory analysis
3. **Overlap Analysis** - Ball-hoop bounding box overlap calculation
4. **Decision Logic** - Multi-factor classification with confidence scoring
5. **Accuracy Validation** - Ground truth comparison and reporting

---

## 🔄 Processing Pipeline

### Stage 1: Video Input & Setup
```
Input Video → OpenCV VideoCapture → Extract Properties
  - FPS, Resolution, Frame Count
  - Initialize ShotAnalyzer with YOLO model
  - Set up output video writer
```

### Stage 2: Frame-by-Frame Processing Loop

For each frame:

#### 2.1 Object Detection (`detect_objects`)
- **YOLOv11 Inference**: Detects basketball and hoop in frame
- **Confidence Filtering**: 
  - Basketball: ≥0.35 confidence
  - Hoop: ≥0.5 confidence
- **Hoop Initialization**: First hoop detection establishes reference point

#### 2.2 Shot Tracking (`update_shot_tracking`)
- **Ball-Hoop Overlap Calculation**: 
  - Computes IoU (Intersection over Union) between ball and hoop bounding boxes
  - Tracks overlap percentage per frame
- **Shot Sequence Grouping**:
  - Groups overlapping frames within 3-second window
  - Prevents multiple detections of same shot
  - Tracks all overlaps in sequence

#### 2.3 Trajectory Analysis
- **Ball Position Tracking**:
  - Stores last 60 frames of ball positions (2 seconds @ 30fps)
  - Uses Kalman filter for smooth tracking
- **Pre-Hoop Trajectory**: Ball movement before overlap
- **Post-Hoop Trajectory**: Ball movement after overlap (20 frames)

#### 2.4 Shot Classification
When shot sequence ends (3-second timeout):

**Multi-Factor Decision Logic (`_finalize_shot_sequence`):**

1. **Overlap Metrics**:
   - Frames at 100% overlap
   - Frames at 95%+ overlap  
   - Frames at 90%+ overlap
   - Average overlap percentage
   - Weighted overlap score

2. **Trajectory Analysis**:
   - Entry angle calculation (ball entry angle relative to hoop)
   - Downward movement (pixels ball moves down after hoop)
   - Downward consistency (0-1 score of trajectory smoothness)
   - Upward movement (pixels ball moves up - rim bounce indicator)
   - Upward consistency
   - Deceleration detection
   - Reversal detection

3. **Post-Hoop Analysis** (`_analyze_post_hoop_trajectory`):
   - Ball continues down: `true/false`
   - Ball bounces back: `true/false`
   - Rim bounce confidence: 0-1 score

4. **Rim Bounce Detection** (`_enhanced_rim_bounce_detection`):
   - Detects upward movement (>20px)
   - Checks upward consistency (>0.6)
   - Identifies deceleration and reversal patterns

5. **Overlap Pattern Analysis** (`_analyze_overlap_pattern`):
   - Sudden drop detection (rim hit signature)
   - Sustained overlap (made shot pattern)

---

## 🎯 Decision Logic Hierarchy (V4)

The system uses a priority-based decision tree:

### Decision Factor 1: Very High Overlap (Certain Made Shots)
- **Condition**: 6+ frames at 100% OR (4+ frames at 100% AND 7+ frames at 95%+)
- **Exceptions**:
  - Rim hit pattern (high max overlap, low avg, no downward movement) → MISSED
  - Steep entry bounce-back → MISSED
  - Rim rattler detection (8+ frames, rim bounce 0.7-0.95) → MADE
  - High rim bounce confidence (>0.7) → MISSED
- **Default**: MADE (confidence: 0.95)

### Decision Factor 2: Strong Rim Bounce Indicators (Certain Missed Shots)
- **Condition**: Steep entry (≥70°) with bounce-back OR rim bounce confidence ≥0.6
- **Result**: MISSED

### Decision Factor 3: Good Overlap + Positive Indicators
- **Condition**: 3+ frames at 100% overlap
- **Sub-decisions**:
  - Steep entry (≥40°): Check rim bounce first, then downward continuation
  - Strong downward continuation (consistency ≥0.8, movement >30px) → MADE
  - Moderate downward continuation → MADE (lower confidence)
  - No downward continuation → MADE (lowest confidence)
- **Result**: MADE (various confidence levels)

### Improvement D: 5+ Frames Threshold
- **Condition**: 5+ frames at 100%, avg overlap ≥80%, bounce confidence <0.6
- **Result**: MADE (confidence: 0.82)

### Decision Factor 3b: Fast Clean Swish (2 Frames)
- **Condition**: 2 frames at 100% overlap
- **Sub-decisions**:
  - **Free Throw** (entry ≥75°, avg overlap ≥70%): Lenient requirements → MADE
  - **Excellent Downward** (overlap ≥85%, consistency ≥0.8, movement ≥150px): → MADE
  - **Strict Validation**: Requires downward consistency ≥0.9, movement ≥40px, entry 30-70°, bounce confidence <0.2
- **Result**: MADE (if conditions met) or MISSED

### Decision Factor 4: Weighted Overlap Score
- **Condition**: Weighted score ≥3.5 (accounts for fast shots)
- **Checks**: Overlap pattern (sudden drop = MISSED, sustained = MADE)
- **Result**: MADE/MISSED based on pattern

### Decision Factor 5: Moderate Overlap Made Shots
- **Condition**: Avg overlap 50-70%, downward consistency >0.7, upward consistency <0.3
- **Requires**: Downward movement >0, ball continues down
- **Result**: MADE

### Improvement 1.2: Steep Entry Clean Swish
- **Condition**: Entry angle ≥70°, avg overlap 40-50%, downward consistency >0.6, bounce confidence <0.3
- **Requires**: Downward movement >0, ball continues down
- **Result**: MADE

### Default: MISSED
- **Condition**: No decision factors matched
- **Reason**: "insufficient_evidence"
- **Result**: MISSED (confidence: 0.0)

---

## 📊 Output Structure

### Per-Shot Output (`detected_shot`)
```json
{
  "timestamp_seconds": 17.01,
  "outcome": "made",
  "outcome_reason": "perfect_overlap_layup",
  "decision_confidence": 0.95,
  "detection_confidence": 0.87,
  "max_overlap_percentage": 100.0,
  "avg_overlap_percentage": 81.22,
  "frames_with_100_percent": 3,
  "frames_with_95_percent": 3,
  "frames_with_90_percent": 4,
  "weighted_overlap_score": 3.5,
  "entry_angle": 38.68,
  "rim_bounce_confidence": 0.2,
  "post_hoop_analysis": {
    "ball_continues_down": true,
    "ball_bounces_back": false,
    "downward_movement": 233,
    "downward_consistency": 1.0,
    "upward_consistency": 0.0
  }
}
```

### Session JSON
- All detected shots with full metadata
- Video metadata (FPS, resolution, frame count)
- Processing timestamp
- Model version info

### Validation Results
- Accuracy analysis (matched correct/incorrect)
- Ground truth comparison
- Mismatch details
- Overall statistics

---

## 🔧 Key Algorithms

### 1. Overlap Calculation (IoU)
```python
def calculate_overlap(ball_bbox, hoop_bbox):
    # Calculate intersection area
    intersection_area = intersection(ball_bbox, hoop_bbox)
    # Calculate union area
    union_area = area(ball_bbox) + area(hoop_bbox) - intersection_area
    # Return percentage
    return (intersection_area / union_area) * 100
```

### 2. Entry Angle Calculation
```python
def calculate_entry_angle(ball_positions, hoop_center):
    # Use ball position at first overlap
    entry_point = ball_positions[overlap_start_index]
    # Calculate angle from entry point to hoop center
    angle = atan2(hoop_center.y - entry_point.y, 
                  abs(hoop_center.x - entry_point.x))
    return degrees(angle)  # 0° = horizontal, 90° = vertical
```

### 3. Trajectory Consistency
```python
def calculate_consistency(positions, direction='downward'):
    # Calculate movement vectors
    vectors = [pos2 - pos1 for pos1, pos2 in zip(positions[:-1], positions[1:])]
    # Check direction consistency
    if direction == 'downward':
        consistent_moves = sum(1 for v in vectors if v.y > 0)
    else:  # upward
        consistent_moves = sum(1 for v in vectors if v.y < 0)
    return consistent_moves / len(vectors)  # 0-1 score
```

### 4. Kalman Filtering
- Tracks ball position with prediction
- Reduces jitter from detection noise
- Smooths trajectory for analysis

---

## ⚙️ Configuration Parameters

### Detection Thresholds
- `basketball_confidence`: 0.35 (minimum detection confidence)
- `hoop_confidence`: 0.5 (minimum detection confidence)

### Shot Sequence Grouping
- `shot_sequence_timeout`: 3.0 seconds (groups overlaps into one shot)
- `post_hoop_max_frames`: 20 frames (post-hoop tracking duration)

### Trajectory Buffer
- `ball_trajectory_buffer`: 60 frames (2 seconds @ 30fps)

### Decision Logic Thresholds
- Very high overlap: 6+ frames at 100% OR 4+ at 100% + 7+ at 95%+
- Good overlap: 3+ frames at 100%
- Fast swish: 2+ frames at 100%
- Moderate overlap: 50-70% avg overlap
- Steep entry: ≥70° entry angle
- Free throw: ≥75° entry angle + ≥70% avg overlap
- Excellent downward: ≥150px movement, ≥0.8 consistency

---

## 🚀 Performance Optimizations

1. **GPU Acceleration**: Uses MPS (Apple Silicon) or CUDA when available
2. **Frame Skipping**: Processes every frame but uses efficient YOLO inference
3. **Sequence Grouping**: Prevents redundant shot detection
4. **Early Termination**: Shot classification happens only when sequence ends
5. **Kalman Filtering**: Reduces computational noise in trajectory analysis

---

## 📈 Accuracy Metrics

The system achieves **95.83% matched_shots_accuracy** (V4 improvements):

- **Matched Correct**: Correctly classified shots (made/missed match ground truth)
- **Matched Incorrect**: Wrong classification (made→missed or missed→made)
- **Missing from Ground Truth**: Detected but not in ground truth
- **Unmatched Ground Truth**: In ground truth but not detected

---

## 🔍 Error Types & Handling

### Made→Missed Errors
- Often due to insufficient overlap evidence
- Fast swish shots with minimal visual overlap
- Current: 3 remaining errors (all "insufficient_overlap")

### Missed→Made Errors
- Rim bounces incorrectly classified as made
- Currently: 0 errors (successfully eliminated)

---

*Architecture Version: V4*
*Last Updated: Current*
*Model: YOLOv11 (custom basketball detection)*

