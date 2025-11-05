# Basketball Shot Detection System

A comprehensive basketball shot detection system using YOLOv11 for object detection and enhanced multi-factor analysis for shot outcome classification.

## Features

- **Enhanced Shot Detection**: Multi-factor analysis combining overlap, trajectory, and physics-based indicators
- **Accuracy Validation**: Automated ground truth comparison with detailed mismatch analysis
- **Multi-Camera Ready**: Architecture supports synced dual-camera analysis
- **Post-Processing Optimized**: Designed for batch video processing, not real-time
- **Made/Missed Classification**: Advanced decision logic with confidence scoring
- **Rim Bounce Detection**: Physics-based detection of shots that hit the rim
- **Entry Angle Analysis**: Calculates ball entry angle for better classification
- **Trajectory Smoothing**: Kalman filtering for stable ball tracking

## Camera Setup

This system is designed for near-angle camera placement, with support for opposite-angle (far) camera integration. The system works with synced footage from both angles to maximize detection accuracy.

## Installation

1. Clone the repository:
```bash
git clone <repository_url>
cd Uball_near_angle_shot_detection
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Supabase credentials for ground truth validation
```

## Input Videos

Place your original basketball game videos in the `input/` directory:
- `input/game2_nearleft.mp4` - Game 2 near angle
- `input/game3_nearleft.mp4` - Game 3 near angle
- `input/game3_nearright.mp4` - Game 3 far angle (synced with near left)

Processed videos and session JSONs will be saved alongside the input videos. Full validation results are saved in `results/[uuid]/`.

## Quick Start

### 1. Process a Video with Enhanced Detection

```bash
# Process full video
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt
```

**Output:**
- `input/game3_nearleft_detected.mp4` - Video with shot annotations
- `input/game3_nearleft_session.json` - Detailed shot data

### 2. Process a Time Range (Faster Testing)

```bash
# Process first 2 minutes
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 0 \
    --end_time 120
```

### 3. Validate Accuracy Against Ground Truth

```bash
# Full validation with Supabase ground truth
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT
```

**Output Location:** `results/[uuid]/`
- `detection_results.json` - All detected shots with enhanced analysis
- `ground_truth.json` - Ground truth from Supabase
- `accuracy_analysis.json` - Detailed accuracy metrics and mismatches
- `session_summary.json` - Quick summary
- `original_video.mp4` & `processed_video.mp4`

### 4. Compare Algorithm Versions

```bash
python test_enhanced_detection.py \
    --old results/OLD_UUID/detection_results.json \
    --new results/NEW_UUID/detection_results.json \
    --analyze
```

### 5. Train Custom Models (Optional)

```bash
# Setup training environment
python custom_training.py --action setup

# Train with custom dataset
python custom_training.py --action train --epochs 50 --batch_size 8
```

## Enhanced Detection Algorithm

The system uses a multi-factor analysis approach:

### Core Features

1. **Box Overlap Analysis**
   - Calculates intersection between ball and hoop bounding boxes
   - Tracks overlap percentage over time
   - Uses weighted scoring for fast shots

2. **Entry Angle Detection**
   - Calculates ball's approach angle to the hoop
   - Steeper angles indicate higher make probability
   - Helps distinguish swishes from rim bounces

3. **Post-Hoop Trajectory**
   - Tracks ball movement after hoop interaction
   - Detects if ball continues downward (made) or bounces back (missed)
   - Uses Kalman filtering for smooth trajectory tracking

4. **Rim Bounce Detection**
   - Multi-factor scoring: vertical velocity changes, trajectory reversals
   - Confidence-based override for ambiguous cases
   - Physics-based validation

5. **Duplicate Prevention**
   - 2-second window to prevent multiple detections of same shot
   - Position-based clustering for nearby shots

### Decision Logic Thresholds

- **Certain Made**: 6+ frames at 100% overlap OR 4+ at 100% with 7+ at 95%
- **Certain Missed**: High-confidence rim bounce detection (>60%)
- **Fast Swish**: Weighted overlap score 3.5+ with good indicators
- **Ambiguous**: Moderate overlap requires supporting evidence

## Project Structure

```
├── input/                          # Input videos (tracked in git)
│   ├── game2_nearleft.mp4
│   ├── game3_nearleft.mp4
│   └── game3_nearright.mp4
├── results/                        # Validation outputs (ignored by git)
│   └── [uuid]/
│       ├── detection_results.json
│       ├── ground_truth.json
│       ├── accuracy_analysis.json
│       └── processed_video.mp4
├── docs/                           # Documentation & references
│   └── reference_images/
├── runs/                           # YOLO training runs (ignored by git)
│   └── detect/
│       └── basketball_yolo11n3/
│           └── weights/best.pt
├── main.py                         # Main entry point
├── shot_detection.py               # Enhanced shot detection logic
├── accuracy_validator.py           # Ground truth validation
├── custom_training.py              # Model training pipeline
├── test_enhanced_detection.py      # Compare detection results
├── requirements.txt                # Python dependencies
├── SCRIPTS_REFERENCE.md            # Complete command reference
├── IMPROVEMENTS_V2.md              # Algorithm improvements plan
└── TESTING_GUIDE.md                # Testing instructions
```

## Video-to-Game Mapping

For accuracy validation, map videos to Supabase game IDs:

```bash
# input/game3_nearleft.mp4
--game_id a3c9c041-6762-450a-8444-413767bb6428 --angle LEFT

# input/game3_nearright.mp4 (synced with near left, no offset)
--game_id a3c9c041-6762-450a-8444-413767bb6428 --angle RIGHT

# input/game2_nearleft.mp4
--game_id c07e85e8-9ae4-4adc-a757-3ca00d9d292a --angle RIGHT
```

## Common Commands

See [`SCRIPTS_REFERENCE.md`](SCRIPTS_REFERENCE.md) for complete command reference.

### Quick Test (2 minutes)
```bash
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 0 --end_time 120
```

### Validate Full Game
```bash
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy --angle LEFT
```

### Compare Results
```bash
python test_enhanced_detection.py \
    --old results/OLD_UUID/detection_results.json \
    --new results/NEW_UUID/detection_results.json \
    --analyze
```

## Accuracy Metrics

The system calculates detailed accuracy metrics:

### Detection Accuracy
- **Total Detected vs Ground Truth**: Count comparison
- **Timestamp Matching**: 2-second window for matches
- **Matched Correct/Incorrect**: Outcome classification accuracy
- **Unmatched/Extra**: Detection precision

### Outcome Classification
- **Made Shot Accuracy**: True positive rate for made shots
- **Missed Shot Accuracy**: True positive rate for missed shots
- **Overall Accuracy**: Combined classification accuracy
- **Confidence Distribution**: Per-outcome confidence analysis

### Latest Results (Game 3 Near Left)
- Detection: ~77-83% outcome accuracy (baseline)
- Target: 90%+ with enhanced multi-factor analysis
- Future: 95%+ with dual-camera fusion

## Performance Characteristics

- **Processing Speed**: ~5-15 FPS (post-processing, not optimized for real-time)
- **Model**: YOLOv11n (nano) for speed vs accuracy balance
- **Memory**: ~2-4GB for video processing
- **GPU**: Optional (CPU processing is supported)

## Troubleshooting

### PyTorch 2.6+ Weight Loading Error

If you encounter `_pickle.UnpicklingError: Weights only load failed`:
- **Fixed**: The code now handles PyTorch 2.6+ security changes
- **Solution**: `torch.serialization.add_safe_globals([DetectionModel])` is called automatically

### Low Accuracy

1. **Check Hoop Detection**: Ensure hoop is consistently detected
2. **Review Overlap Thresholds**: Adjust in `shot_detection.py` if needed
3. **Validate Time Ranges**: Test specific problematic timestamps
4. **Check Ground Truth**: Ensure Supabase data is correct and synced

### Missing Detections

1. **Ball Occlusion**: Ball hidden behind players/structures
2. **Low Confidence**: Adjust YOLO confidence threshold
3. **Fast Motion**: Ball moves too quickly between frames
4. **Camera Angle**: Some shots may be out of view

## Next Steps

1. **Single-Camera Optimization** (Current Phase)
   - Refine multi-factor analysis thresholds
   - Improve rim bounce detection
   - Target: 90%+ accuracy

2. **Dual-Camera Integration** (Next Phase)
   - Correlate detections from synced opposite cameras
   - Fusion algorithm for combined decision making
   - Target: 95%+ accuracy

3. **Production Deployment**
   - Optimize processing speed
   - Batch processing pipeline
   - API integration

## References

- **SCRIPTS_REFERENCE.md**: Complete command reference
- **IMPROVEMENTS_V2.md**: Algorithm enhancement plan
- **TESTING_GUIDE.md**: Testing instructions

## Acknowledgments

- **YOLOv11** by Ultralytics - Object detection framework
- **OpenCV** - Computer vision operations
- **FilterPy** - Kalman filtering for trajectory smoothing
- **SciPy** - Gaussian smoothing for signal processing