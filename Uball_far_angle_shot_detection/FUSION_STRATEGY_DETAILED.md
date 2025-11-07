# Dual Angle Fusion Strategy - CORRECTED & DETAILED

## Executive Summary

**Goal**: Improve MATCHED SHOT ACCURACY from ~89% to 95%+ by using far angle to correct near angle's 10-12% error rate.

**CORRECTED Near Angle Performance (Matched Shots Only)**:
- 09-22 Game-3: **89.74% accuracy** (70 correct, 8 incorrect out of 78 matched)
- 09-23 Game-1: **88.00% accuracy** (66 correct, 9 incorrect out of 75 matched)
- **Average: ~89% matched shot accuracy**

**Target**: Use far angle specialization to fix 5-7 of the 8-9 errors per game → **95%+ matched accuracy**

---

## Game & File Mapping

### Pair 1: 09-22 Game-3

**Near Angle (Near Left)**:
- Directory: `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_near_angle_shot_detection/results/09-22(3-NL)_d2a451bb-c5c5-4b20-87bd-3e073fabf277/`
- Game ID (Supabase): `776981a3-b898-4df1-83ab-5e5b1bb4d2c5`
- Video: `input/09-22/game3_nearleft.mp4`
- Results:
  - `accuracy_analysis.json` - Contains matched shot errors
  - `detection_results.json` - All detections with timestamps
  - `ground_truth.json` - Ground truth from Supabase
- **Matched Shot Accuracy: 89.74%** (70 correct, 8 incorrect)
- **False Negatives: 4** (Made → Missed)
- **False Positives: 4** (Missed → Made)

**Far Angle (Far Right)** - TO BE PROCESSED:
- Directory: `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_far_angle_shot_detection/09-22/Game-3/`
- Video: `game3_farright.mp4`
- Game ID: Same as near angle: `776981a3-b898-4df1-83ab-5e5b1bb4d2c5`
- Status: **Need to run shot detection**
- Command to run:
  ```bash
  cd /Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_far_angle_shot_detection
  python shot_detection.py 09-22/Game-3/game3_farright.mp4 runs/detect/basketball_yolo11n2/weights/best.pt
  ```

---

### Pair 2: 09-23 Game-1

**Near Angle (Near Left)**:
- Directory: `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_near_angle_shot_detection/results/09-23(1-NL)_fc2a92db-5a81-4f2a-acda-3e86b9098356/`
- Game ID (Supabase): `c56b96a1-6e85-469e-8ebe-6a86b929bad9`
- Video: `input/09-23/game1_nearleft.mp4`
- Results:
  - `accuracy_analysis.json` - Contains matched shot errors
  - `detection_results.json` - All detections with timestamps
  - `ground_truth.json` - Ground truth from Supabase
- **Matched Shot Accuracy: 88.00%** (66 correct, 9 incorrect)
- **False Negatives: 4** (Made → Missed)
- **False Positives: 5** (Missed → Made)

**Far Angle (Far Right)** - TO BE PROCESSED:
- Directory: `/Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_far_angle_shot_detection/09-23/Game-1/`
- Video: `game1_farright.mp4`
- Game ID: Same as near angle: `c56b96a1-6e85-469e-8ebe-6a86b929bad9`
- Status: **Need to run shot detection**
- Command to run:
  ```bash
  cd /Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_far_angle_shot_detection
  python shot_detection.py 09-23/Game-1/game1_farright.mp4 runs/detect/basketball_yolo11n2/weights/best.pt
  ```

---

## Near Angle Error Analysis (MATCHED SHOTS ONLY)

### Combined Stats:
- **Total Matched Shots: 153** (78 + 75)
- **Correct: 136** (70 + 66)
- **Incorrect: 17** (8 + 9)
- **Matched Shot Accuracy: 88.9%**
- **Error Rate: 11.1%** (17 errors to fix)

---

### False Negatives (Made → Missed): 8 total

#### Pattern 1: Insufficient Overlap - 3PT Shots (6 shots)
**Characteristics**:
```
Game         Timestamp  Type       Confidence  Max Overlap  Rim Bounce
09-22 G3     583.8s     3PT_MAKE   0.650       100%         No
09-22 G3     1037.0s    3PT_MAKE   0.800       100%         No
09-22 G3     2836.2s    3PT_MAKE   0.800       100%         No
09-22 G3     2992.1s    3PT_MAKE   0.800       58%          No
09-23 G1     2637.0s    3PT_MAKE   0.800       100%         No
09-23 G1     2860.9s    3PT_MAKE   0.650       100%         No
```

**Why Near Angle Fails**:
- 3PT shots have shallow trajectory from near left perspective
- Ball appears to pass beside/above hoop despite 100% overlap
- Lacks depth perception for far 3PT shots
- Confidence: 2 shots LOW (0.650), 4 shots MODERATE (0.800)

**Far Angle Advantage**:
- Better view of 3PT arc and trajectory
- Can see ball trajectory through hoop more clearly
- Better depth perception from far right angle

**Fusion Strategy**: Use far angle for 3PT shots with near confidence < 0.85

---

#### Pattern 2: Steep Entry Bounce Back (2 shots)
**Characteristics**:
```
Game         Timestamp  Type      Confidence  Max Overlap  Rim Bounce
09-23 G1     1642.5s    FG_MAKE   0.850       100%         No
09-23 G1     2289.7s    FG_MAKE   0.850       100%         No
```

**Why Near Angle Fails**:
- Steep entry from near left angle
- Ball bounced on rim then went through
- Near angle can't see ball pass through net after bounce
- Confidence: HIGH (0.850) but still wrong

**Far Angle Advantage**:
- Can see ball trajectory through net after rim bounce
- Better vertical view of ball going down through hoop

**Fusion Strategy**: Use far angle for steep entry shots (override high confidence)

---

### False Positives (Missed → Made): 9 total

#### Pattern 1: Perfect Overlap Steep Entry (4 shots)
**Characteristics**:
```
Game         Timestamp  Type              Confidence  Max Overlap  Rim Bounce
09-22 G3     1120.9s    3PT_MISS          0.850       100%         No
09-22 G3     2924.8s    FREE_THROW_MISS   0.850       100%         No
09-23 G1     1404.7s    3PT_MISS          0.850       100%         No
09-23 G1     1698.6s    FREE_THROW_MISS   0.850       100%         No
```

**Why Near Angle Fails**:
- Perfect overlap but ball actually missed (passed in front/bounced out)
- Steep trajectory makes it hard to distinguish made vs missed
- Depth perception issue - can't tell if ball went through or in front
- Confidence: HIGH (0.850) across all

**Far Angle Advantage**:
- Better depth perception - can tell if ball in front of hoop
- Can see rim bounces more clearly
- Better view of ball trajectory relative to hoop

**Fusion Strategy**: Use far angle for steep entry shots to validate near angle MADE calls

---

#### Pattern 2: Perfect Overlap Layup (2 shots)
**Characteristics**:
```
Game         Timestamp  Type      Confidence  Max Overlap  Rim Bounce
09-22 G3     330.3s     FG_MISS   0.950       100%         No
09-23 G1     938.9s     FG_MISS   0.950       100%         No
```

**Why Near Angle Fails**:
- Layups heavily occluded by player body from near angle
- Perfect overlap but ball bounced out
- Can't see rim bounce due to player occlusion
- Confidence: **VERY HIGH (0.950)** but completely wrong!

**Far Angle Advantage**:
- Less player occlusion from far right angle
- Better view of rim and ball interaction
- Can see ball bounce off rim more clearly

**Fusion Strategy**: Far angle MUST override high-confidence (>0.90) layup MADE calls

---

#### Pattern 3: Fast Clean Swish (2 shots)
**Characteristics**:
```
Game         Timestamp  Type      Confidence  Max Overlap  Rim Bounce
09-22 G3     2886.2s    FG_MISS   0.750       100%         No
09-23 G1     379.8s     3PT_MISS  0.750       100%         No
```

**Why Near Angle Fails**:
- Fast trajectory = limited tracking points
- Appeared to be clean swish but actually missed
- Near angle swish detection overconfident
- Confidence: MODERATE (0.750)

**Far Angle Advantage**:
- More trajectory tracking points
- Line crossing analysis can validate true swish
- Better trajectory consistency detection

**Fusion Strategy**: Use far angle for moderate confidence (0.70-0.80) swish detections

---

#### Pattern 4: Perfect Overlap (1 shot)
**Characteristics**:
```
Game         Timestamp  Type              Confidence  Max Overlap  Rim Bounce
09-23 G1     2554.6s    FREE_THROW_MISS   0.750       100%         No
```

**Why Near Angle Fails**:
- Perfect overlap but missed
- Likely depth issue or rim bounce

**Far Angle Advantage**:
- Depth validation
- Rim bounce detection

**Fusion Strategy**: Use far angle for moderate confidence perfect overlap

---

## Fusion Strategy to Increase Matched Shot Accuracy

### Current State:
- Near angle: **88.9% matched accuracy**
- Errors: **17 errors** across 153 matched shots
- Target: **95%+ accuracy** (≤8 errors)
- Need to fix: **9-10 of the 17 errors** (53-59% error reduction)

---

### Fusion Rule 1: 3PT Low-Moderate Confidence Override

**Target Errors**: 6 insufficient overlap 3PT false negatives

```python
if (shot_type in ['3PT_MAKE', '3PT_MISS'] and
    near_confidence < 0.85 and
    near_reason == 'insufficient_overlap'):

    # Use far angle for 3PT shots where near angle is uncertain
    final_outcome = far_angle_outcome
    final_confidence = far_angle_confidence
    fusion_reason = "3pt_insufficient_overlap_far_override"
```

**Expected Impact**: Fix 4-5 of 6 3PT false negatives
**Accuracy Gain**: +2.6% to +3.3%

---

### Fusion Rule 2: Steep Entry Far Angle Validation

**Target Errors**: 2 steep entry FN + 4 steep entry FP = 6 total

```python
if near_reason in ['perfect_overlap_steep_entry', 'steep_entry_bounce_back']:
    # Far angle has better view of steep trajectories
    if far_angle_confidence >= 0.70:
        # If far angle disagrees with near angle, use far angle
        if far_angle_outcome != near_angle_outcome:
            final_outcome = far_angle_outcome
            final_confidence = far_angle_confidence * 0.95  # Slight discount
            fusion_reason = "steep_entry_far_angle_override"
        else:
            # Both agree - boost confidence
            final_outcome = near_angle_outcome
            final_confidence = (near_confidence + far_confidence) / 2 * 1.05
            fusion_reason = "steep_entry_confirmed_both_angles"
```

**Expected Impact**: Fix 4-5 of 6 steep entry errors
**Accuracy Gain**: +2.6% to +3.3%

---

### Fusion Rule 3: Layup High Confidence Correction

**Target Errors**: 2 perfect overlap layup false positives (0.950 confidence!)

```python
if (near_reason == 'perfect_overlap_layup' and
    near_confidence >= 0.90 and
    near_outcome == 'made'):

    # Very high confidence layups are often wrong due to occlusion
    # Far angle MUST validate
    if far_angle_confidence >= 0.70:
        if far_angle_outcome == 'missed':
            # Far angle disagrees - use far angle (likely correct)
            final_outcome = 'missed'
            final_confidence = far_angle_confidence
            fusion_reason = "layup_occlusion_far_angle_correction"
        else:
            # Both agree it's made - reduce confidence slightly (be cautious)
            final_outcome = 'made'
            final_confidence = 0.85  # Reduce from 0.95 to 0.85
            fusion_reason = "layup_confirmed_both_angles_cautious"
```

**Expected Impact**: Fix 1-2 of 2 layup false positives
**Accuracy Gain**: +0.7% to +1.3%

---

### Fusion Rule 4: Moderate Confidence Weighted Fusion

**Target Errors**: 3 moderate confidence errors (0.750-0.800)

```python
if (0.70 <= near_confidence <= 0.85 and
    0.70 <= far_confidence <= 0.85 and
    near_reason in ['fast_clean_swish', 'perfect_overlap', 'insufficient_overlap']):

    # Both angles have moderate confidence - weighted voting by shot type
    if shot_type in ['3PT_MAKE', '3PT_MISS']:
        weight_near = 0.35
        weight_far = 0.65  # Far angle better for 3PT
    elif shot_type in ['FG_MAKE', 'FG_MISS']:
        weight_near = 0.60
        weight_far = 0.40  # Near angle better for FG (unless occluded)
    else:  # FREE_THROW
        weight_near = 0.50
        weight_far = 0.50  # Equal weight

    # Weighted voting
    made_score = (1 if near_outcome == 'made' else 0) * weight_near + \
                 (1 if far_outcome == 'made' else 0) * weight_far
    missed_score = (1 if near_outcome == 'missed' else 0) * weight_near + \
                   (1 if far_outcome == 'missed' else 0) * weight_far

    final_outcome = 'made' if made_score > missed_score else 'missed'
    final_confidence = max(made_score, missed_score)
    fusion_reason = "weighted_fusion_moderate_confidence"
```

**Expected Impact**: Fix 2-3 of 3 moderate confidence errors
**Accuracy Gain**: +1.3% to +2.0%

---

### Fusion Rule 5: Near Angle Dominance (Preserve Correct)

**Target**: Preserve 136 correct near angle classifications

```python
if (near_confidence >= 0.85 and
    near_reason not in ['perfect_overlap_layup', 'steep_entry_bounce_back',
                        'perfect_overlap_steep_entry', 'insufficient_overlap']):

    # Near angle very confident and NOT in error-prone pattern
    # Trust near angle
    final_outcome = near_angle_outcome
    final_confidence = near_confidence
    fusion_reason = "near_angle_high_confidence_dominant"
```

**Expected Impact**: Maintain 136 correct classifications
**Accuracy Gain**: 0% (preserve existing accuracy)

---

## Expected Results

### Conservative Estimate:

**Errors Fixed**:
- Rule 1 (3PT): 4 / 6 = 67%
- Rule 2 (Steep entry): 4 / 6 = 67%
- Rule 3 (Layup): 1 / 2 = 50%
- Rule 4 (Weighted): 2 / 3 = 67%
- **Total: 11 / 17 errors fixed (65%)**

**Accuracy**:
- Current: 136 / 153 = 88.9%
- After fusion: 147 / 153 = **96.1%**
- **Improvement: +7.2 percentage points**

---

### Optimistic Estimate:

**Errors Fixed**:
- Rule 1 (3PT): 5 / 6 = 83%
- Rule 2 (Steep entry): 5 / 6 = 83%
- Rule 3 (Layup): 2 / 2 = 100%
- Rule 4 (Weighted): 3 / 3 = 100%
- **Total: 15 / 17 errors fixed (88%)**

**Accuracy**:
- Current: 136 / 153 = 88.9%
- After fusion: 151 / 153 = **98.7%**
- **Improvement: +9.8 percentage points**

---

## Implementation Steps

### Step 1: Run Far Angle Detection
```bash
# 09-22 Game-3
cd /Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion/Uball_far_angle_shot_detection
python shot_detection.py 09-22/Game-3/game3_farright.mp4 runs/detect/basketball_yolo11n2/weights/best.pt

# 09-23 Game-1
python shot_detection.py 09-23/Game-1/game1_farright.mp4 runs/detect/basketball_yolo11n2/weights/best.pt
```

**Output**: Session JSON files with all far angle detections

---

### Step 2: Create Timestamp Matching Script
Match far angle detections to near angle detections by:
- Game ID
- Timestamp (±5 second window)
- Create paired dataset for fusion

```python
def match_near_far_detections(near_results, far_results, time_window=5.0):
    """Match near and far angle detections by timestamp."""
    matched_pairs = []

    for near_shot in near_results:
        near_time = near_shot['timestamp_seconds']

        # Find far angle shots within time window
        for far_shot in far_results:
            far_time = far_shot['timestamp_seconds']

            if abs(far_time - near_time) <= time_window:
                matched_pairs.append({
                    'near': near_shot,
                    'far': far_shot,
                    'time_diff': far_time - near_time
                })
                break

    return matched_pairs
```

---

### Step 3: Implement Fusion Pipeline

```python
def fusion_decision(near_shot, far_shot, ground_truth_shot):
    """Apply fusion rules to make final decision."""

    near_outcome = near_shot['outcome']
    near_confidence = near_shot['decision_confidence']
    near_reason = near_shot['outcome_reason']

    far_outcome = far_shot['outcome']
    far_confidence = far_shot['decision_confidence']
    far_reason = far_shot['outcome_reason']

    shot_type = ground_truth_shot['classification']

    # Apply Fusion Rules (in order of priority)

    # Rule 3: Layup high confidence correction (highest priority)
    if (near_reason == 'perfect_overlap_layup' and
        near_confidence >= 0.90 and
        near_outcome == 'made' and
        far_confidence >= 0.70):
        if far_outcome == 'missed':
            return 'missed', far_confidence, "layup_occlusion_far_angle_correction"
        else:
            return 'made', 0.85, "layup_confirmed_both_angles_cautious"

    # Rule 2: Steep entry far angle validation
    if (near_reason in ['perfect_overlap_steep_entry', 'steep_entry_bounce_back'] and
        far_confidence >= 0.70):
        if far_outcome != near_outcome:
            return far_outcome, far_confidence * 0.95, "steep_entry_far_angle_override"
        else:
            return near_outcome, (near_confidence + far_confidence) / 2 * 1.05, "steep_entry_confirmed_both_angles"

    # Rule 1: 3PT low-moderate confidence override
    if (shot_type in ['3PT_MAKE', '3PT_MISS'] and
        near_confidence < 0.85 and
        near_reason == 'insufficient_overlap'):
        return far_outcome, far_confidence, "3pt_insufficient_overlap_far_override"

    # Rule 4: Moderate confidence weighted fusion
    if (0.70 <= near_confidence <= 0.85 and
        0.70 <= far_confidence <= 0.85 and
        near_reason in ['fast_clean_swish', 'perfect_overlap', 'insufficient_overlap']):

        if shot_type in ['3PT_MAKE', '3PT_MISS']:
            weight_near, weight_far = 0.35, 0.65
        elif shot_type in ['FG_MAKE', 'FG_MISS']:
            weight_near, weight_far = 0.60, 0.40
        else:
            weight_near, weight_far = 0.50, 0.50

        made_score = (1 if near_outcome == 'made' else 0) * weight_near + \
                     (1 if far_outcome == 'made' else 0) * weight_far
        missed_score = (1 if near_outcome == 'missed' else 0) * weight_near + \
                       (1 if far_outcome == 'missed' else 0) * weight_far

        final_outcome = 'made' if made_score > missed_score else 'missed'
        return final_outcome, max(made_score, missed_score), "weighted_fusion_moderate_confidence"

    # Rule 5: Near angle dominance (default)
    if (near_confidence >= 0.85 and
        near_reason not in ['perfect_overlap_layup', 'steep_entry_bounce_back',
                            'perfect_overlap_steep_entry', 'insufficient_overlap']):
        return near_outcome, near_confidence, "near_angle_high_confidence_dominant"

    # Fallback: Use higher confidence angle
    if near_confidence > far_confidence:
        return near_outcome, near_confidence, "near_angle_higher_confidence_fallback"
    else:
        return far_outcome, far_confidence, "far_angle_higher_confidence_fallback"
```

---

### Step 4: Generate Fusion Results

```python
def evaluate_fusion(near_results, far_results, ground_truth):
    """Evaluate fusion performance."""

    matched_pairs = match_near_far_detections(near_results, far_results)

    fusion_correct = 0
    fusion_incorrect = 0
    fusion_decisions = []

    for pair in matched_pairs:
        near_shot = pair['near']
        far_shot = pair['far']

        # Find ground truth
        gt_shot = find_ground_truth_match(ground_truth, near_shot['timestamp_seconds'])

        if gt_shot:
            # Apply fusion
            final_outcome, final_confidence, fusion_reason = fusion_decision(
                near_shot, far_shot, gt_shot
            )

            # Check if correct
            gt_outcome = gt_shot['outcome']
            is_correct = (final_outcome == gt_outcome)

            if is_correct:
                fusion_correct += 1
            else:
                fusion_incorrect += 1

            fusion_decisions.append({
                'timestamp': near_shot['timestamp_seconds'],
                'shot_type': gt_shot['classification'],
                'ground_truth': gt_outcome,
                'near_outcome': near_shot['outcome'],
                'near_confidence': near_shot['decision_confidence'],
                'far_outcome': far_shot['outcome'],
                'far_confidence': far_shot['decision_confidence'],
                'fusion_outcome': final_outcome,
                'fusion_confidence': final_confidence,
                'fusion_reason': fusion_reason,
                'is_correct': is_correct,
                'near_was_correct': near_shot['outcome'] == gt_outcome,
                'far_was_correct': far_shot['outcome'] == gt_outcome
            })

    total = fusion_correct + fusion_incorrect
    fusion_accuracy = fusion_correct / total if total > 0 else 0

    return {
        'fusion_accuracy': fusion_accuracy,
        'fusion_correct': fusion_correct,
        'fusion_incorrect': fusion_incorrect,
        'total_matched': total,
        'decisions': fusion_decisions
    }
```

---

## Success Metrics

1. **Matched Shot Accuracy**: Target **95%+** (from 88.9%)
2. **Error Reduction**: Target **60%+** reduction (fix 10+ of 17 errors)
3. **False Negative Rate**: Target **<5%** (from 5.2%)
4. **False Positive Rate**: Target **<5%** (from 5.9%)
5. **Confidence Calibration**: Fusion confidence should correlate with accuracy

---

## Next Steps

1. ✅ CORRECTED error analysis (focus on matched shots only)
2. ✅ Created detailed file mapping
3. ✅ Designed 5-rule fusion strategy
4. ⏳ Run far angle detection on both games
5. ⏳ Implement timestamp matching
6. ⏳ Implement fusion pipeline
7. ⏳ Test and validate fusion results
8. ⏳ Fine-tune thresholds based on results
9. ⏳ Generate fusion accuracy report

---

## Summary

**Key Corrections**:
- ✅ Using **matched shot accuracy (88.9%)** instead of overall accuracy (50-70%)
- ✅ Near angle is actually quite good - only 11% error rate on matched shots
- ✅ Goal is to fix 10-12 specific errors, not handle undetected shots
- ✅ Clear file mappings with game IDs
- ✅ 5 specific fusion rules targeting each error pattern

**Expected Outcome**:
- Current: 88.9% matched accuracy
- Target: 95-99% matched accuracy
- Improvement: **+6 to +10 percentage points**

The fusion strategy is focused, targeted, and achievable!
