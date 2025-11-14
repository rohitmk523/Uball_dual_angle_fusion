# Dual-Angle Fusion - Command Reference

Quick reference for common fusion commands. Copy and paste these templates, adjusting paths as needed.

## Command Templates

### 1. Full Pipeline (First Run)
Runs both near and far angle detection, then fuses results.

```bash
python3 dual_angle_fusion.py \
  --near_video input/09-23/Game-1/game1_nearleft.mp4 \
  --far_video input/09-23/Game-1/game1_farright.mp4 \
  --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
  --near_model Uball_near_angle_shot_detection/runs/detect/basketball_yolo11n3/weights/best.pt \
  --far_model Uball_far_angle_shot_detection/runs/detect/basketball_yolo11n2/weights/best.pt \
  --offset_file offsets/09_23_game_1_offsets.json \
  --validate_accuracy \
  --angle RIGHT
```

**Time:** ~90-95 minutes for full game

---

### 2. Fast Mode (Using Existing Results)
Reuse existing single-angle results to experiment with fusion parameters.

```bash
python3 dual_angle_fusion.py \
  --use_existing_near "Uball_near_angle_shot_detection/results/09-23(1-NL)_19952716-2882-401c-9598-6532a9c403cc" \
  --use_existing_far "Uball_far_angle_shot_detection/results/09-23(1-FR)_146de990-89ca-4fef-a013-6569201b92da" \
  --near_video input/09-23/Game-1/game1_nearleft.mp4 \
  --far_video input/09-23/Game-1/game1_farright.mp4 \
  --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
  --near_model Uball_near_angle_shot_detection/runs/detect/basketball_yolo11n3/weights/best.pt \
  --far_model Uball_far_angle_shot_detection/runs/detect/basketball_yolo11n2/weights/best.pt \
  --offset_file offsets/09_23_game_1_offsets.json \
  --validate_accuracy \
  --angle RIGHT
```

**Time:** ~20-25 minutes (video stitching still runs)

---

### 3. Ultra-Fast Mode (Skip Video Output)
Fastest option - only generates JSON analysis, no video output.

```bash
python3 dual_angle_fusion.py \
  --use_existing_near "Uball_near_angle_shot_detection/results/09-23(1-NL)_19952716-2882-401c-9598-6532a9c403cc" \
  --use_existing_far "Uball_far_angle_shot_detection/results/09-23(1-FR)_146de990-89ca-4fef-a013-6569201b92da" \
  --near_video input/09-23/Game-1/game1_nearleft.mp4 \
  --far_video input/09-23/Game-1/game1_farright.mp4 \
  --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
  --near_model Uball_near_angle_shot_detection/runs/detect/basketball_yolo11n3/weights/best.pt \
  --far_model Uball_far_angle_shot_detection/runs/detect/basketball_yolo11n2/weights/best.pt \
  --offset_file offsets/09_23_game_1_offsets.json \
  --validate_accuracy \
  --angle RIGHT \
  --skip_video
```

**Time:** ~5-10 seconds (only fusion logic and JSON generation)

---

### 4. Quick Test (Time Range)
Test on a specific time segment before running full game.

```bash
python3 dual_angle_fusion.py \
  --near_video input/09-23/Game-1/game1_nearleft.mp4 \
  --far_video input/09-23/Game-1/game1_farright.mp4 \
  --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
  --near_model Uball_near_angle_shot_detection/runs/detect/basketball_yolo11n3/weights/best.pt \
  --far_model Uball_far_angle_shot_detection/runs/detect/basketball_yolo11n2/weights/best.pt \
  --offset_file offsets/09_23_game_1_offsets.json \
  --validate_accuracy \
  --angle RIGHT \
  --start_time 0 \
  --end_time 50
```

**Time:** ~2-3 minutes for 50 seconds

---

## Performance Comparison

| Mode | Detection | Video Stitching | Time (Full Game) | Use Case |
|------|-----------|-----------------|------------------|----------|
| **Full Pipeline** | ✅ Run | ✅ Create | ~90-95 min | First-time analysis |
| **Fast Mode** | ❌ Reuse | ✅ Create | ~20-25 min | Experiment with fusion params |
| **Ultra-Fast** | ❌ Reuse | ❌ Skip | ~5-10 sec | Rapid iteration on fusion logic |
| **Quick Test** | ✅ Run (partial) | ✅ Create | ~2-3 min | Validate before full run |

---

## Key Parameters

### Required Arguments
- `--near_video`: Path to near angle video
- `--far_video`: Path to far angle video  
- `--game_id`: UUID for ground truth lookup
- `--near_model`: Near angle YOLO model path
- `--far_model`: Far angle YOLO model path
- `--offset_file`: JSON file with temporal offset

### Optional Flags
- `--validate_accuracy`: Enable accuracy analysis against ground truth
- `--angle`: Filter ground truth by angle (`LEFT` or `RIGHT`)
- `--start_time`: Start time in seconds (for testing)
- `--end_time`: End time in seconds (for testing)
- `--use_existing_near`: Path to existing near results directory
- `--use_existing_far`: Path to existing far results directory
- `--skip_video`: Skip video output (analysis only)

---

## Output Files

All results saved to: `results/MM-DD(gameN-ANGLE)_UUID/`

- `detection_results.json` - Fused shot detections
- `accuracy_analysis.json` - Performance metrics vs ground truth
- `session_summary.json` - Session metadata and quick stats
- `ground_truth.json` - Copy of ground truth data
- `processed_video.mp4` - Side-by-side stitched video (unless `--skip_video`)

---

## Tips

1. **First run**: Use full pipeline to generate baseline results
2. **Iterating**: Use ultra-fast mode (`--use_existing_*` + `--skip_video`) for rapid testing
3. **Validation**: Always include `--validate_accuracy` to compare against ground truth
4. **Time testing**: Use `--start_time`/`--end_time` to test on specific game segments
5. **Video review**: Omit `--skip_video` when you need visual confirmation

---

**Last Updated:** 2025-11-15
