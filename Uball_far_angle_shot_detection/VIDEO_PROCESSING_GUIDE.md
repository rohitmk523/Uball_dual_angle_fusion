# Video Processing Guide

## Overview

The `process_video.py` script processes basketball game videos using your trained YOLO model to detect and track basketballs and hoops. It generates:
- **Annotated video** with bounding boxes and labels
- **JSON report** with detailed detection data and ball-hoop tracking analysis

## Features

- ✅ Real-time detection visualization with bounding boxes
- ✅ Confidence scores displayed on detections
- ✅ Frame-by-frame detection logging
- ✅ Ball-hoop proximity tracking and analysis
- ✅ Ball trajectory analysis (moving towards/away from hoop)
- ✅ Time-range processing (test specific segments)
- ✅ Comprehensive JSON report with all detection data

## Quick Start

### Process Full Video

```bash
python process_video.py \
    --input Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt
```

### Process Specific Time Range (30s to 60s)

```bash
python process_video.py \
    --input Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --start 30 \
    --end 60
```

### Process with Custom Confidence Threshold

```bash
python process_video.py \
    --input Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --conf 0.5 \
    --start 0 \
    --end 120
```

## Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--input` | Yes | - | Path to input video file |
| `--model` | Yes | - | Path to trained YOLO model (.pt file) |
| `--output` | No | Auto | Path for annotated output video |
| `--json-output` | No | Auto | Path for JSON detection report |
| `--start` | No | 0 | Start time in seconds |
| `--end` | No | End | End time in seconds |
| `--conf` | No | 0.25 | Confidence threshold (0.0-1.0) |

## Output Files

### 1. Annotated Video

**Filename**: `{input_name}_annotated_{start}s-{end}s.mp4`

**Features**:
- Bounding boxes around detections
  - Yellow boxes: Basketball
  - Green boxes: Basketball Hoop
- Confidence scores on each detection
- Frame number and timestamp overlay
- Ball-hoop distance (when both detected)
- "BALL NEAR HOOP!" indicator (when within threshold)

### 2. JSON Detection Report

**Filename**: `{input_name}_detections_{start}s-{end}s.json`

**Structure**:

```json
{
  "summary": {
    "input_video": "...",
    "model": "...",
    "detection_summary": {
      "total_frames_processed": 900,
      "frames_with_basketball": 650,
      "frames_with_hoop": 890,
      "frames_ball_near_hoop": 45,
      "basketball_detection_rate": 72.22,
      "hoop_detection_rate": 98.89,
      "ball_near_hoop_rate": 5.0
    }
  },
  "detections": [
    {
      "frame": 1234,
      "timestamp": 41.133,
      "time_formatted": "0:00:41.133000",
      "ball_detections": [
        {
          "class": "Basketball",
          "confidence": 0.876,
          "bbox": [450, 320, 480, 350],
          "center_x": 465.0,
          "center_y": 335.0,
          "width": 30.0,
          "height": 30.0
        }
      ],
      "hoop_detections": [...],
      "tracking_analysis": {
        "ball_near_hoop": true,
        "distance_to_hoop": 125.5,
        "ball_trajectory": "towards_hoop_upward",
        "relative_position": "above-left"
      }
    }
  ]
}
```

## Ball-Hoop Tracking Analysis

The script includes advanced tracking that analyzes ball movement relative to the hoop:

### Metrics Tracked:

1. **Distance to Hoop**: Euclidean distance in pixels
2. **Proximity Status**: Boolean flag when ball is within 200px of hoop
3. **Relative Position**: Ball position relative to hoop
   - Vertical: `above`, `level`, `below`
   - Horizontal: `left`, `center`, `right`
   - Combined: e.g., `"above-left"`, `"below-center"`

4. **Ball Trajectory**: Movement pattern analysis
   - `towards_hoop` - Ball moving closer to hoop
   - `away_from_hoop` - Ball moving away from hoop
   - `towards_hoop_upward` - Moving closer while going up
   - `towards_hoop_downward` - Moving closer while going down
   - `away_from_hoop_upward` - Moving away while going up
   - `stationary` - Not moving significantly

### Example Use Cases:

**Find all moments when ball is near hoop:**
```python
import json

with open('game1_farleft_detections.json', 'r') as f:
    data = json.load(f)

near_hoop_moments = [
    det for det in data['detections']
    if det['tracking_analysis']['ball_near_hoop']
]

print(f"Found {len(near_hoop_moments)} frames with ball near hoop")
for moment in near_hoop_moments[:5]:
    print(f"  Time: {moment['time_formatted']} | Distance: {moment['tracking_analysis']['distance_to_hoop']}px")
```

**Find shot attempts (ball moving towards hoop):**
```python
shot_attempts = [
    det for det in data['detections']
    if det['tracking_analysis'].get('ball_trajectory', '').startswith('towards_hoop')
]
```

## Workflow Examples

### Example 1: Quick Validation (First 60 Seconds)

```bash
# Process first minute to validate model
python process_video.py \
    --input Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --end 60

# Review: game1_farleft_annotated_0s-60s.mp4
# Check JSON: game1_farleft_detections_0s-60s.json
```

### Example 2: Process Specific Play (2:30 to 3:00)

```bash
python process_video.py \
    --input Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --start 150 \
    --end 180
```

### Example 3: High Confidence Only

```bash
# Only show detections with >70% confidence
python process_video.py \
    --input Game-1/game1_farleft.mp4 \
    --model runs/detect/basketball_yolo11n/weights/best.pt \
    --conf 0.7 \
    --start 0 \
    --end 300
```

## Performance

- **Processing Speed**: ~15-30 FPS (depending on hardware)
- **Memory Usage**: ~2-4GB RAM for 1080p video
- **Storage**: Annotated video ~same size as input

## Troubleshooting

**Issue**: Video processing is slow
- **Solution**: Process shorter segments using `--start` and `--end`
- **Solution**: Lower confidence threshold with `--conf` to skip low-confidence detections

**Issue**: Too many false positives
- **Solution**: Increase confidence threshold: `--conf 0.5`

**Issue**: Missing detections
- **Solution**: Lower confidence threshold: `--conf 0.15`

**Issue**: JSON file is very large
- **Solution**: Process smaller time ranges or implement frame sampling

## Next Steps

1. **Validate model performance**: Process representative clips from different game scenarios
2. **Fine-tune confidence threshold**: Find optimal balance between precision and recall
3. **Analyze ball-hoop interactions**: Use JSON data to identify shot patterns
4. **Compare models**: Process same clip with nano vs small model to compare
