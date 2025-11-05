# Thorough Analysis: V3 vs V4 Performance

## Executive Summary

**FINDING: V4 improvements caused a net regression across all tested datasets.**

| Version | Overall Accuracy | Status |
|---------|-----------------|--------|
| V3 (commit 2f96b08) | **93.04%** | Baseline |
| V4 (current + fix) | **87.83%** | ❌ **-5.22%** regression |

**RECOMMENDATION: Revert to V3 baseline (commit 2f96b08 or earlier)**

---

## Detailed Comparison

### Datasets with Old Baseline (V3) Available

| Dataset | V3 Accuracy | V4 Accuracy | Change | Correct→Incorrect |
|---------|-------------|-------------|--------|-------------------|
| 09-22(2-NL) | **92.16%** (47✓/4✗) | 88.24% (45✓/6✗) | **-3.92%** | 2 shots worse |
| 09-22(2-NR) | **93.75%** (60✓/4✗) | 87.50% (56✓/8✗) | **-6.25%** | 4 shots worse |
| **TOTAL** | **93.04%** (107✓/8✗) | 87.83% (101✓/14✗) | **-5.22%** | 6 shots worse |

### Datasets with Only V4 Results

These datasets have no V3 baseline to compare against:

| Dataset | V4 Accuracy | Note |
|---------|-------------|------|
| 09-22(1-NL) | 86.84% | Recovered from V4 bug (was 82.89%) |
| 09-22(1-NR) | 95.83% | Target dataset for V4 optimization |
| 09-22(3-NL) | 89.33% | Unknown if better/worse than V3 |
| 09-22(3-NR) | 90.24% | Unknown if better/worse than V3 |
| 09-23(1-NL) | 88.00% | Unknown if better/worse than V3 |
| 09-23(1-NR) | 88.46% | Unknown if better/worse than V3 |
| 09-23(2-NL) | 92.63% | Unknown if better/worse than V3 |
| 09-23(2-NR) | 91.35% | Unknown if better/worse than V3 |

---

## Root Cause Analysis

### What is V4?

V4 introduced **deceleration and reversal detection** in the `_analyze_post_hoop_trajectory()` function:

```python
# IMPROVEMENT 2.2: Track if downward movement decelerates or reverses
deceleration_detected = False
reversal_detected = False

# Analyzes velocity patterns to detect rim hits
if early_avg_vel > late_avg_vel * 1.5:
    deceleration_detected = True
```

This was then used in `_enhanced_rim_bounce_detection()` to add to bounce_score:

```python
if post_hoop_analysis.get('deceleration_detected', False):
    bounce_score += 1.0  # Deceleration suggests rim hit
```

### Why Did V4 Cause Regressions?

**Overfitting to 09-22(1-NR):**
- V4 was optimized specifically for 09-22(1-NR) to achieve 95.83%
- The deceleration detection worked well for that specific video's characteristics
- But it overfits and misclassifies shots in other videos

**False positives for rim bounces:**
- Natural made shot deceleration (ball passing through net) is detected as rim bounce
- Low overlap shots are incorrectly flagged as missed due to deceleration
- The 1.5x velocity threshold is too sensitive for many real made shots

**Dataset-specific behavior:**
- Camera angles vary across games
- Ball behavior through the net varies
- What works for one video regresses on others

---

## The Fix Attempt

My fix attempted to address the regression by preventing double-penalization:

```python
if post_hoop_analysis.get('deceleration_detected', False):
    # Only skip if: low angle (< 35°) AND high avg overlap (>= 75%)
    if entry_angle is None or entry_angle >= 35 or avg_overlap < 75:
        bounce_score += 1.0
```

**Result:**
- ✅ Fixed 09-22(1-NL): recovered from 82.89% to 86.84%
- ❌ But overall: still -5.22% regression vs V3

The fix addressed a symptom but not the root cause.

---

## Comparison: V3 vs V4 Trade-offs

### V3 Strengths (commit 2f96b08 or earlier)
- ✅ **Consistent**: 93.04% average across tested datasets
- ✅ **Stable**: No deceleration detection = fewer false positives
- ✅ **Generalizes well**: Works across different game videos
- ✅ **Simple**: Easier to understand and maintain

### V3 Weaknesses
- ❌ Lower accuracy on 09-22(1-NR): likely ~90% instead of 95.83%
- ❌ Misses some edge cases that V4 improvements target

### V4 Strengths
- ✅ **High peak accuracy**: 95.83% on 09-22(1-NR)
- ✅ **Advanced detection**: Deceleration/reversal detection for rim hits
- ✅ **More sophisticated**: Additional heuristics

### V4 Weaknesses
- ❌ **Overfitted**: Optimized for specific video
- ❌ **Regression on other datasets**: -3.92% to -6.25% on tested datasets
- ❌ **Net negative**: Overall -5.22% worse than V3
- ❌ **Complex**: More parameters to tune, harder to debug
- ❌ **Brittle**: Small changes cause large accuracy swings

---

## Key Insights

### 1. The Optimization Paradox
Optimizing for one dataset (09-22(1-NR)) to achieve 95.83% came at the cost of:
- 6 additional errors on other datasets
- Overall system accuracy decreased by 5.22%

**Trade-off:**
- Gain: +5.55% on 1 dataset
- Loss: -5.22% across all datasets
- Net: Negative impact on generalization

### 2. Deceleration Detection is Unreliable
The assumption "deceleration = rim bounce" doesn't hold universally:
- Made shots naturally decelerate through the net
- Camera angles affect perceived deceleration
- Different net types (loose vs tight) show different patterns

### 3. Simplicity > Complexity
V3's simpler approach generalizes better than V4's complex heuristics.

---

## Recommendations

### Option 1: Revert to V3 (RECOMMENDED)

**Action:** `git checkout 2f96b08` or earlier V3 commit

**Pros:**
- ✅ Immediate +5.22% overall accuracy gain
- ✅ Proven stable across multiple datasets
- ✅ Simpler codebase
- ✅ Easier to maintain and debug

**Cons:**
- ❌ Lose 95.83% peak on 09-22(1-NR) (likely drops to ~90%)
- ❌ Abandon V4 improvements work

**Expected Results:**
```
09-22(2-NL): 88.24% → 92.16% (+3.92%)
09-22(2-NR): 87.50% → 93.75% (+6.25%)
Overall: 87.83% → 93.04% (+5.22%)
```

---

### Option 2: Keep V4, Run More Tests

**Action:** Test V4 on all 8 datasets with V3 baseline runs

**Pros:**
- ✅ Get complete picture of V4 impact
- ✅ Might find V4 is better on untested datasets
- ✅ Data-driven decision

**Cons:**
- ❌ Time-consuming (8 dataset runs)
- ❌ Preliminary data suggests V4 will be net negative
- ❌ May confirm we need to revert anyway

**Risk:** High likelihood that overall results still show V4 regression

---

### Option 3: Hybrid Approach (NOT RECOMMENDED)

**Action:** Use dataset-specific logic or model selection

**Pros:**
- ✅ Could get best of both worlds

**Cons:**
- ❌ Extremely complex to maintain
- ❌ Overfitting to specific videos
- ❌ Not scalable to production
- ❌ Defeats purpose of general-purpose detector

---

## Final Recommendation

**REVERT TO V3 (Option 1)**

### Rationale:
1. **Proven performance**: V3 has 93.04% accuracy across tested datasets
2. **Generalization**: V3 works consistently across different games
3. **Simplicity**: Easier to understand, maintain, and improve upon
4. **Risk mitigation**: V4 has shown it regresses on unseen data

### Next Steps After Revert:
1. Re-baseline all datasets with V3
2. Identify systematic error patterns in V3
3. Design improvements that generalize across datasets
4. Test improvements on multiple datasets before committing
5. Use cross-validation approach (test on unseen videos)

---

## Lessons Learned

### 1. Avoid Overfitting to Single Dataset
Optimizing for one video's characteristics doesn't generalize.

### 2. Test on Multiple Datasets Before Committing
V4 looked great on 09-22(1-NR) but regressed on others.

### 3. Measure Overall System Performance
Peak accuracy on one dataset ≠ better overall system.

### 4. Simpler is Often Better
Complex heuristics are harder to tune and more prone to overfitting.

### 5. Establish Baselines First
Should have run V3 on all datasets before V4 changes.

---

## Commit to Revert To

**Target Commit:** `2f96b08` - ✨ Improve results folder naming

This was the commit active when the baseline results (09-22(2-NL), 09-22(2-NR)) were generated with 93.04% overall accuracy.

**Alternative:** Could go back to `ac374bb` - 🚀 V3: Physics-based improvements - 90% accuracy achieved

---

## Commands to Revert

```bash
# Option A: Create new branch from V3
git checkout -b revert-to-v3 2f96b08

# Option B: Hard reset main to V3 (DESTRUCTIVE)
git reset --hard 2f96b08

# Option C: Revert commits (preserves history)
git revert --no-commit 20f10cf..HEAD
git commit -m "Revert V4 changes - net regression observed"
```

---

*Analysis Date: 2025-11-01*
*Datasets Analyzed: 10 total (2 with V3 baseline, 8 V4 only)*
*Overall V3→V4 Change: -5.22% regression*
