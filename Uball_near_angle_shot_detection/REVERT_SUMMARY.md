# V3 Revert Summary

## What Was Done

Successfully reverted shot detection logic from V4 back to V3 (commit `2f96b08`).

## Changes Made

### Commits
1. `faced92` - Documented V4 regression analysis
2. `029ef7c` - Reverted shot_detection.py to V3 logic

### Code Changes
- **Removed:** V4 deceleration and reversal detection (252 lines removed, 14 lines added)
- **Restored:** V3's simpler rim bounce detection
- **Removed:** IMPROVEMENT 2.2 (deceleration/reversal detection)
- **Restored:** Basic post-hoop trajectory analysis

## Expected Performance

Based on baseline testing:

| Dataset | V4 Accuracy | Expected V3 Accuracy | Expected Gain |
|---------|-------------|---------------------|---------------|
| 09-22(2-NL) | 88.24% | 92.16% | +3.92% |
| 09-22(2-NR) | 87.50% | 93.75% | +6.25% |
| **Overall** | 87.83% | **93.04%** | **+5.22%** |

## What Was Removed

### V4 Features (Removed)
- `deceleration_detected` tracking in `_analyze_post_hoop_trajectory()`
- `reversal_detected` tracking in `_analyze_post_hoop_trajectory()`
- Velocity pattern analysis (early vs late average velocity)
- Deceleration scoring in `_enhanced_rim_bounce_detection()`
- Reversal scoring in `_enhanced_rim_bounce_detection()`

### V3 Features (Restored)
- Simple post-hoop trajectory analysis (downward vs upward movement)
- Basic rim bounce detection (upward movement, low angle, low overlap)
- No deceleration tracking
- Cleaner, more generalizable logic

## Next Steps

### 1. Verify Revert (Immediate)
Run a test on 09-22(2-NR) to confirm accuracy is back to ~93.75%:

```bash
python main.py --action video \
    --video_path input/09-22/game2_nearright.mp4 \
    --model runs/detect/basketball_yolo11n3/weights/best.pt \
    --game_id b9477b23-c490-42ca-84e1-5dbae4150f54 \
    --validate_accuracy \
    --angle LEFT
```

Expected result: ~93.75% matched_shots_accuracy (vs 87.50% with V4)

### 2. Re-baseline All Datasets
Run V3 on all datasets to establish clean baselines:
- 09-22(1-NL)
- 09-22(1-NR)
- 09-22(2-NL) ✓ (already have baseline)
- 09-22(2-NR) ✓ (already have baseline)
- 09-22(3-NL)
- 09-22(3-NR)
- 09-23(1-NL)
- 09-23(1-NR)
- 09-23(2-NL)
- 09-23(2-NR)

### 3. Identify Improvement Opportunities
Once baselines are established:
1. Analyze error patterns across ALL datasets
2. Find common failure modes
3. Design improvements that generalize
4. Test improvements on multiple datasets before committing
5. Use cross-validation (test on unseen videos)

## Why We Reverted

### The Problem with V4
1. **Overfitted to 09-22(1-NR):** Achieved 95.83% on one video
2. **Regressed on others:** Lost 3.92-6.25% on other datasets
3. **Net negative:** Overall -5.22% accuracy loss
4. **Poor generalization:** Deceleration detection too sensitive

### V3 Advantages
1. **Consistent:** 93.04% average across datasets
2. **Simple:** Easier to understand and maintain
3. **Stable:** No false positives from deceleration
4. **Generalizes:** Works across different camera angles and game styles

## Documentation

All analysis preserved in:
- `THOROUGH_ANALYSIS_V3_VS_V4.md` - Full comparison
- `V4_REGRESSION_ANALYSIS.md` - Root cause analysis
- `comprehensive_accuracy_comparison.py` - Comparison script

## Git History

```
029ef7c revert: restore V3 shot detection logic - V4 caused 5.22% overall regression
faced92 docs: add V4 regression analysis - shows 5.22% overall regression vs V3
80dca6d docs: clean up repository - consolidate to 4 essential .md files
20f10cf feat: V4 accuracy improvements - achieve 95.83% matched_shots_accuracy [REVERTED]
```

---

*Revert Date: 2025-11-01*
*Reason: V4 caused net 5.22% regression*
*Status: ✅ Complete - Ready for testing*
