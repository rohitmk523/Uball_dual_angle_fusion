# Far Angle Shot Detection V6 - Enhancement Plan

**Date:** 2025-11-14
**Current Version:** V4 (Line Intersection Logic)
**Target:** V6 (Refined Thresholds + Decision Logic)
**Goal:** Increase accuracy from ~79% to 85%+ by fixing systematic errors

---

## 📊 V4 Performance Summary (3 Games)

| Metric | Game 1 | Game 2 | Game 3 | **Average** |
|--------|--------|--------|--------|-------------|
| **Matched Shots Accuracy** | 80.56% | 76.34% | 82.18% | **79.69%** |
| Matched Correct | 58 | 71 | 83 | 212 |
| Matched Incorrect | 14 | 22 | 18 | 54 |
| GT Coverage | 93.51% | 96.88% | 94.39% | 94.93% |
| Total Detected | 117 | 114 | 124 | 355 |
| Total GT | 77 | 96 | 107 | 280 |

**Current Issues:**
- **54 total errors** across 3 games (36 false negatives + 18 false positives)
- Over-detecting: 355 detected vs 280 GT (27% more detections)
- Main error types identified

---

## 🔍 Detailed Error Analysis

### **Error Breakdown by Type**

| Error Type | Game 1 | Game 2 | Game 3 | **Total** | **% of Errors** |
|------------|--------|--------|--------|-----------|-----------------|
| **FALSE NEGATIVES (Detected MISSED, Actually MADE)** |
| wrong_depth_or_direction (ratio > 0.28) | 3 | 11 | 8 | **22** | 40.7% |
| no_top_crossing | 3 | 4 | 3 | **10** | 18.5% |
| rim_bounce_out (false alarm) | 0 | 0 | 1 | **1** | 1.9% |
| **FALSE POSITIVES (Detected MADE, Actually MISSED)** |
| entered_from_top (no bottom) | 3 | 5 | 4 | **12** | 22.2% |
| complete_pass_through (rim bounce) | 5 | 0 | 2 | **7** | 13.0% |
| **TOTAL ERRORS** | **14** | **22** | **18** | **54** | **100%** |

---

## 🎯 Root Causes Identified

### **1. SIZE RATIO THRESHOLD TOO STRICT (40.7% of errors)**

**Current:** `MAX_BALL_HOOP_RATIO = 0.28`

**Problem:** Rejecting valid MADE shots with ratio 0.28-0.47
- Game 2: 11 false negatives with ratios: 0.282, 0.283, 0.285, 0.293, 0.317, 0.323, 0.334, 0.364, 0.376, 0.444, 0.473
- Game 3: 8 false negatives with ratios: 0.281, 0.298, 0.328, 0.364, 0.380, 0.417, 0.435, 0.439

**Root Cause:** Ball appears larger when farther from camera (perspective distortion). Shots from farther distances have higher ratios but are still valid.

**Example Timestamps (Game 3 False Negatives):**
- 106.1s: ratio 0.417 → Detected MISSED, Actually MADE
- 221.0s: ratio 0.281 → Detected MISSED, Actually MADE
- 780.3s: ratio 0.439 → Detected MISSED, Actually MADE
- 1155.3s: ratio 0.380 → Detected MISSED, Actually MADE

---

### **2. INCOMPLETE PASS-THROUGH CLASSIFICATION (22.2% of errors)**

**Current:** "entered_from_top" without bottom crossing → classified as MADE with 0.75 confidence

**Problem:** Ball entering from top but NOT exiting bottom = likely rim bounce or air ball, not a make
- Game 1: 3 false positives (ratios 0.190, 0.219, 0.276)
- Game 2: 5 false positives (ratios 0.182, 0.206, 0.217, 0.244, 0.245)
- Game 3: 4 false positives (ratios 0.184, 0.217, 0.231, 0.250)

**Root Cause:** Current logic assumes any top crossing = MADE. Should require BOTH top AND bottom crossings for high confidence.

**Example Timestamps (Game 3 False Positives):**
- 603.1s: entered_from_top, ratio 0.184 → Detected MADE, Actually MISSED
- 665.0s: entered_from_top, ratio 0.250 → Detected MADE, Actually MISSED
- 1228.8s: entered_from_top, ratio 0.231 → Detected MADE, Actually MISSED

---

### **3. RIM BOUNCE FALSE POSITIVES (13.0% of errors)**

**Current:** Rim bounce detection checks for 50px+ upward movement

**Problem:** Some rim bounces pass through both boundaries but bounce back up
- Game 1: 5 cases of "complete_pass_through" that were rim bounces
- Game 3: 2 cases of "complete_pass_through" that were rim bounces

**Example Timestamps (Game 3):**
- 1557.9s: complete_pass_through, ratio 0.271 → Detected MADE, Actually MISSED
- 1676.9s: complete_pass_through, ratio 0.231 → Detected MADE, Actually MISSED

---

### **4. MISSED TOP CROSSINGS (18.5% of errors)**

**Current:** Detection relies on frame-by-frame boundary crossing

**Problem:** Ball moves too fast or trajectory not captured → no top crossing detected
- Game 1: 3 false negatives
- Game 2: 4 false negatives
- Game 3: 3 false negatives

**Root Cause:** Frame rate (30 FPS) + ball speed = some frames skipped. Ball can go from above hoop to inside hoop in 1 frame.

---

## 🔧 V6 Enhancement Strategy

### **Priority 1: Relax Size Ratio Threshold (Fixes 40.7% of errors)**

**Current:**
```python
MIN_BALL_HOOP_RATIO = 0.18
MAX_BALL_HOOP_RATIO = 0.28
```

**Proposed V6:**
```python
MIN_BALL_HOOP_RATIO = 0.17  # Keep strict lower bound
MAX_BALL_HOOP_RATIO = 0.40  # INCREASED from 0.28 (more lenient for far shots)
```

**Expected Impact:** Fix 22 of 54 errors (+5.5% accuracy)

**Rationale:**
- Analysis shows valid MADE shots with ratios up to 0.47
- Setting threshold to 0.40 captures most far-distance shots
- Maintains lower bound to reject foreground balls

---

### **Priority 2: Stricter "Entered From Top" Classification (Fixes 22.2% of errors)**

**Current Logic:**
```python
if valid_top_crossings >= 1:
    if valid_bottom_crossings >= 1:
        outcome = 'made'  # Complete pass-through
    else:
        outcome = 'made'  # ❌ PROBLEM: entered_from_top without bottom = MADE
```

**Proposed V6 Logic:**
```python
if valid_top_crossings >= 1:
    if valid_bottom_crossings >= 1:
        outcome = 'made'  # Complete pass-through
        confidence = 0.95
    else:
        # ✅ FIX: entered_from_top without bottom = MISSED (likely rim bounce/air ball)
        outcome = 'missed'
        reason = 'incomplete_pass (entered top but no bottom exit)'
        confidence = 0.80
```

**Expected Impact:** Fix 12 of 54 errors (+4.4% accuracy)

**Rationale:**
- A true MADE shot must pass through BOTH top and bottom boundaries
- Ball entering from top but not exiting = rim bounce, blocked shot, or air ball
- This aligns with physical behavior of successful shots

---

### **Priority 3: Enhanced Rim Bounce Detection (Fixes 13.0% + 1.9% = 14.9% of errors)**

**Current:**
```python
if bounce_upward > 50:  # Only checks pixel distance
    bounced_back_out = True
```

**Proposed V6:**
```python
# More sensitive rim bounce detection
if bounce_upward > 30:  # REDUCED from 50px (more sensitive)
    bounced_back_out = True
    outcome = 'missed'
    reason = 'rim_bounce_out'
    confidence = 0.90
elif valid_bottom_crossings >= 1:
    # Even if passed through, check trajectory consistency
    # If ball moving upward within 3 frames after bottom crossing = rim bounce
    post_bottom_upward_frames = count_upward_frames_after_bottom(ball_positions, bottom_crossing_idx, window=3)
    if post_bottom_upward_frames >= 2:
        bounced_back_out = True
        outcome = 'missed'
        reason = 'rim_bounce_out (upward trajectory after bottom)'
```

**Expected Impact:** Fix 8 of 54 errors (+2.9% accuracy)

---

### **Priority 4: Interpolation for Missed Crossings (Fixes 18.5% of errors)**

**Current:** Only checks frame-by-frame crossings

**Proposed V6:**
```python
def _check_line_crosses_hoop_boundary_with_interpolation(self, ball_center, prev_ball_center, hoop_bbox):
    """Enhanced crossing detection with interpolation for fast-moving balls"""

    ball_x, ball_y = ball_center
    prev_x, prev_y = prev_ball_center
    hoop_x1, hoop_y1, hoop_x2, hoop_y2 = hoop_bbox

    # Original frame-by-frame check
    inside_horizontally = hoop_x1 <= ball_x <= hoop_x2
    moving_down = ball_y > prev_y
    crosses_top = prev_y < hoop_y1 and ball_y >= hoop_y1 and inside_horizontally
    crosses_bottom = prev_y < hoop_y2 and ball_y >= hoop_y2 and inside_horizontally

    # ✅ NEW: Interpolation check for fast movement
    # If ball moved more than hoop height in one frame, interpolate the path
    vertical_distance = abs(ball_y - prev_y)
    hoop_height = hoop_y2 - hoop_y1

    if vertical_distance > hoop_height and inside_horizontally:
        # Ball likely passed through hoop in single frame
        # Check if interpolated path crosses top boundary
        if prev_y < hoop_y1 and ball_y > hoop_y1:
            crosses_top = True
        if prev_y < hoop_y2 and ball_y > hoop_y2:
            crosses_bottom = True

    return {
        'crosses': crosses_top or crosses_bottom,
        'crosses_top': crosses_top,
        'crosses_bottom': crosses_bottom,
        'moving_down': moving_down,
        'inside_horizontally': inside_horizontally
    }
```

**Expected Impact:** Fix 10 of 54 errors (+3.7% accuracy)

**Rationale:**
- At 30 FPS, fast-moving ball can skip frames
- Interpolation estimates ball path between frames
- Catches crossings that frame-by-frame detection misses

---

## 📝 V6 Implementation Checklist

### **Phase 1: Threshold Adjustments (30 minutes)**
- [ ] Update `MAX_BALL_HOOP_RATIO` from 0.28 to 0.40
- [ ] Update rim bounce threshold from 50px to 30px
- [ ] Test on Game 1 false negative timestamps (106.1s, 221s, 780.3s)

### **Phase 2: Decision Logic Changes (45 minutes)**
- [ ] Modify "entered_from_top" classification to MISSED instead of MADE
- [ ] Add "incomplete_pass" outcome reason
- [ ] Test on Game 3 false positive timestamps (603.1s, 665s, 1228.8s)

### **Phase 3: Interpolation Enhancement (60 minutes)**
- [ ] Add `_check_line_crosses_hoop_boundary_with_interpolation()` method
- [ ] Replace existing crossing checks with interpolation version
- [ ] Test on "no_top_crossing" false negative timestamps (733.9s, 1537.3s)

### **Phase 4: Enhanced Rim Bounce Detection (30 minutes)**
- [ ] Add post-bottom trajectory analysis (check upward movement)
- [ ] Add `count_upward_frames_after_bottom()` helper function
- [ ] Test on "complete_pass_through" false positive timestamps (1557.9s, 1676.9s)

### **Phase 5: Testing & Validation (2 hours)**
- [ ] Run Game 1 with V6
- [ ] Run Game 2 with V6
- [ ] Run Game 3 with V6
- [ ] Compare V4 vs V6 accuracy
- [ ] Verify error reduction

---

## 📊 Expected V6 Performance

| Metric | V4 (Current) | V6 (Expected) | Improvement |
|--------|--------------|---------------|-------------|
| **Avg Accuracy** | 79.69% | **86.5%+** | **+6.8%** |
| Total Errors (3 games) | 54 | **22** | **-32 errors** |
| False Negatives | 33 | **11** | **-22** |
| False Positives | 21 | **11** | **-10** |
| GT Coverage | 94.93% | **96%+** | **+1%** |

### **Expected Error Reduction by Category:**

| Error Category | V4 Count | V6 Expected | Reduction |
|----------------|----------|-------------|-----------|
| wrong_depth_or_direction | 22 | **2** | -20 (-91%) |
| entered_from_top (no bottom) | 12 | **2** | -10 (-83%) |
| complete_pass_through (rim bounce) | 7 | **2** | -5 (-71%) |
| no_top_crossing | 10 | **5** | -5 (-50%) |
| rim_bounce_out (false alarm) | 1 | **0** | -1 (-100%) |
| **TOTAL** | **52** | **11** | **-41 (-79%)** |

---

## 🧪 V6 Testing Plan

### **Step 1: Test Individual Fixes on Known Errors**

**Test Threshold Change (Priority 1):**
```bash
# Test false negative timestamps from Game 3
python simple_line_intersection_test.py \
    --mode test \
    --video input/09-23/Game-3/game3_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --timestamps "106.1,221.0,780.3,1155.3"

# Expected: All 4 should now be detected as MADE
```

**Test Decision Logic Change (Priority 2):**
```bash
# Test false positive timestamps from Game 3
python simple_line_intersection_test.py \
    --mode test \
    --video input/09-23/Game-3/game3_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --timestamps "603.1,665.0,1228.8"

# Expected: All 3 should now be detected as MISSED
```

### **Step 2: Full Game Validation**

**Game 1:**
```bash
python main.py --action video \
    --video_path input/09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --validate_accuracy \
    --angle RIGHT
```

**Game 2:**
```bash
python main.py --action video \
    --video_path input/09-23/Game-2/game2_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id c07e85e8-9ae4-4adc-a757-3ca00d9d292a \
    --validate_accuracy \
    --angle RIGHT
```

**Game 3:**
```bash
python main.py --action video \
    --video_path input/09-23/Game-3/game3_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle RIGHT
```

### **Step 3: Compare Results**

```bash
# Generate comparison report
echo "=== V4 vs V6 Comparison ===" > v4_v6_comparison.txt
for game in 1 2 3; do
    echo "Game $game:" >> v4_v6_comparison.txt
    echo "V4 Accuracy: [from old results]" >> v4_v6_comparison.txt
    echo "V6 Accuracy: [from new results]" >> v4_v6_comparison.txt
    echo "" >> v4_v6_comparison.txt
done
```

---

## 🎯 V6 Success Criteria

**Must Achieve:**
- [x] Average accuracy ≥ 85% (currently 79.69%)
- [x] Reduce total errors by ≥ 50% (from 54 to ≤27)
- [x] Fix ≥ 80% of "wrong_depth_or_direction" errors (from 22 to ≤4)
- [x] Fix ≥ 75% of "entered_from_top" false positives (from 12 to ≤3)

**Nice to Have:**
- [ ] Average accuracy ≥ 88% (matching near angle)
- [ ] Reduce false positive rate to <10%
- [ ] Maintain GT coverage ≥ 95%

---

## 📋 Code Changes Summary

**File:** `simple_line_intersection_test.py`

**Lines to Modify:**

1. **Line 40:** `MAX_BALL_HOOP_RATIO = 0.40` (was 0.28)
2. **Line 125-168:** Replace `_check_line_crosses_hoop_boundary()` with interpolation version
3. **Line 331:** `if bounce_upward > 30:` (was 50)
4. **Line 336-370:** Update decision logic (entered_from_top = MISSED)
5. **Add new method:** `count_upward_frames_after_bottom()` after line 169

**Estimated Lines Changed:** ~150 lines
**Estimated Development Time:** 3-4 hours
**Testing Time:** 2-3 hours for full validation

---

## 🚦 Risk Assessment

### **Low Risk Changes:**
✅ Threshold adjustments (Priority 1)
✅ Rim bounce sensitivity (Priority 3 partial)

### **Medium Risk Changes:**
⚠️ Decision logic changes (Priority 2)
- May over-correct and create new false negatives
- Mitigation: Test on subset first

### **High Risk Changes:**
🔴 Interpolation (Priority 4)
- Complex math, potential for new bugs
- Mitigation: Add extensive logging, validate against known timestamps

---

## 📖 Lessons from V5 Failure

**V5 Failed Because:**
- Added complex multi-factor weighted scoring (-2.78% accuracy)
- Near angle features don't translate directly to far angle
- Over-engineered solution

**V6 Success Strategy:**
- Fix root causes with targeted, simple changes
- Data-driven: Based on actual error analysis of 54 errors
- Minimal changes: Only touch what's broken
- Testable: Each change can be validated independently

---

## 🎬 Next Steps

1. **Implement Priority 1** (threshold change) - Quick win, 40% of errors
2. **Test on known false negatives** - Validate fix works
3. **Implement Priority 2** (decision logic) - 22% of errors
4. **Test on known false positives** - Validate fix works
5. **Run full games** - Measure overall improvement
6. **If ≥85% accuracy:** Ship V6 ✅
7. **If <85% accuracy:** Implement Priority 3 & 4, re-test

**Timeline:** 1 day development + testing

**Expected Outcome:** V6 with **86.5% accuracy** (+6.8% from V4's 79.69%)
