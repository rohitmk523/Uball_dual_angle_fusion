# Dual Angle Fusion - Basketball Shot Detection

Combines near angle and far angle shot detection systems for improved basketball shot classification accuracy.

## Overview

This repository implements a fusion algorithm that combines detections from two complementary camera angles:

- **Near Angle (Primary)**: Front-view camera, 88% accuracy, excellent general shot detection
- **Far Angle (Specialist)**: Side-view camera, 68% accuracy, excels at rim bounces and clean swishes

**Goal**: Achieve >90% matched shot accuracy by leveraging the strengths of both systems.

## Key Features

- **Smart Fusion Logic**: Combines detections using confidence-based rules
- **Specialist Override**: Far angle corrects near angle on rim bounces and swishes
- **Comprehensive Validation**: Compares individual and fused results against ground truth
- **Detailed Reports**: JSON outputs with fusion decisions and accuracy metrics

## Repository Structure

```
Uball_dual_angle_fusion/
├── dual_fusion.py                           # Main fusion engine
├── requirements.txt                         # Dependencies
├── README.md                               # This file
│
├── input/                                   # Input videos
│   ├── game1_nearleft.mp4
│   └── game1_farright.mp4
│
├── Uball_near_angle_shot_detection/        # Near angle system
│   ├── main.py
│   ├── shot_detection.py
│   └── results/
│
├── Uball_far_angle_shot_detection/         # Far angle system
│   ├── main.py
│   ├── shot_detection.py
│   └── results/
│
└── results/                                 # Fusion outputs
    └── [session_uuid]/
        ├── fused_session.json              # Combined detections
        ├── fusion_analysis.json            # Decision breakdown
        └── accuracy_report.json            # Performance metrics
```

## Fusion Algorithm

### Decision Rules

The fusion algorithm applies the following priority rules:

#### 1. Agreement (Both angles agree)
```
If near_outcome == far_outcome:
    → Use agreed outcome
    → Boost confidence: (near_conf + far_conf) / 2 + 0.1
```

#### 2. Near MADE + Far MISSED
```
If far detected RIM BOUNCE with high confidence (>0.90):
    → Override: Use FAR (MISSED) ✅
    → Reason: Far angle advantage on rim bounces
Else:
    → Use NEAR (MADE) - Near is primary
```

#### 3. Near MISSED + Far MADE
```
If far detected CLEAN SWISH with high confidence (>0.90):
    → Override: Use FAR (MADE) ✅
    → Reason: Far angle advantage on swishes
Else:
    → Use NEAR (MISSED) - Near is primary
```

#### 4. Single Angle Only
```
If only one angle detected the shot:
    → Use that angle if confidence > 0.75
    → Otherwise: Keep but mark as low confidence
```

### Shot Matching

Shots from both angles are matched by timestamp with a 2-second tolerance window:
```python
if abs(near_timestamp - far_timestamp) <= 2.0:
    # Consider it the same shot
    match_shots(near_shot, far_shot)
```

## Installation

```bash
# Clone the repository
cd Uball_dual_angle_fusion

# Install dependencies (optional, fusion only needs JSON inputs)
pip install -r requirements.txt
```

## Usage

### Step 1: Process Both Angles Independently

**Near Angle:**
```bash
cd Uball_near_angle_shot_detection
python main.py --action video \
    --video_path ../input/game1_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt
```

**Far Angle:**
```bash
cd Uball_far_angle_shot_detection
python main.py --action video \
    --video_path ../input/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt
```

### Step 2: Run Fusion

```bash
python dual_fusion.py \
    --near_results Uball_near_angle_shot_detection/results/[uuid]/detection_results.json \
    --far_results Uball_far_angle_shot_detection/results/[uuid]/detection_results.json \
    --ground_truth Uball_near_angle_shot_detection/results/[uuid]/ground_truth.json \
    --output_dir results/fusion_[timestamp]
```

### Example with Game 1:

```bash
python dual_fusion.py \
    --near_results Uball_near_angle_shot_detection/results/09-23\(1-NL\)_fc2a92db-5a81-4f2a-acda-3e86b9098356/detection_results.json \
    --far_results Uball_far_angle_shot_detection/results/game1-farright_b8c98465-3d89-4cbf-be78-1740432be0ee/detection_results.json \
    --ground_truth Uball_near_angle_shot_detection/results/09-23\(1-NL\)_fc2a92db-5a81-4f2a-acda-3e86b9098356/ground_truth.json \
    --output_dir results/game1_fusion
```

## Output Files

### 1. `fused_session.json`
Combined detection results with fusion decisions:
```json
{
  "fusion_info": {...},
  "matching_summary": {
    "near_shots_total": 130,
    "far_shots_total": 156,
    "matched_pairs": 75,
    "near_only": 55,
    "far_only": 81
  },
  "statistics": {
    "total_shots": 211,
    "made_shots": 95,
    "missed_shots": 116
  },
  "shots": [...]
}
```

### 2. `fusion_analysis.json`
Detailed breakdown of every fusion decision:
```json
{
  "fusion_decisions": [
    {
      "timestamp_seconds": 381.5,
      "outcome": "missed",
      "fusion_method": "far_rim_bounce_override",
      "confidence": 0.95,
      "reason": "Far angle detected rim bounce: rim_bounce_frames (conf: 0.95 vs near: 0.85)",
      "override": true
    }
  ]
}
```

### 3. `accuracy_report.json`
Performance comparison:
```json
{
  "near_angle_performance": {
    "matched_shots_accuracy": 88.0,
    "overall_accuracy": 50.77,
    "false_positives": 55
  },
  "far_angle_performance": {
    "matched_shots_accuracy": 65.33,
    "overall_accuracy": 31.41,
    "false_positives": 81
  },
  "fused_performance": {
    "matched_shots_accuracy": 92.0,
    "overall_accuracy": 55.45,
    "false_positives": 52
  },
  "improvement_analysis": {
    "matched_accuracy_improvement": 4.0,
    "false_positive_change": -3
  }
}
```

## Expected Performance

| Metric | Near Angle | Far Angle | Fused (Target) |
|--------|------------|-----------|----------------|
| **Matched Shot Accuracy** | 88% | 68% | **>90%** ✅ |
| **Overall Accuracy** | 63% | 32% | **>65%** |
| **False Positives** | 55 | 81 | **<55** |

### Fusion Benefits

1. **Rim Bounce Correction**: Far angle corrects ~8 cases where near angle misclassified rim bounces
2. **Swish Detection**: Far angle catches clean swishes that near angle missed
3. **Confidence Boost**: Agreement between angles increases confidence
4. **False Positive Reduction**: Single-angle-only detections filtered by confidence

## Camera Syncing

The system assumes near-left and far-right cameras are synchronized:
- **Synced Pair 1**: Near-Left ↔ Far-Right
- **Synced Pair 2**: Near-Right ↔ Far-Left

Videos should be time-aligned (±2 seconds tolerance is acceptable).

## Troubleshooting

### Issue: Low fusion accuracy

**Check:**
1. Are the videos from synced camera pairs?
2. Is the timestamp tolerance appropriate? (try adjusting `--tolerance`)
3. Are confidence thresholds in the fusion logic appropriate?

### Issue: Too many false positives in fused results

**Solution:**
- Increase the `min_confidence` threshold in `handle_single_angle()` (currently 0.75)
- Filter out single-angle-only detections with low confidence

### Issue: Missing expected improvements

**Debug:**
1. Check `fusion_analysis.json` to see which fusion methods are being used
2. Look for `far_rim_bounce_override` and `far_swish_override` - these should be triggering
3. Verify far angle is detecting rim bounces with high confidence (>0.90)

## Development Roadmap

- [x] Basic fusion implementation
- [x] Validation against ground truth
- [x] Comprehensive reporting
- [ ] Confidence threshold tuning
- [ ] Web UI for fusion visualization
- [ ] Real-time fusion for live games
- [ ] Multi-game batch processing

## Contributing

This is part of the Uball basketball analytics system. For questions or improvements, refer to the individual angle detection repositories.

## References

- **Near Angle System**: `Uball_near_angle_shot_detection/`
- **Far Angle System**: `Uball_far_angle_shot_detection/`
- **Fusion Strategy**: `Uball_far_angle_shot_detection/DUAL_ANGLE_FUSION_STRATEGY.md`

---

**Last Updated**: November 6, 2025
**Version**: 1.0
**Target**: >90% Matched Shot Accuracy
