# 📚 Far Angle Shot Detection - Scripts Reference Guide

**Complete reference for all commands - FORMAT MATCHES NEAR ANGLE!**

---

## 🎥 Video Processing

### Process Full Video with Validation (Matches Near Angle!)
```bash
python main.py --action video \
    --video_path 09-23/Game-2/game2_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id c07e85e8-9ae4-4adc-a757-3ca00d9d292a \
    --validate_accuracy \
    --angle RIGHT
```

**Output:**
- Auto-generates UUID-based directory: `results/09-23(1-FR)_<uuid>/`
- Files created:
  - `detection_results.json` - All shots with far angle features
  - `ground_truth.json` - Ground truth from Supabase
  - `accuracy_analysis.json` - Detailed accuracy metrics
  - `session_summary.json` - Quick summary
  - `processed_video.mp4` - Annotated video

### Process Without Validation
```bash
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt
```

**Output:**
- `game1_farright_detected.mp4` - Annotated video
- `game1_farright_session.json` - Detection results

### Process with Time Range
```bash
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 0 \
    --end_time 300
```

### Process Specific Segment with Validation
```bash
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 0 \
    --end_time 300 \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT
```

---

## 🧪 Test Specific Timestamps (Old Method - Still Available)

```bash
python simple_line_intersection_test.py \
    --mode test \
    --video "09-23/Game-1/game1_farright.mp4" \
    --model "runs/detect/basketball_yolo11n2/weights/best.pt" \
    --timestamps "26.8,63.1,91.7"
```

**Note:** This is for debugging only. Use `python main.py` for production.

---

## 📊 Argument Comparison

### Far Angle (NEW - Matches Near Angle!)
```bash
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT
```

### Near Angle (Reference)
```bash
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT
```

**Arguments:**
- `--action video` - Process video mode
- `--video_path` - Path to video file
- `--model` - Path to YOLO model
- `--game_id` - UUID from Supabase database
- `--validate_accuracy` - Enable ground truth validation
- `--angle LEFT/RIGHT` - Filter ground truth by angle
- `--start_time` - Optional start time (seconds or HH:MM:SS)
- `--end_time` - Optional end time (seconds or HH:MM:SS)

---

## 📂 Result Directory Structure

### With Validation (Auto-Generated UUID Directory)
```
results/
└── 11-13(1-FR)_7f3e4b2a-9d1c-4e8f-b6a5-1c8d9e2f4a3b/
    ├── detection_results.json      # Far angle shot detections
    ├── accuracy_analysis.json      # Precision, recall, F1 metrics
    ├── ground_truth.json           # Ground truth from Supabase
    ├── processed_video.mp4         # Annotated video
    └── session_summary.json        # High-level stats
```

**Naming:** `MM-DD(GAME-ANGLE)_UUID`
- **Date:** MM-DD format (e.g., `11-13`)
- **Game:** Game number (e.g., `1`, `2`, `3`)
- **Angle:** `FL` (Far Left) or `FR` (Far Right)
- **UUID:** Random UUID (fetched from video path naming)

### Without Validation (Same Directory as Video)
```
09-23/Game-1/
├── game1_farright.mp4
├── game1_farright_detected.mp4
└── game1_farright_session.json
```

---

## 🔍 Analysis Commands

### Check Detection Results
```bash
# View statistics
cat results/[UUID]/detection_results.json | jq '.stats'

# View first shot
cat results/[UUID]/detection_results.json | jq '.shots[0]'

# Count shots by outcome
cat results/[UUID]/detection_results.json | jq '[.shots[].outcome] | group_by(.) | map({outcome: .[0], count: length})'
```

### Check Accuracy Metrics
```bash
# View overall accuracy
cat results/[UUID]/accuracy_analysis.json | jq '.metrics'

# View detailed matches
cat results/[UUID]/accuracy_analysis.json | jq '.matches'
```

### Find Latest Result
```bash
# Find latest result directory
ls -t results/ | head -1

# View latest summary
cat results/$(ls -t results/ | head -1)/session_summary.json | jq
```

---

## 🚀 Quick Reference

### Most Common Commands

**Process with validation (Production):**
```bash
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT
```

**Quick test (first 5 minutes):**
```bash
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 0 \
    --end_time 300
```

**Debug specific timestamps:**
```bash
python simple_line_intersection_test.py \
    --mode test \
    --video "09-23/Game-1/game1_farright.mp4" \
    --model "runs/detect/basketball_yolo11n2/weights/best.pt" \
    --timestamps "26.8,63.1,91.7"
```

---

## 📊 Useful One-Liners

```bash
# Find latest result
ls -t results/ | head -1

# Check statistics
cat detection_results.json | jq '.stats'

# Get shooting percentage
cat detection_results.json | jq '(.stats.made_shots / .stats.total_shots * 100)'

# Find made shots
cat detection_results.json | jq '.shots[] | select(.outcome == "made")'

# Extract all timestamps
cat detection_results.json | jq -r '.shots[].timestamp_seconds'

# Find complete pass-through shots
cat detection_results.json | jq '.shots[] | select(.outcome_reason | contains("complete_pass_through"))'

# Find rim bounces
cat detection_results.json | jq '.shots[] | select(.bounced_back_out == true)'
```

---

## 🔧 Model Selection

```bash
# YOLOv11 nano v2 (current default)
--model runs/detect/basketball_yolo11n2/weights/best.pt

# YOLOv11 nano (alternative)
--model runs/detect/basketball_yolo11n/weights/best.pt

# Training checkpoint
--model runs/detect/train9/weights/best.pt
```

---

## 📈 Example Workflows

### Complete Validation Workflow
```bash
# 1. Process with validation
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT

# 2. Check results (UUID auto-generated from video path)
LATEST=$(ls -t results/ | head -1)
cat results/$LATEST/session_summary.json | jq

# 3. View accuracy
cat results/$LATEST/accuracy_analysis.json | jq '.metrics'

# 4. Watch annotated video
open results/$LATEST/processed_video.mp4
```

### Test Then Validate
```bash
# 1. Quick test first 5 minutes
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 0 \
    --end_time 300

# 2. If good, run full game with validation
python main.py --action video \
    --video_path 09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT
```

---

**Last Updated:** 2025-11-13
**Detection Method:** Line Intersection V4
**Command Format:** Matches Near Angle Exactly!
