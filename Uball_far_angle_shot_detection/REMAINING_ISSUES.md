# Remaining Far Angle Classification Issues

**Date**: November 5, 2025
**Status**: Documented for future improvement after dual angle fusion is working
**Total Issues**: 19 (12 rim bounce false positives + 7 swish false positives)

---

## Overview

Far angle detection has achieved **65.5% success rate** on its two critical advantages (rim bounces and swishes). This document lists the remaining 19 incorrect classifications that will be addressed later to improve individual far angle accuracy.

### Current Performance
- **Rim Bounce Detection**: 22 correct, 12 incorrect (64.7% success rate)
- **Clean Swish Detection**: 14 correct, 7 incorrect (66.7% success rate)
- **Overall Critical Advantages**: 36 correct, 19 incorrect (65.5% success rate)

---

## 1. Rim Bounce False Positives (12 cases)

These shots were **detected as MISSED (rim bounce)** but were **actually MADE**.

### Pattern Analysis
- **Common Issue**: High upward movement (43-325px) in zone
- **Possible Cause**: Ball may have touched rim and bounced up slightly before going in
- **Improvement Ideas**:
  - Check if downward movement after upward is sufficient (ball recovers and goes down through hoop)
  - Add "recovery ratio": if (downward after peak) / (total upward) > threshold → MADE

### Detailed Cases

#### 1. Time: 158s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 26 frames, 149px up, 139px down
- **Reason**: rim_bounce_frames (frames:26, up:149px)
- **Note**: Up/Down nearly equal (1.07 ratio) - may indicate slight rim touch but still made

#### 2. Time: 524s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 47 frames, 43px up, 187px down
- **Reason**: rim_bounce_frames (frames:47, up:43px)
- **Note**: Long duration (47f) but only 43px upward - likely rolled on rim before dropping in

#### 3. Time: 954s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 33 frames, 102px up, 148px down
- **Reason**: rim_bounce_frames (frames:33, up:102px)
- **Note**: Up/Down ratio 0.69 - decent downward recovery

#### 4. Time: 1025s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 89 frames, 325px up, 327px down
- **Reason**: rim_bounce_frames (frames:89, up:325px)
- **Note**: Extremely long duration (89f), nearly equal up/down (0.99 ratio) - major rim contact but eventually made

#### 5. Time: 1212s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 35 frames, 120px up, 175px down
- **Reason**: rim_bounce_frames (frames:35, up:120px)
- **Note**: Up/Down ratio 0.69 - good downward recovery

#### 6. Time: 1642s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 30 frames, 144px up, 145px down
- **Reason**: rim_bounce_frames (frames:30, up:144px)
- **Note**: Nearly equal up/down (0.99 ratio) - borderline case

#### 7. Time: 1767s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 33 frames, 155px up, 141px down
- **Reason**: rim_bounce_frames (frames:33, up:155px)
- **Note**: Up slightly exceeds down (1.10 ratio) - but still went in

#### 8. Time: 1863s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 21 frames, 177px up, 190px down
- **Reason**: rim_bounce_frames (frames:21, up:177px)
- **Note**: Good downward recovery (0.93 ratio) - just at threshold (20f)

#### 9. Time: 2467s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 37 frames, 155px up, 173px down
- **Reason**: rim_bounce_frames (frames:37, up:155px)
- **Note**: Up/Down ratio 0.90 - decent recovery

#### 10. Time: 2491s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 31 frames, 155px up, 148px down
- **Reason**: rim_bounce_frames (frames:31, up:155px)
- **Note**: Nearly equal up/down (1.05 ratio)

#### 11. Time: 2536s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 36 frames, 150px up, 149px down
- **Reason**: rim_bounce_frames (frames:36, up:150px)
- **Note**: Nearly equal up/down (1.01 ratio) - perfect balance but still made

#### 12. Time: 2685s ❌
- **Ground Truth**: MADE
- **Detected**: MISSED (rim bounce)
- **Metrics**: 33 frames, 76px up, 163px down
- **Reason**: rim_bounce_frames (frames:33, up:76px)
- **Note**: Good downward dominance (0.47 ratio) - should have been caught as made

---

## 2. Clean Swish False Positives (7 cases)

These shots were **detected as MADE (clean swish)** but were **actually MISSED**.

### Pattern Analysis
- **Common Issue**: Very short duration (7-26 frames) with perfect or near-perfect consistency
- **Possible Cause**: Ball passed through zone briefly without actually going in hoop
- **Improvement Ideas**:
  - Add minimum frame threshold for swish detection (e.g., >= 10 frames)
  - Require minimum downward movement for swishes (e.g., >= 80px)
  - Check if ball trajectory ends below hoop (confirms ball went through)

### Detailed Cases

#### 1. Time: 221s ❌
- **Ground Truth**: MISSED
- **Detected**: MADE (clean swish)
- **Metrics**: 25 frames, 17px up, cons:0.92
- **Reason**: clean_swish (up:17px, cons:0.92)
- **Note**: At threshold (17px < 20px, 0.92 > 0.85) - borderline case

#### 2. Time: 1006s ❌
- **Ground Truth**: MISSED
- **Detected**: MADE (clean swish)
- **Metrics**: 20 frames, 1px up, cons:0.99
- **Reason**: clean_swish (up:1px, cons:0.99)
- **Note**: Nearly perfect metrics but still missed - may need downward movement check

#### 3. Time: 1056s ❌
- **Ground Truth**: MISSED
- **Detected**: MADE (clean swish)
- **Metrics**: 26 frames, 15px up, cons:0.91
- **Reason**: clean_swish (up:15px, cons:0.91)
- **Note**: Good metrics but missed - needs additional validation

#### 4. Time: 1374s ❌
- **Ground Truth**: MISSED
- **Detected**: MADE (clean swish)
- **Metrics**: 7 frames, 0px up, cons:1.00
- **Reason**: clean_swish (up:0px, cons:1.00)
- **Note**: **Too short** (7 frames) - may need minimum frame requirement (>= 8 or 10)

#### 5. Time: 1752s ❌
- **Ground Truth**: MISSED
- **Detected**: MADE (clean swish)
- **Metrics**: 24 frames, 9px up, cons:0.94
- **Reason**: clean_swish (up:9px, cons:0.94)
- **Note**: Good metrics but missed - needs additional validation

#### 6. Time: 1938s ❌
- **Ground Truth**: MISSED
- **Detected**: MADE (clean swish)
- **Metrics**: 9 frames, 0px up, cons:1.00
- **Reason**: clean_swish (up:0px, cons:1.00)
- **Note**: **Too short** (9 frames) - perfect metrics but insufficient duration

#### 7. Time: 2659s ❌
- **Ground Truth**: MISSED
- **Detected**: MADE (clean swish)
- **Metrics**: 7 frames, 0px up, cons:1.00
- **Reason**: clean_swish (up:0px, cons:1.00)
- **Note**: **Too short** (7 frames) - same issue as 1374s

---

## Improvement Ideas for Next Iteration

### For Rim Bounce False Positives

1. **Recovery Ratio Check**:
   ```python
   # If ball bounces up but then comes back down strongly
   if upward > 35px and downward > upward * 0.8:
       # Ball recovered from bounce - likely MADE
       outcome = 'made'
   ```

2. **Up/Down Balance Check**:
   ```python
   # If up/down nearly equal AND long duration, may have rolled on rim before going in
   if frames >= 30 and 0.95 <= upward/downward <= 1.05:
       # Check other indicators (consistency, final trajectory)
   ```

3. **Duration Threshold Adjustment**:
   - Current: 20 frames triggers rim bounce
   - Consider: Raise to 25 frames for more certainty
   - OR: Use different thresholds based on up/down ratio

### For Swish False Positives

1. **Minimum Frame Requirement**:
   ```python
   # Require at least 10 frames for swish detection
   if upward <= 20 and consistency >= 0.85 and frames >= 10:
       outcome = 'made'
       reason = 'clean_swish'
   ```

2. **Minimum Downward Movement**:
   ```python
   # Require sufficient downward movement to confirm ball went through hoop
   if upward <= 20 and consistency >= 0.85 and downward >= 80:
       outcome = 'made'
       reason = 'clean_swish'
   ```

3. **Final Position Check**:
   - Check if ball's final Y position is below hoop
   - Confirms ball actually went through (not just passed by)

---

## Testing Strategy for Next Iteration

### Test Set
Focus testing on these 19 timestamps:
- **Rim bounces**: 158s, 524s, 954s, 1025s, 1212s, 1642s, 1767s, 1863s, 2467s, 2491s, 2536s, 2685s
- **Swishes**: 221s, 1006s, 1056s, 1374s, 1752s, 1938s, 2659s

### Test Commands
```bash
# Test specific incorrect rim bounce
python main.py --action video \
    --video_path Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 157 --end_time 160

# Test specific incorrect swish
python main.py --action video \
    --video_path Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 1373 --end_time 1376
```

### Success Metrics
- **Target**: Fix at least 10/19 cases (50% improvement)
- **Stretch Goal**: Fix 15/19 cases (79% improvement)
- **Expected Result**:
  - Current: 36/55 correct (65.5%)
  - Target: 46/55 correct (83.6%)
  - Stretch: 51/55 correct (92.7%)

---

## Priority for Improvement

### High Priority (Quick Wins)
1. **Swish minimum frames** (fixes 3/7 swish false positives: 1374s, 1938s, 2659s)
2. **Swish minimum downward** (may fix 2-3 more)

### Medium Priority
3. **Rim bounce recovery ratio** (may fix 4-6 rim bounce false positives)
4. **Duration threshold adjustment** (careful - may affect correct detections)

### Low Priority (Complex)
5. **Final position check** (requires tracking ball after zone exit)
6. **Advanced trajectory analysis** (may require machine learning)

---

## Timeline

- **Current Phase**: Dual angle fusion implementation
- **Next Phase**: Test fusion system on Game-1
- **Later Phase**: Return to these 19 cases and improve individual far angle accuracy
- **Target**: After dual fusion achieves >90% combined accuracy

---

**End of Document** | Last Updated: November 5, 2025
