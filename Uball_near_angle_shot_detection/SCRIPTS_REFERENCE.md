# 📚 Scripts Reference Guide

Complete reference for all commands and scripts used in the basketball shot detection system.

---

## 🎥 Video Processing

### Available Input Videos
```bash
input/game2_nearleft.mp4      # Game 2 - Near Left angle
input/game3_nearleft.mp4      # Game 3 - Near Left angle  
input/game3_nearright.mp4     # Game 3 - Near Right angle (far angle)
```

### Process Full Video
```bash
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt
```

**Output:**
- Processed video: `input/game3_nearleft_detected.mp4`
- Session JSON: `input/game3_nearleft_session.json`
- Validation results: `results/[uuid]/`

### Process Video with Time Range
```bash
# Using HH:MM:SS format
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 00:01:00 \
    --end_time 00:05:00

# Using MM:SS format
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 1:30 \
    --end_time 5:45

# Using seconds only
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 90 \
    --end_time 345
```

### Process Specific Shot Timestamp (Debug)
```bash
# Test shot at 71.9 seconds (±5 seconds)
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 67 \
    --end_time 77
```

---

## ✅ Accuracy Validation

### Validate with Ground Truth
```bash
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT
```

**Output Location:** `results/[uuid]/`
- `detection_results.json` - All detected shots
- `ground_truth.json` - Ground truth from Supabase
- `accuracy_analysis.json` - Detailed accuracy metrics
- `session_summary.json` - Quick summary
- `original_video.mp4` - Copy of input video
- `processed_video.mp4` - Annotated video

### Validate Time Range
```bash
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 0 \
    --end_time 300 \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT
```

### Video-to-Game Mapping
```bash
# input/game3_nearleft.mp4
--game_id a3c9c041-6762-450a-8444-413767bb6428 --angle LEFT

# input/game3_nearright.mp4  
--game_id a3c9c041-6762-450a-8444-413767bb6428 --angle RIGHT

# input/game2_nearleft.mp4
--game_id c07e85e8-9ae4-4adc-a757-3ca00d9d292a --angle RIGHT
```

---

## 📊 Compare Results

### Compare Two Sessions
```bash
python test_enhanced_detection.py \
    --old results/65ea832e-3b10-4a55-9be7-cf3803f4f8ee/detection_results.json \
    --new results/d55f148c-bf16-4750-9729-22f33e995863/detection_results.json \
    --analyze
```

### Compare Session Files (Alternative)
```bash
# Using session JSON files (they're saved in input/ folder)
python test_enhanced_detection.py \
    --old input/game3_nearleft_session_old.json \
    --new input/game3_nearleft_session.json \
    --analyze
```

### Quick Stats Check (Using jq)
```bash
# Get basic statistics
cat game3_nearleft_session.json | jq '.statistics'

# Check detection method
cat game3_nearleft_session.json | jq '.shots[0].detection_method'

# Count made vs missed
cat game3_nearleft_session.json | jq '[.shots[].outcome] | group_by(.) | map({outcome: .[0], count: length})'
```

---

## 🔍 Analysis Commands

### Check Enhanced Features
```bash
# View first shot with all enhanced fields
cat session.json | jq '.shots[0]'

# Check entry angles
cat session.json | jq '[.shots[].entry_angle] | add / length'

# Find rim bounces
cat session.json | jq '[.shots[] | select(.is_rim_bounce == true)] | length'

# Check decision confidence distribution
cat session.json | jq '[.shots[].decision_confidence] | group_by(. >= 0.8) | map(length)'
```

### Find Specific Timestamps
```bash
# Find shot at specific time (±2 seconds)
cat session.json | jq '.shots[] | select(.timestamp_seconds > 70 and .timestamp_seconds < 74)'

# Get all shots in time range
cat session.json | jq '.shots[] | select(.timestamp_seconds > 100 and .timestamp_seconds < 200)'

# Find all missed shots with high overlap (potential errors)
cat session.json | jq '.shots[] | select(.outcome == "missed" and .max_overlap_percentage > 90)'
```

### Analyze Outcome Reasons
```bash
# Count by outcome reason
cat session.json | jq '[.shots[].outcome_reason] | group_by(.) | map({reason: .[0], count: length})'

# Find fast swoosh detections
cat session.json | jq '.shots[] | select(.outcome_reason | contains("fast_swoosh"))'

# Find rim bounce detections
cat session.json | jq '.shots[] | select(.is_rim_bounce == true)'
```

---

## 🎯 Accuracy Analysis

### View Accuracy Results
```bash
# Session summary
cat results/[UUID]/session_summary.json

# Detailed accuracy
cat results/[UUID]/accuracy_analysis.json | jq '.accuracy_analysis'

# Matched incorrect (misclassifications)
cat results/[UUID]/accuracy_analysis.json | jq '.detailed_analysis.matched_incorrect[0:5]'

# Unmatched ground truth (missed detections)
cat results/[UUID]/accuracy_analysis.json | jq '.detailed_analysis.unmatched_ground_truth[0:5]'
```

### Compare Multiple Validation Runs
```bash
# List all validation results
ls -lth results/

# Quick comparison of outcomes
for dir in results/*/; do
    echo "=== $(basename $dir) ==="
    cat "$dir/accuracy_analysis.json" | jq '{
        detection_total: .detection_summary.total_shots,
        ground_truth_total: .ground_truth_summary.total_shots,
        outcome_accuracy: .timestamp_matching.outcome_accuracy
    }'
done
```

---

## 🏀 Batch Processing

### Process Multiple Videos
```bash
python main.py --action batch \
    --video_dir videos/ \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --output_dir processed/
```

### Batch Validate
```bash
# Create a script for multiple videos
for video in game*.mp4; do
    echo "Processing $video..."
    python main.py --action video \
        --video_path "$video" \
        --model runs/detect/basketball_yolo11n3/weights/best.pt \
        --validate_accuracy \
        --game_id a3c9c041-6762-450a-8444-413767bb6428 \
        --angle LEFT
done
```

---

## 🔧 Model Selection

### Use Different Models
```bash
# YOLOv11 nano (fastest)
--model runs/detect/basketball_yolo11n/weights/best.pt

# YOLOv11 nano v3 (current default)
--model runs/detect/basketball_yolo11n3/weights/best.pt

# YOLOv11 small (more accurate, slower)
--model runs/detect/basketball_yolo11s/weights/best.pt

# Pre-trained YOLO11n (baseline)
--model yolo11n.pt
```

---

## 📈 Performance Testing

### Quick Test (First 2 Minutes)
```bash
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 0 \
    --end_time 120
```

### Test Problem Timestamps
```bash
# Based on accuracy analysis, test specific problem areas
# Example: Shots around 71s, 378s, 550s

python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 70 \
    --end_time 75

python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 375 \
    --end_time 381
```

### Benchmark Processing Speed
```bash
# Time the processing
time python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time 0 \
    --end_time 60
```

---

## 🎬 Live Detection

### Live Camera Feed
```bash
# Default camera (index 0)
python main.py --action live \
    --model runs/detect/basketball_yolo11n3/weights/best.pt

# Specific camera
python main.py --action live \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --camera 1

# Without saving session
python main.py --action live \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --no_save
```

**Controls:**
- Press `q` to quit
- Press `s` to save current session

---

## 🔍 Debug & Troubleshooting

### Check Dependencies
```bash
# Verify installations
pip list | grep -E "ultralytics|opencv|scipy|filterpy|torch"

# Install missing dependencies
pip install scipy filterpy

# Reinstall all
pip install -r requirements.txt
```

### Verify Enhanced Algorithm
```bash
# Check if enhanced algorithm is active
cat game3_nearleft_session.json | jq '.shots[0].detection_method'
# Should show: "enhanced_multi_factor_v2"

# Check for enhanced fields
cat game3_nearleft_session.json | jq '.shots[0] | keys'
# Should include: decision_confidence, entry_angle, rim_bounce_confidence, etc.
```

### Clear Cache
```bash
# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Clear YOLO cache
rm -rf runs/detect/*/cache
```

---

## 📝 Export & Reporting

### Export Results to CSV
```bash
# Convert JSON to CSV for analysis
cat session.json | jq -r '.shots[] | [
    .timestamp_seconds,
    .outcome,
    .outcome_reason,
    .decision_confidence,
    .max_overlap_percentage,
    .frames_with_100_percent,
    .entry_angle,
    .rim_bounce_confidence
] | @csv' > shots.csv
```

### Generate Summary Report
```bash
# Create comprehensive summary
cat session.json | jq '{
    total_shots: .statistics.total_shots,
    made: .statistics.made_shots,
    missed: .statistics.missed_shots,
    shooting_pct: (.statistics.made_shots / .statistics.total_shots * 100),
    avg_confidence: ([.shots[].decision_confidence] | add / length),
    rim_bounces: ([.shots[] | select(.is_rim_bounce == true)] | length)
}' > summary.json
```

### Compare Validation Folders
```bash
# Quick comparison script
echo "UUID,Detection Total,Ground Truth,Outcome Accuracy"
for dir in results/*/; do
    uuid=$(basename "$dir")
    detection=$(cat "$dir/accuracy_analysis.json" | jq -r '.detection_summary.total_shots')
    ground_truth=$(cat "$dir/accuracy_analysis.json" | jq -r '.ground_truth_summary.total_shots')
    accuracy=$(cat "$dir/accuracy_analysis.json" | jq -r '.timestamp_matching.outcome_accuracy')
    echo "$uuid,$detection,$ground_truth,$accuracy"
done
```

---

## 🎯 Common Workflows

### Complete Validation Workflow
```bash
# 1. Process video with validation
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle LEFT

# 2. Check results
cat results/[LATEST_UUID]/session_summary.json | jq '.quick_summary'

# 3. View detailed accuracy
cat results/[LATEST_UUID]/accuracy_analysis.json | jq '.accuracy_analysis'

# 4. Find misclassifications
cat results/[LATEST_UUID]/accuracy_analysis.json | jq '.detailed_analysis.matched_incorrect[0:10]'
```

### Compare Algorithm Versions
```bash
# 1. Save old session as backup
cp input/game3_nearleft_session.json input/game3_nearleft_session_old.json

# 2. Run with new algorithm
python main.py --action video \
    --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt

# 3. Compare results
python test_enhanced_detection.py \
    --old input/game3_nearleft_session_old.json \
    --new input/game3_nearleft_session.json \
    --analyze

# 4. Check improvement
diff <(cat input/game3_nearleft_session_old.json | jq '.statistics') \
     <(cat input/game3_nearleft_session.json | jq '.statistics')
```

### Iterative Testing
```bash
# Test → Analyze → Adjust → Repeat
# 1. Quick test on subset
python main.py --action video --video_path input/game3_nearleft.mp4 \
    --start_time 0 --end_time 300 --model runs/detect/basketball_yolo11n3/weights/best.pt

# 2. Check accuracy
cat input/game3_nearleft_session.json | jq '[.shots[].outcome] | group_by(.) | map({outcome: .[0], count: length})'

# 3. Identify issues
cat input/game3_nearleft_session.json | jq '.shots[] | select(.outcome_reason | contains("ambiguous"))'

# 4. Adjust thresholds in shot_detection.py if needed

# 5. Retest full video
python main.py --action video --video_path input/game3_nearleft.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt --validate_accuracy \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 --angle LEFT
```

---

## 📊 Useful One-Liners

```bash
# Find latest validation result
ls -t results/ | head -1

# Count total shots detected
cat session.json | jq '.statistics.total_shots'

# Get shooting percentage
cat session.json | jq '(.statistics.made_shots / .statistics.total_shots * 100)'

# Find high-confidence made shots
cat session.json | jq '.shots[] | select(.outcome == "made" and .decision_confidence > 0.8)'

# Find uncertain decisions
cat session.json | jq '.shots[] | select(.decision_confidence < 0.65)'

# Extract all timestamps
cat session.json | jq -r '.shots[].timestamp_seconds'

# Find shots with specific outcome reason
cat session.json | jq '.shots[] | select(.outcome_reason == "rim_bounce_detected")'

# Get average entry angle for made vs missed
cat session.json | jq '[.shots[] | select(.outcome == "made" and .entry_angle != null) | .entry_angle] | add / length'

# Compare two UUID results quickly
diff <(cat results/UUID1/session_summary.json | jq) <(cat results/UUID2/session_summary.json | jq)
```

---

## 🚀 Quick Reference

### Most Common Commands

**Test specific time range:**
```bash
python main.py --action video --video_path input/VIDEO.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --start_time START --end_time END
```

**Validate with ground truth:**
```bash
python main.py --action video --video_path input/VIDEO.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --game_id GAME_ID --validate_accuracy --angle ANGLE
```

**Compare two results:**
```bash
python test_enhanced_detection.py --old OLD.json --new NEW.json --analyze
```

**Check latest result:**
```bash
cat results/$(ls -t results/ | head -1)/session_summary.json | jq
```

---

## 📞 Quick Help

```bash
# Main script help
python main.py --help

# Validation help
python accuracy_validator.py --help

# Test script help
python test_enhanced_detection.py --help
```

---

**Last Updated:** 2025-10-31  
**Version:** Enhanced Algorithm V2

