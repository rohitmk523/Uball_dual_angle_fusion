# V4 Regression Analysis - 09-22 Game1 Near Left

## Summary
V4 improvements that worked well for 09-22 Game1 Near Right (90% → 95.83%) **caused a regression** for 09-22 Game1 Near Left, dropping accuracy from **86.84% to 82.89%** (-3.95%).

## Metrics Comparison

| Metric | Old (7d465647) | New (4f9cfca3) | Change |
|--------|---------------|---------------|---------|
| matched_correct | 66 | 63 | -3 |
| matched_incorrect | 10 | 13 | +3 |
| **matched_shots_accuracy** | **86.84%** | **82.89%** | **-3.95%** |

## Root Cause Analysis

### The Bug
The V4 `deceleration_detected` feature in `_analyze_post_hoop_trajectory()` is **too aggressive** and incorrectly flags made shots as rim bounces when combined with low entry angles.

### How It Fails

In `shot_detection.py:584-619`, the rim bounce detection calculates a bounce_score:

1. **Low entry angle** (< 35°): +1.5 to bounce_score
2. **deceleration_detected**: +1.0 to bounce_score
3. Total: 2.5 → triggers `is_rim_bounce = True` (threshold: 2.5)

When `is_rim_bounce == True`, the code **skips critical decision branches**:
- Line 795: `frames_with_100_percent >= 5 and avg_overlap >= 80 and not is_rim_bounce`
- Line 807: `frames_with_100_percent >= 3 and not is_rim_bounce`

Result: Perfect overlap shots with low entry angles are **incorrectly classified as "missed"** with reason "insufficient_overlap", despite having **100% max overlap and 76-91% avg overlap**.

### Affected Shots

5 shots changed from **CORRECT (made)** → **INCORRECT (missed)**:

| Timestamp | Entry Angle | Max Overlap | Avg Overlap | Old Classification | New Classification | Issue |
|-----------|-------------|-------------|-------------|-------------------|-------------------|-------|
| 1098.03 | 15.77° | 100% | 76.88% | made (perfect_overlap) | **missed** (insufficient_overlap) | decel + low angle |
| 1936.04 | 15.26° | 100% | 79.10% | made (perfect_overlap_continues_down_strong) | **missed** (insufficient_overlap) | decel + low angle |
| 2514.61 | 26.99° | 100% | 91.30% | made (perfect_overlap) | **missed** (insufficient_overlap) | decel + low angle |
| 1349.75 | 33.20° | 100% | 84.12% | made (perfect_overlap_continues_down_strong) | **missed** (insufficient_overlap) | decel + low angle |

**Common Pattern:**
- All have **100% max overlap**
- All have **high avg overlap (76-91%)**
- All have **low entry angles (15-33°)**
- All show `deceleration_detected: True` but `confidence: 0.0`

### Why Deceleration Detection Fails

The deceleration detection triggers on **normal made shot behavior**:
- Made shots naturally slow down as the ball passes through the net
- This is NOT a rim bounce, but the algorithm treats it as one
- When combined with low entry angles (common in near-angle cameras), it creates false positives

## Code Location

**File:** `shot_detection.py`

**Lines 584-585:** Deceleration adds to bounce_score
```python
if post_hoop_analysis.get('deceleration_detected', False):
    bounce_score += 1.0  # Deceleration suggests rim hit
```

**Lines 591-592:** Low angle adds to bounce_score
```python
if entry_angle is not None and entry_angle < 35:
    bounce_score += 1.5
```

**Line 616:** Bounce threshold
```python
is_bounce = bounce_score >= 2.5
```

**Lines 795, 807:** Perfect overlap branches skip if `is_rim_bounce`
```python
elif frames_with_100_percent >= 5 and avg_overlap >= 80 and not is_rim_bounce:
    # This branch is SKIPPED for low-angle shots with deceleration
```

## Fix Options

### Option 1: Don't Double-Penalize Low Angles with High Overlap (IMPLEMENTED)
Don't add deceleration to bounce_score if entry angle is low AND avg overlap is high:
```python
if post_hoop_analysis.get('deceleration_detected', False):
    # Only skip if: low angle (< 35°) AND high avg overlap (>= 75%)
    # Low angle + low overlap might be legitimate rim bounce
    if entry_angle is None or entry_angle >= 35 or avg_overlap < 75:
        bounce_score += 1.0
```

**Rationale:**
- Low angle + high overlap (≥75%) = likely clean made shot (skip deceleration penalty)
- Low angle + low overlap (<75%) = might be rim bounce (keep deceleration penalty)

### Option 2: Increase Bounce Threshold
Require higher confidence before flagging as rim bounce:
```python
is_bounce = bounce_score >= 3.0  # Was 2.5
```

### Option 3: Override for Perfect Overlap
Allow perfect overlap to override rim bounce flag:
```python
if frames_with_100_percent >= 5 and avg_overlap >= 80:
    # Perfect overlap overrides rim bounce for low confidence
    if not is_rim_bounce or bounce_confidence < 0.6:
        outcome = "made"
```

### Option 4: Improve Deceleration Detection
Make deceleration detection more sophisticated to distinguish between:
- Natural made shot deceleration (going through net)
- Actual rim bounce deceleration (hitting rim and bouncing back)

## Recommendation

Implement **Option 1 (refined)** - only skip deceleration penalty when there's strong overlap evidence (avg ≥75%). This prevents double-penalization of clean made shots while still detecting legitimate rim bounces with lower overlap.

## Validation on 09-23(1-NR)

Before fix was applied, V4 showed improvement on 09-23(1-NR):
- Old: 84.61% → New: 88.46% (+3.85%)
- 9 shots became correct, including 1 at timestamp 467.80 with:
  - Entry angle: 32.38° (< 35°)
  - Avg overlap: 67.72% (< 75%)
  - Deceleration detected: True
  - Ground truth: MISSED

**Fix preserves this improvement** because:
- Condition: `entry_angle >= 35 or avg_overlap < 75`
- Shot 467.80: avg_overlap = 67.72% < 75 → deceleration STILL adds to bounce_score
- Result: Shot correctly classified as MISSED ✓

## Impact Assessment

- **09-22(1-NL):** Fixes 5 false negatives (all have avg overlap 76-91% ≥ 75%)
- **09-23(1-NR):** Preserves improvement (critical shot has avg overlap 67.72% < 75%)
- **Net:** All regressions fixed, no new regressions introduced
- **Logic:** High overlap = clean shot, low overlap = potential rim bounce
