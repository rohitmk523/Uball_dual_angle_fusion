# Far Angle Shot Detection - Implementation Plan

**Created**: November 5, 2025
**Project**: Basketball Shot Detection System - Far Angle Camera Implementation
**Repository**: `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_far_angle_shot_detection`

---

## 📋 Overview

This document outlines the complete implementation plan for a far angle basketball shot detection system. The far angle cameras provide a side view of the basketball hoop, requiring different detection logic compared to near angle cameras.

### Key Differences from Near Angle

| Aspect | Near Angle | Far Angle |
|--------|------------|-----------|
| **Camera View** | Front/close to hoop | Side view of court |
| **Hoop Visibility** | Full hoop opening visible | Hoop rim visible from side |
| **Ball Detection** | Ball passes through hoop opening | Ball center crosses hoop vertical zone |
| **Primary Metric** | Box overlap percentage (IoU) | Ball center position in hoop zone |
| **Made Shot Logic** | 6+ frames at 100% overlap | Ball center passes through zone vertically |
| **Missed Shot Logic** | Rim bounce, low overlap | Ball outside zone or bounces back |
| **Trajectory Analysis** | Entry angle + post-hoop movement | Vertical passage + horizontal zone alignment |

---

## 🎯 Project Goals

1. **Independent Shot Detection**: Detect and classify shots from far angle cameras
2. **Ground Truth Validation**: Compare detections against Supabase database
3. **High Accuracy**: Target 90%+ matched shot accuracy
4. **Same Structure as Near Angle**: Maintain consistent architecture for future dual-camera fusion

---

## 🏗️ System Architecture

### Detection Pipeline

```
Video Input
    ↓
YOLO Object Detection (Ball + Hoop)
    ↓
Ball Center Position Tracking
    ↓
Hoop Zone Definition (vertical column around hoop)
    ↓
Vertical Passage Detection
    ↓
Trajectory Analysis (downward vs bounce-back)
    ↓
Shot Classification (MADE/MISSED)
    ↓
Output: Annotated Video + Session JSON + Accuracy Report
```

### Core Components

1. **Object Detection**: YOLOv11 model (already trained on basketball + hoop)
2. **Zone-Based Tracking**: Track ball center position relative to hoop zone
3. **Vertical Passage Detection**: Detect when ball crosses hoop plane
4. **Trajectory Analysis**: Analyze ball movement for made/missed classification
5. **Accuracy Validation**: Compare with Supabase ground truth

---

## 📁 File Structure

```
Uball_far_angle_shot_detection/
├── main.py                          # Main entry point (similar to near angle)
├── shot_detection.py                # Far angle ShotAnalyzer class
├── accuracy_validator.py            # Ground truth validation (reuse near angle)
├── requirements.txt                 # Dependencies (already exists)
├── create_training_clips.py         # Already exists - for dataset prep
├── process_video.py                 # Already exists - for model validation
├── custom_training.py               # Already exists - for training
├── .env                             # Supabase credentials
├── .env.example                     # Template
├── FAR_ANGLE_IMPLEMENTATION_PLAN.md # This file
├── results/                         # Validation outputs (UUID-based folders)
│   └── [uuid]/
│       ├── detection_results.json   # All detected shots
│       ├── ground_truth.json        # Ground truth from Supabase
│       ├── accuracy_analysis.json   # Accuracy metrics
│       ├── session_summary.json     # Quick summary
│       └── processed_video.mp4      # Annotated video
├── Game-1/                          # Input videos
│   ├── game1_farleft.mp4
│   └── game1_farright.mp4
└── runs/detect/                     # Trained models
    └── basketball_yolo11n/weights/best.pt
```

---

## 🔧 Implementation Details

### 1. Main Entry Point (`main.py`)

**Purpose**: Process videos with far angle shot detection and optional accuracy validation

**Command-Line Interface**:
```bash
# Process full video
python main.py --action video \
    --video_path Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt

# Process with time range (testing)
python main.py --action video \
    --video_path Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --start_time 0 \
    --end_time 120

# Validate accuracy against ground truth
python main.py --action video \
    --video_path Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --validate_accuracy \
    --angle LEFT
```

**Required Arguments**:
- `--action`: Action to perform (video, batch)
- `--video_path`: Path to input video

**Optional Arguments**:
- `--model`: Path to YOLO model (default: `runs/detect/basketball_yolo11n/weights/best.pt`)
- `--output_path`: Custom output path
- `--start_time`: Start time in seconds
- `--end_time`: End time in seconds
- `--game_id`: Game UUID from Supabase (for validation)
- `--validate_accuracy`: Enable accuracy validation
- `--angle`: Camera angle (LEFT or RIGHT)

**Functions to Implement**:
1. `process_video()`: Main video processing function
2. Command-line argument parsing
3. Integration with ShotAnalyzer and AccuracyValidator

---

### 2. Shot Detection Logic (`shot_detection.py`)

**Class**: `ShotAnalyzer`

#### Initialization
```python
class ShotAnalyzer:
    def __init__(self, model_path):
        # Load YOLO model
        # Initialize tracking variables
        # Set far angle specific parameters
```

#### Key Parameters (Far Angle Specific)

```python
# Hoop zone definition
HOOP_ZONE_WIDTH = 80        # Pixels on each side of hoop center X
HOOP_ZONE_VERTICAL = 100    # Vertical zone height around hoop Y

# Shot detection thresholds
MIN_FRAMES_IN_ZONE = 3      # Minimum frames ball must be in zone
MIN_VERTICAL_MOVEMENT = 50  # Minimum downward pixels for made shot
TRAJECTORY_CONSISTENCY = 0.7 # Downward consistency threshold

# Confidence thresholds
BASKETBALL_CONFIDENCE = 0.35
HOOP_CONFIDENCE = 0.5

# Shot sequence grouping
SHOT_SEQUENCE_TIMEOUT = 3.0  # seconds
POST_SHOT_TRACKING_FRAMES = 20

# Kalman filter for trajectory smoothing
USE_KALMAN_FILTER = True
```

#### Core Methods

##### 1. `detect_objects(frame)`
- Run YOLO inference on frame
- Extract ball and hoop detections
- Filter by confidence thresholds
- Return detections with bounding boxes

##### 2. `update_shot_tracking(detections)`
- Track ball center position
- Define hoop zone (vertical column around hoop)
- Check if ball center is in zone
- Track frames in zone
- Finalize shot when sequence ends

##### 3. `is_ball_in_hoop_zone(ball_center, hoop_center)`
```python
def is_ball_in_hoop_zone(self, ball_center, hoop_center):
    """
    Check if ball center is within hoop vertical zone

    Args:
        ball_center: (x, y) tuple of ball center
        hoop_center: (x, y) tuple of hoop center

    Returns:
        bool: True if ball is in zone
    """
    x_in_zone = abs(ball_center[0] - hoop_center[0]) <= HOOP_ZONE_WIDTH
    y_in_zone = abs(ball_center[1] - hoop_center[1]) <= HOOP_ZONE_VERTICAL

    return x_in_zone and y_in_zone
```

##### 4. `detect_vertical_passage(ball_positions, hoop_y)`
```python
def detect_vertical_passage(self, ball_positions, hoop_y):
    """
    Detect if ball passed vertically through hoop

    Checks:
    1. Ball starts above hoop (y < hoop_y)
    2. Ball ends below hoop (y > hoop_y)
    3. Ball maintains horizontal alignment during passage

    Returns:
        dict: {
            'passed_through': bool,
            'downward_movement': float,
            'consistency': float
        }
    """
```

##### 5. `classify_shot(shot_sequence)`
```python
def classify_shot(self, shot_sequence):
    """
    Classify shot as MADE or MISSED based on far angle logic

    Decision Logic:

    MADE if:
      - Ball center passed through zone vertically (3+ frames)
      - Downward movement >= 50 pixels
      - Trajectory consistency >= 0.7
      - No bounce-back detected

    MISSED if:
      - Ball did not pass through zone
      - Ball bounced back (upward movement after approach)
      - Insufficient frames in zone (<3)
      - Low trajectory consistency

    Returns:
        dict: {
            'outcome': 'made'/'missed',
            'outcome_reason': str,
            'decision_confidence': float,
            'frames_in_zone': int,
            'vertical_passage': bool,
            'downward_movement': float,
            'trajectory_consistency': float
        }
    """
```

#### Detection Logic Flow Chart

```
Ball Detected
    ↓
Calculate Ball Center (cx, cy)
    ↓
Hoop Detected? → NO → Skip frame
    ↓ YES
Define Hoop Zone (hoop_x ± 80px, hoop_y ± 100px)
    ↓
Is Ball Center in Zone?
    ↓ YES
Add to Shot Sequence (track frames in zone)
    ↓
Continue tracking for 3 seconds
    ↓
Shot Sequence Timeout
    ↓
Analyze Trajectory:
  - Did ball pass through zone vertically?
  - Downward movement >= 50px?
  - Consistency >= 0.7?
    ↓ YES → MADE
    ↓ NO  → MISSED
```

#### Shot Sequence Data Structure

```python
shot_sequence = {
    'frames_in_zone': [],          # List of frame numbers
    'ball_positions': [],          # List of (x, y) positions
    'hoop_position': (x, y),       # Hoop center
    'start_frame': int,
    'end_frame': int,
    'timestamp_seconds': float,

    # Analysis results
    'vertical_passage': bool,
    'downward_movement': float,
    'upward_movement': float,
    'trajectory_consistency': float,

    # Classification
    'outcome': 'made'/'missed',
    'outcome_reason': str,
    'decision_confidence': float
}
```

##### 6. `draw_overlay(frame, detections)`
- Draw bounding boxes for ball and hoop
- Draw hoop zone (vertical column)
- Draw ball trajectory
- Show shot count and current stats
- Display confidence scores

##### 7. `save_session_data(output_path)`
- Save all detected shots to JSON
- Include video metadata
- Format compatible with accuracy validator

---

### 3. Accuracy Validator (`accuracy_validator.py`)

**Reuse from Near Angle**: The accuracy validation logic is the same for both angles.

**Copy from**: `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_near_angle_shot_detection/accuracy_validator.py`

**Key Methods**:
1. `fetch_ground_truth(game_id, angle)`: Fetch shots from Supabase
2. `match_shots_by_timestamp()`: Match detected shots to ground truth (2-second window)
3. `calculate_accuracy_metrics()`: Calculate matched/unmatched/incorrect stats
4. `generate_accuracy_report()`: Create detailed JSON report
5. `create_results_folder()`: Create UUID-based results folder

**No modifications needed** - this module works for both near and far angle.

---

### 4. Video Processing Workflow

```python
def process_video(video_path, model_path, game_id=None, validate_accuracy=False, angle=None):
    # 1. Initialize
    analyzer = ShotAnalyzer(model_path)
    cap = cv2.VideoCapture(video_path)

    # 2. Setup output
    output_path = video_path.parent / f"{video_path.stem}_detected.mp4"
    session_json_path = video_path.parent / f"{video_path.stem}_session.json"

    # 3. Process frames
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect objects
        detections = analyzer.detect_objects(frame)

        # Update shot tracking
        analyzer.update_shot_tracking(detections)

        # Draw overlay
        annotated_frame = analyzer.draw_overlay(frame, detections)

        # Write output
        out.write(annotated_frame)

    # 4. Save session data
    analyzer.save_session_data(session_json_path)

    # 5. Validate accuracy (optional)
    if validate_accuracy:
        validator = AccuracyValidator()
        results_folder = validator.create_results_folder(video_path=video_path)

        # Fetch ground truth
        ground_truth = validator.fetch_ground_truth(game_id, angle)

        # Match shots
        accuracy_results = validator.match_shots_by_timestamp(
            detected_shots=analyzer.detected_shots,
            ground_truth_shots=ground_truth
        )

        # Generate report
        validator.generate_accuracy_report(results_folder, accuracy_results)
```

---

## 📊 Output Format

### Session JSON (`{video_name}_session.json`)

```json
{
  "video_path": "Game-1/game1_farleft.mp4",
  "model_path": "runs/detect/basketball_yolo11n/weights/best.pt",
  "fps": 29,
  "frame_count": 88788,
  "duration_seconds": 3061.65,
  "processing_timestamp": "2025-11-05T16:30:00",
  "detection_version": "far_angle_v1",

  "stats": {
    "total_shots": 45,
    "made_shots": 28,
    "missed_shots": 17,
    "undetermined_shots": 0
  },

  "shots": [
    {
      "timestamp_seconds": 17.45,
      "frame": 506,
      "outcome": "made",
      "outcome_reason": "vertical_passage_through_zone",
      "decision_confidence": 0.92,
      "detection_confidence": 0.87,

      "frames_in_zone": 5,
      "vertical_passage": true,
      "downward_movement": 145.3,
      "upward_movement": 12.1,
      "trajectory_consistency": 0.89,

      "ball_final_position": [850, 620],
      "hoop_position": [825, 450],
      "zone_width": 80,

      "trajectory": [
        {"frame": 502, "x": 820, "y": 380},
        {"frame": 503, "x": 823, "y": 410},
        {"frame": 504, "x": 825, "y": 445},
        {"frame": 505, "x": 827, "y": 485},
        {"frame": 506, "x": 830, "y": 525}
      ]
    }
  ]
}
```

### Accuracy Analysis JSON (`results/{uuid}/accuracy_analysis.json`)

```json
{
  "summary": {
    "total_detected": 45,
    "total_ground_truth": 48,
    "matched_correct": 41,
    "matched_incorrect": 3,
    "missing_from_ground_truth": 1,
    "unmatched_ground_truth": 4,

    "matched_shots_accuracy": 93.18,
    "overall_accuracy": 91.11,
    "precision": 97.78,
    "recall": 91.67
  },

  "matched_correct": [...],
  "matched_incorrect": [...],
  "missing_from_ground_truth": [...],
  "unmatched_ground_truth": [...]
}
```

---

## 🧪 Testing Strategy

### Phase 1: Basic Detection Testing
```bash
# Test first 2 minutes to verify detection works
python main.py --action video \
    --video_path Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --start_time 0 \
    --end_time 120
```

**Verify**:
- Ball and hoop are detected
- Hoop zone is drawn correctly
- Ball trajectory is tracked
- Shots are being detected

### Phase 2: Classification Testing
```bash
# Process longer segment to test classification
python main.py --action video \
    --video_path Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --start_time 0 \
    --end_time 600
```

**Verify**:
- Made shots are correctly classified
- Missed shots are correctly classified
- Session JSON has proper data

### Phase 3: Accuracy Validation
```bash
# Full video with ground truth validation
python main.py --action video \
    --video_path Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --validate_accuracy \
    --angle LEFT
```

**Target Metrics**:
- Matched shots accuracy: ≥ 90%
- Overall accuracy: ≥ 85%
- Precision: ≥ 90%
- Recall: ≥ 85%

### Phase 4: Both Angles
```bash
# Test LEFT angle
python main.py --action video \
    --video_path Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --validate_accuracy \
    --angle LEFT

# Test RIGHT angle
python main.py --action video \
    --video_path Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --validate_accuracy \
    --angle RIGHT
```

**Compare**:
- LEFT vs RIGHT accuracy
- Consistency across angles

---

## 🎨 Visualization Requirements

### Annotated Video Overlay

1. **Bounding Boxes**:
   - Ball: Yellow box with confidence score
   - Hoop: Green box with confidence score

2. **Hoop Zone Visualization**:
   - Draw vertical zone (semi-transparent blue rectangle)
   - Width: ±80px from hoop center
   - Height: ±100px from hoop center

3. **Ball Trajectory**:
   - Draw line connecting last 30 ball positions
   - Color: White (normal), Yellow (in zone), Green (made), Red (missed)

4. **Shot Detection Indicators**:
   - When shot detected: Flash "SHOT DETECTED" text
   - Show outcome: "MADE" (green) or "MISSED" (red)
   - Show confidence score

5. **Stats Overlay** (top-left corner):
   - Frame number
   - Timestamp
   - Total shots: XX
   - Made: XX | Missed: XX
   - Current: Made/Missed (if recent shot)

---

## 📋 Implementation Checklist

### Step 1: Setup
- [ ] Copy `accuracy_validator.py` from near angle
- [ ] Verify `.env` has Supabase credentials
- [ ] Confirm trained model exists at `runs/detect/basketball_yolo11n/weights/best.pt`

### Step 2: Implement `shot_detection.py`
- [ ] Create `ShotAnalyzer` class
- [ ] Implement `__init__()` with far angle parameters
- [ ] Implement `detect_objects()`
- [ ] Implement `is_ball_in_hoop_zone()`
- [ ] Implement `detect_vertical_passage()`
- [ ] Implement `classify_shot()`
- [ ] Implement `update_shot_tracking()`
- [ ] Implement `draw_overlay()` with zone visualization
- [ ] Implement `save_session_data()`

### Step 3: Implement `main.py`
- [ ] Create command-line argument parser
- [ ] Implement `process_video()` function
- [ ] Integrate ShotAnalyzer
- [ ] Integrate AccuracyValidator
- [ ] Add results folder creation
- [ ] Add progress indicators
- [ ] Add error handling

### Step 4: Testing
- [ ] Test basic detection (Phase 1)
- [ ] Test classification logic (Phase 2)
- [ ] Test accuracy validation (Phase 3)
- [ ] Test both angles (Phase 4)
- [ ] Verify output files are generated
- [ ] Verify JSON format is correct

### Step 5: Documentation
- [ ] Create README.md for far angle
- [ ] Document command examples
- [ ] Document accuracy results
- [ ] Document differences from near angle

---

## 🔍 Known Challenges & Solutions

### Challenge 1: Hoop Zone Definition
**Problem**: Hoop size varies with distance from camera
**Solution**:
- Use adaptive zone based on hoop bounding box size
- `HOOP_ZONE_WIDTH = hoop_bbox_width * 1.2`

### Challenge 2: Ball Occlusion
**Problem**: Ball hidden behind players
**Solution**:
- Use Kalman filter for position prediction
- Allow gaps in trajectory tracking
- Require minimum frames for shot classification

### Challenge 3: Fast Shots
**Problem**: Ball moves through zone in < 3 frames
**Solution**:
- Lower minimum frames threshold for high-confidence detections
- Use weighted scoring based on trajectory consistency

### Challenge 4: Rim Bounces
**Problem**: Ball bounces off rim but stays in zone
**Solution**:
- Detect upward movement after downward passage
- If upward_movement > downward_movement/2 → MISSED
- Track velocity reversals

---

## 🎯 Success Criteria

### Minimum Viable Product (MVP)
- ✅ Detect shots from far angle video
- ✅ Classify as MADE/MISSED
- ✅ Generate session JSON
- ✅ Create annotated video
- ✅ Achieve 80%+ matched shots accuracy

### Target Performance
- ✅ 90%+ matched shots accuracy
- ✅ 85%+ overall accuracy
- ✅ < 10% false positive rate
- ✅ < 10% false negative rate

### Future Enhancements (Post-MVP)
- Dual-camera fusion with near angle
- Real-time processing optimization
- Player tracking integration
- Shot type classification (layup, jump shot, etc.)

---

## 📚 Reference Files

### Existing Files (Already in Repository)
- `create_training_clips.py`: Dataset preparation (working)
- `process_video.py`: Model validation tool (working)
- `custom_training.py`: Model training pipeline (working)
- `requirements.txt`: Dependencies (working)

### Files from Near Angle (To Reference)
- `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_near_angle_shot_detection/main.py`
- `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_near_angle_shot_detection/shot_detection.py`
- `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_near_angle_shot_detection/accuracy_validator.py`

### Database Schema Reference
Located in this file under "Supabase Database Schema" section

---

## 💡 Implementation Notes

1. **Start Simple**: Begin with basic zone detection, then add complexity
2. **Test Incrementally**: Test each method before moving to next
3. **Use Near Angle as Template**: Structure should mirror near angle for consistency
4. **Visualize Everything**: Draw zones, trajectories, etc. for debugging
5. **Log Verbosely**: Print detection decisions for debugging
6. **Validate Early**: Run accuracy validation frequently during development

---

## 📞 Support Resources

- **Near Angle Implementation**: Reference for structure and patterns
- **YOLOv11 Docs**: https://docs.ultralytics.com/
- **OpenCV Docs**: https://docs.opencv.org/
- **Supabase Docs**: https://supabase.com/docs

---

**End of Implementation Plan**

*This plan should be used to implement the far angle shot detection system in a new session. All necessary details, logic, and structure are documented above.*
