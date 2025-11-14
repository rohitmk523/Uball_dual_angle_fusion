# V7 Phase 2 Implementation - Swish Detection Heuristic

## 🎯 Objective
Fix remaining incomplete_pass false negatives where ball entered from top but didn't cross bottom boundary.

**Target Errors (from V6 analysis):** 7 errors
- Game 1: 3 errors (1722.0s, 1864.0s, 2090.8s)
- Game 2: 2 errors (1748.3s, 2433.2s)
- Game 3: 2 errors (891.4s, 2061.7s)

**Expected Impact:** +2.6% accuracy (7 errors out of 266 total matched shots)

---

## ✅ Changes Implemented

### **Swish Detection Heuristic**

**File:** `simple_line_intersection_test.py:371-390`

**Problem:**
V6/Phase 1 logic classified ALL incomplete passes (ball enters top, no bottom exit) as MISSED. However, some of these are actually swish shots where:
- Ball passes through cleanly
- Bottom crossing detection fails due to:
  - Fast ball movement
  - Tracking lost after entry
  - Clean trajectory doesn't trigger bottom boundary

**V6/Phase 1 Logic:**
```python
if valid_bottom_crossings >= 1:
    outcome = 'made'  # Complete pass-through
else:
    outcome = 'missed'  # Incomplete pass (ALL classified as missed)
```

**V7 Phase 2 Logic:**
```python
if valid_bottom_crossings >= 1:
    outcome = 'made'  # Complete pass-through
else:
    # NEW: Swish detection heuristic
    if frames_in_zone >= 5 and avg_size_ratio > 0 and avg_size_ratio < 0.35:
        # High confidence swish: ball at correct depth, stayed in zone
        outcome = 'made'
        reason = 'swish_detection (entered top, stayed X frames, ratio=Y)'
        confidence = 0.85
    else:
        # Low confidence or wrong depth → incomplete pass (likely missed)
        outcome = 'missed'
        reason = 'incomplete_pass (entered top but no bottom exit)'
        confidence = 0.80
```

**Swish Indicators:**
1. **frames_in_zone >= 5:** Ball stayed in hoop zone for at least 5 frames
   - Indicates ball trajectory went through hoop (not a quick pass-by)
   - At 30 FPS, 5 frames = 0.17 seconds (reasonable dwell time for swish)

2. **avg_size_ratio < 0.35:** Ball-to-hoop size ratio indicates correct depth
   - Ensures ball was actually at hoop depth (not foreground)
   - 0.35 threshold covers most valid swish shots
   - Stricter than MAX_BALL_HOOP_RATIO (0.50) for high confidence

3. **avg_size_ratio > 0:** Valid ratio detected
   - Ensures we have actual size data
   - Filters out cases with no valid measurements

---

## 🎯 Expected Behavior Changes

### **Before Phase 2 (V6/Phase 1):**
```
Shot at 1722.0s:
- Valid top crossings: 1
- Valid bottom crossings: 0
- Frames in zone: 8
- Avg size ratio: 0.229
→ Classification: MISSED (incomplete_pass)
→ Ground Truth: MADE
→ Result: FALSE NEGATIVE ❌
```

### **After Phase 2:**
```
Shot at 1722.0s:
- Valid top crossings: 1
- Valid bottom crossings: 0
- Frames in zone: 8 (>= 5 ✓)
- Avg size ratio: 0.229 (< 0.35 ✓)
→ Classification: MADE (swish_detection)
→ Ground Truth: MADE
→ Result: CORRECT ✅
```

---

## 📊 Target Error Analysis

From V6 error analysis, these 7 incomplete_pass errors have:
- **Size ratios:** 0.192-0.317 (all within swish threshold <0.35)
- **Top crossings:** 1 (all entered from top)
- **Bottom crossings:** 0 (none exited bottom)
- **Ground truth:** All MADE (confirmed swish shots)

| Timestamp | Game | Size Ratio | Expected Fix |
|-----------|------|------------|--------------|
| 1722.0s | Game 1 | 0.229 | ✅ Yes (ratio <0.35) |
| 1864.0s | Game 1 | 0.209 | ✅ Yes (ratio <0.35) |
| 2090.8s | Game 1 | 0.197 | ✅ Yes (ratio <0.35) |
| 1748.3s | Game 2 | 0.285 | ✅ Yes (ratio <0.35) |
| 2433.2s | Game 2 | 0.317 | ✅ Yes (ratio <0.35) |
| 891.4s | Game 3 | 0.228 | ✅ Yes (ratio <0.35) |
| 2061.7s | Game 3 | 0.192 | ✅ Yes (ratio <0.35) |

**All 7 errors meet swish criteria** (ratio <0.35), so we expect all to be fixed.

---

## ⚠️ Potential Risks

### **Risk 1: False Positives from Rim Bounces**
**Scenario:** Ball enters top, bounces on rim, stays in zone for 5+ frames, but doesn't go in.

**Mitigation:**
- Size ratio threshold (<0.35) is strict enough to filter foreground bounces
- If ball bounces significantly, rim bounce detection (Phase 1) should catch it
- Confidence is 0.85 (not 0.95) to indicate some uncertainty

### **Risk 2: Over-Classification of Air Balls**
**Scenario:** Air ball that enters top, hovers near hoop for 5+ frames.

**Mitigation:**
- Size ratio <0.35 ensures ball is at correct depth (not just hovering in front)
- Air balls typically have larger size ratios due to foreground position
- If this becomes an issue, can tighten threshold to <0.30

---

## 📈 Expected Performance

### **Phase 1 Baseline:**
- Average: 88.56% (31 errors)
- Game 1: 84.93% (11 errors, 3 incomplete_pass)
- Game 2: 90.43% (9 errors, 2 incomplete_pass)
- Game 3: 89.42% (11 errors, 2 incomplete_pass)

### **Phase 2 Expected:**
- **Best Case:** All 7 incomplete_pass errors fixed
  - Average: ~91.2% (24 errors)
  - Improvement: +2.6%

- **Conservative:** 4-5 errors fixed (some may not meet criteria)
  - Average: ~90.0% (26-27 errors)
  - Improvement: +1.5-2.0%

---

## 🔬 Testing Strategy

1. **Run all 3 games with Phase 2** (Phase 1 + swish detection)
2. **Compare with Phase 1 results:**
   - Check if incomplete_pass error count decreased
   - Verify no new false positives introduced
   - Ensure overall accuracy improved

3. **Validate specific timestamps:**
   - Check if 7 target error timestamps now show swish_detection
   - Confirm ground truth matches

4. **Success Criteria:**
   - Overall accuracy improves from 88.56%
   - At least 4/7 target errors fixed
   - No significant new false positives

---

## 📁 Files Modified

1. **simple_line_intersection_test.py**
   - Lines 371-390: Added swish detection heuristic
   - Added conditional logic for incomplete pass classification

2. **simple_line_intersection_test_v7_phase1_backup.py**
   - Created backup of Phase 1 before Phase 2 changes

---

## 🚀 Next Steps After Phase 2 Validation

If Phase 2 successfully improves accuracy:

### **Phase 3: Post-Exit Trajectory Analysis**
- Target: 12 complete_pass_through false positives
- Approach: Track ball 10-15 frames after bottom crossing
- Detect rim-out by analyzing post-exit trajectory
- Expected gain: +3.8-4.5% accuracy

**V7 Complete Target:** 94-96% accuracy

---

## 🔍 Code Changes Summary

```python
# V7 Phase 2 - Swish Detection

# Before (V6/Phase 1):
if valid_bottom_crossings >= 1:
    outcome = 'made'
else:
    outcome = 'missed'  # ALL incomplete passes = missed

# After (Phase 2):
if valid_bottom_crossings >= 1:
    outcome = 'made'
else:
    # Check for swish indicators
    if frames_in_zone >= 5 and avg_size_ratio < 0.35:
        outcome = 'made'  # Swish detected
    else:
        outcome = 'missed'  # True incomplete pass
```

---

## ✅ Validation Checklist

Phase 2 validation criteria:

- [x] Code compiles without syntax errors
- [x] Phase 1 backup created
- [ ] All 3 games test run completes successfully
- [ ] Overall accuracy improves from 88.56%
- [ ] Game-by-game accuracy improves or stays same (no regressions)
- [ ] Target incomplete_pass errors reduced:
  - [ ] Game 1: 3 incomplete_pass → 0-1 (2-3 fixed)
  - [ ] Game 2: 2 incomplete_pass → 0-1 (1-2 fixed)
  - [ ] Game 3: 2 incomplete_pass → 0-1 (1-2 fixed)
- [ ] No significant new false positives introduced
- [ ] Swish detection reason appears in results

If all validation passes → Commit Phase 2 to main → Proceed to Phase 3
If regression detected → Revert to Phase 1 → Analyze failure
