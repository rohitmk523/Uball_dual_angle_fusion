# V7 Phase 1 Implementation - Detection Zone Expansion & Size Ratio Relaxation

## 🎯 Objective
Fix 15 errors from V6 analysis:
- **Priority 4:** 5 wrong_depth errors (size ratio 0.417-0.473 exceeded 0.40 threshold)
- **Priority 1:** 10 no_top_crossing errors (ball never entered from top)

**Expected Impact:** +5.6% accuracy (15 errors out of 266 total matched shots)

---

## ✅ Changes Implemented

### **1. Priority 4: Increased MAX_BALL_HOOP_RATIO**

**File:** `simple_line_intersection_test.py:40`

**Change:**
```python
# V6
MAX_BALL_HOOP_RATIO = 0.40

# V7 Phase 1
MAX_BALL_HOOP_RATIO = 0.50  # Covers ratios up to 0.473
```

**Rationale:**
- V6 analysis showed 5 false negatives with size ratios 0.417-0.473
- All were confirmed made shots (ground truth)
- Perspective distortion at certain camera angles causes larger ratios
- Increasing to 0.50 accommodates all observed valid shots

**Target Errors (5):**
- Game 2 @ 87.5s: ratio=0.444
- Game 2 @ 623.6s: ratio=0.473
- Game 3 @ 105.5s: ratio=0.417
- Game 3 @ 780.9s: ratio=0.439
- Game 3 @ 2984.4s: ratio=0.435

---

### **2. Priority 1: Expanded Vertical Detection Zone**

**File:** `simple_line_intersection_test.py:34`

**Change:**
```python
# V6
HOOP_ZONE_VERTICAL = 95  # Symmetric: 95px above and below

# V7 Phase 1 - Added asymmetric expansion
HOOP_ZONE_VERTICAL = 95      # Base vertical zone (symmetric bottom)
ZONE_EXPANSION_TOP = 100     # Extra expansion above hoop
# Result: 195px above hoop, 95px below hoop
```

**Updated Zone Check Logic:**
```python
# V6 - Symmetric check
dy = abs(ball_y - hoop_y)
in_zone = dx <= self.HOOP_ZONE_WIDTH and dy <= self.HOOP_ZONE_VERTICAL

# V7 Phase 1 - Asymmetric check
top_boundary = hoop_y - (self.HOOP_ZONE_VERTICAL + self.ZONE_EXPANSION_TOP)  # 195px above
bottom_boundary = hoop_y + self.HOOP_ZONE_VERTICAL  # 95px below
in_zone_vertical = top_boundary <= ball_y <= bottom_boundary
in_zone = in_zone_horizontal and in_zone_vertical
```

**Rationale:**
- V6 analysis showed 10 false negatives: "ball never entered from top"
- Root cause: Ball trajectory starts INSIDE the detection zone (already past top boundary)
- Fast shots where ball passes through before detection begins
- Expanding upward by 100px catches ball earlier in its arc

**Benefits:**
- Tracks ball 100px higher above the hoop
- Captures early trajectory before ball reaches hoop
- Ensures top boundary crossing is always detected
- Doesn't expand downward to avoid false positives from dribbles

**Target Errors (10):**
- Game 1 @ 25.8s, 918.2s, 2639.7s
- Game 2 @ 685.6s, 809.0s, 880.0s, 2545.5s
- Game 3 @ 734.4s, 1538.8s, 2324.2s

---

## 📊 Expected Performance

### Game 3 Test (6 target errors)
- **V6 Game 3:** 87.13% (13 errors out of 101 matched shots)
- **V7 Phase 1 Expected:** ~93% (7 errors if all 6 fixed)
  - Priority 4 fixes: 3 errors (105.5s, 780.9s, 2984.4s)
  - Priority 1 fixes: 3 errors (734.4s, 1538.8s, 2324.2s)

### All Games Combined (15 target errors)
- **V6 Average:** 86.84% (35 errors out of 266 matched shots)
- **V7 Phase 1 Expected:** ~92.5% (20 errors if all 15 fixed)
- **Improvement:** +5.6% accuracy

---

## 🔬 Testing Strategy

### Phase 1 Validation
1. **Quick Test:** Game 3 only (has both error types)
2. **Verify:** Check if 6 target timestamps are fixed
3. **Validate:** Compare accuracy with V6 Game 3 (87.13%)

### Success Criteria
- [x] Code syntax valid (passed `py_compile`)
- [ ] Game 3 accuracy improves by ~5-6% (87.13% → ~93%)
- [ ] Target error timestamps show correct classifications
- [ ] No new false positives introduced

---

## 📁 Files Modified

1. **simple_line_intersection_test.py**
   - Line 34: Added `ZONE_EXPANSION_TOP = 100`
   - Line 40: Changed `MAX_BALL_HOOP_RATIO = 0.40` → `0.50`
   - Lines 430-445: Updated zone check logic (asymmetric)
   - Lines 563-570: Updated zone visualization

2. **simple_line_intersection_test_v6_backup.py**
   - Created backup of V6 before Phase 1 changes

3. **test_v7_phase1.py**
   - Validation script for Phase 1 error timestamps

---

## 🚀 Next Steps After Phase 1 Validation

If Phase 1 successfully fixes the target errors:

### **Phase 2: Swish Detection Heuristic**
- Target: 7 incomplete_pass errors
- Approach: If ball enters from top + stays in zone >5 frames → MADE
- Expected gain: +2.6% accuracy

### **Phase 3: Post-Exit Trajectory Analysis**
- Target: 12 complete_pass_through false positives
- Approach: Track ball 10-15 frames after bottom crossing, detect bounce-out
- Expected gain: +3.8-4.5% accuracy

---

## 📊 V7 Complete Performance Projection

| Phase | Errors Fixed | Cumulative Accuracy |
|-------|--------------|---------------------|
| V6 Baseline | - | 86.84% |
| Phase 1 | 15 | 92.5% |
| Phase 2 | 7 | 95.1% |
| Phase 3 | 10-12 | 95-96% |

**V7 Target:** 95-96% accuracy (fix 32-34 of 35 V6 errors)

---

## 🔍 Code Changes Summary

```python
# V7 Phase 1 Changes

class SimplifiedShotAnalyzer:
    # CHANGE 1: Relaxed size ratio threshold
    MAX_BALL_HOOP_RATIO = 0.50  # V6: 0.40

    # CHANGE 2: Added asymmetric zone expansion
    ZONE_EXPANSION_TOP = 100    # NEW: Expand upward only

    # CHANGE 3: Asymmetric zone check
    # Old: dy <= HOOP_ZONE_VERTICAL (symmetric)
    # New: top_boundary <= ball_y <= bottom_boundary (asymmetric)
    top_boundary = hoop_y - (HOOP_ZONE_VERTICAL + ZONE_EXPANSION_TOP)
    bottom_boundary = hoop_y + HOOP_ZONE_VERTICAL
```

---

## ✅ Validation Checklist

Phase 1 validation criteria:

- [x] Code compiles without syntax errors
- [x] V6 backup created
- [ ] Game 3 test run completes successfully
- [ ] Accuracy improves from 87.13% to ~93%
- [ ] Priority 4 errors (3) are fixed:
  - [ ] Game 3 @ 105.5s (ratio 0.417)
  - [ ] Game 3 @ 780.9s (ratio 0.439)
  - [ ] Game 3 @ 2984.4s (ratio 0.435)
- [ ] Priority 1 errors (3) are fixed:
  - [ ] Game 3 @ 734.4s (no_top_crossing)
  - [ ] Game 3 @ 1538.8s (no_top_crossing)
  - [ ] Game 3 @ 2324.2s (no_top_crossing)
- [ ] No significant new false positives introduced

If all validation passes → Proceed to Phase 2
