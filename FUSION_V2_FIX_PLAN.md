# Fusion V2 Fix Plan - Addressing False Positive "Made" Calls

**Date**: 2025-11-15
**Status**: Ready for Implementation
**Context**: V2 achieved 91.0% accuracy (6 errors) vs V1's 91.2% (7 errors), but ALL 6 V2 errors are false positives

---

## Executive Summary

**Problem**: V2 feature-based fusion is too aggressive in calling shots as "made", resulting in 6 false positives (predicting "made" when ground truth is "missed"). These are likely rim bounces being misclassified as clean makes.

**Root Cause**: The weighted confidence scoring is boosting "made" predictions too much, and rim bounce detection features aren't strong enough to override base confidence when both angles weakly agree on "made".

**Goal**: Reduce false positives from 6 to ≤3 while maintaining high recall on actual made shots, targeting **93%+ accuracy**.

---

## Current V2 Performance

### Metrics
| Metric | V1 | V2 | Target |
|--------|----|----|--------|
| Accuracy | 91.2% | 91.0% | **93%+** |
| Coverage | 88.3% | 87.0% | 90%+ |
| Total Errors | 7 | 6 | ≤4 |
| False Positives (made→missed) | 4 | **6** | ≤3 |
| False Negatives (missed→made) | 3 | 0 | ≤1 |

### V2 Error Cases (All False Positives)
1. **124.06s** - Fusion: made, GT: missed
2. **939.57s** - Fusion: made, GT: missed
3. **1549.75s** - Fusion: made, GT: missed
4. **1937.84s** - Fusion: made, GT: missed
5. **2250.68s** - Fusion: made, GT: missed
6. **2555.96s** - Fusion: made, GT: missed

**Pattern**: All errors are rim bounces being called as "made"

---

## Current V2 Feature Weights

```python
weights = {
    'outcome_agreement': 0.30,      # Both angles agree on outcome
    'rim_bounce_agreement': 0.20,   # Both angles agree on rim bounce
    'entry_angle_consistency': 0.15,# Entry trajectories match
    'swoosh_speed': 0.15,           # Fast swoosh = made, slow = missed
    'overlap_quality': 0.10,        # Near angle: ball-hoop overlap
    'line_intersection': 0.10       # Far angle: line crossings
}
```

**Issue**: `rim_bounce_agreement` weight is too low relative to `outcome_agreement`

---

## Root Cause Analysis

### Why V2 Calls Rim Bounces as "Made"

1. **Both angles weakly agree on "made"**
   - Near angle: Insufficient overlap → calls it "missed" with low confidence
   - Far angle: Sees ball pass through lines → calls it "made" with medium confidence
   - V2 boosts this weak agreement through feature scoring

2. **Rim bounce detection not strong enough**
   - `rim_bounce_agreement` is only 20% of total weight
   - When near says "no bounce" and far says "no bounce", V2 treats this as high confidence for "made"
   - But the detectors might both MISS the rim bounce!

3. **Swoosh speed analysis inadequate**
   - Current logic only checks `ball_continues_down` and `bottom_crossings`
   - Doesn't account for ball oscillation or slow descent patterns
   - Rim bounces that eventually go through still get "fast swoosh" score

4. **Confidence formula too optimistic**
   - `final_confidence = base_conf * (0.7 + 0.6 * weighted_score)`
   - Even mediocre weighted_score (0.6) results in 1.06x multiplier
   - This amplifies false positives

---

## Proposed Fixes

### Phase 1: Conservative Rim Bounce Detection (High Priority)

**Change 1**: Increase rim bounce weight, decrease outcome agreement weight
```python
weights = {
    'outcome_agreement': 0.25,      # Decreased from 0.30
    'rim_bounce_agreement': 0.30,   # Increased from 0.20 ← KEY FIX
    'entry_angle_consistency': 0.15,
    'swoosh_speed': 0.15,
    'overlap_quality': 0.08,        # Decreased from 0.10
    'line_intersection': 0.07       # Decreased from 0.10
}
```

**Change 2**: Add "rim bounce suspected" penalty in `resolve_disagreement()`
```python
def resolve_disagreement(self, near_shot: Dict, far_shot: Dict, fusion_analysis: Dict) -> Tuple[str, float]:
    # ... existing code ...

    # NEW: Check for rim bounce indicators
    rim_bounce_suspected = False
    rim_check = self.check_rim_bounce_agreement(near_shot, far_shot)

    # If either angle detected bounce, be conservative
    if near_shot.get('is_rim_bounce') or far_shot.get('bounced_back_out'):
        rim_bounce_suspected = True

    # If near has low overlap AND far has low confidence, likely rim bounce
    near_overlap = near_shot.get('weighted_overlap_score', 0) / 2.0
    far_conf = far_shot.get('confidence', far_shot.get('detection_confidence', 0))
    if near_overlap < 0.4 and far_conf < 0.75:
        rim_bounce_suspected = True

    # High confidence indicators for MADE:
    made_indicators = [
        feature_scores['rim_bounce_agreement'] < 0.6,
        feature_scores['swoosh_speed'] > 0.8,
        feature_scores['line_intersection'] > 0.8,
        feature_scores['overlap_quality'] > 0.7,
        not rim_bounce_suspected  # NEW: Only confident if no bounce suspected
    ]

    made_score = sum(made_indicators)

    # If rim bounce suspected, bias toward "missed"
    if rim_bounce_suspected:
        made_score = max(0, made_score - 2)  # Heavy penalty

    # ... rest of logic ...
```

**Expected Impact**: Reduce 4-5 of the 6 false positives

---

### Phase 2: Improved Swoosh Speed Analysis (Medium Priority)

**Change 3**: Enhance `analyze_swoosh_speed()` to detect oscillation
```python
def analyze_swoosh_speed(self, near_shot: Dict, far_shot: Dict) -> Dict:
    # Near angle analysis
    post_hoop = near_shot.get('post_hoop_analysis', {})
    near_continues_down = post_hoop.get('ball_continues_down', False)
    downward_movement = post_hoop.get('downward_movement', 0)
    upward_movement = post_hoop.get('upward_movement', 0)

    # NEW: Detect oscillation (rim bounce indicator)
    oscillation_ratio = 0
    if downward_movement > 0:
        oscillation_ratio = upward_movement / downward_movement

    # Far angle analysis
    far_size_ratio = far_shot.get('avg_size_ratio', 0)
    far_bottom_crossings = far_shot.get('valid_bottom_crossings', 0)
    far_bounced_back = far_shot.get('bounced_back_out', False)

    # Fast swoosh indicators (stricter criteria):
    fast_swoosh = (
        near_continues_down and
        far_bottom_crossings > 0 and
        far_size_ratio > 0.65 and  # Increased from 0.6
        oscillation_ratio < 0.3 and  # NEW: Low oscillation
        not far_bounced_back
    )

    # Slow swoosh indicators (rim bounce):
    slow_swoosh = (
        not near_continues_down or
        far_bottom_crossings == 0 or
        oscillation_ratio > 0.5 or  # NEW: High oscillation
        far_bounced_back
    )

    if fast_swoosh:
        return {'swoosh_quality': 'fast', 'made_confidence': 1.15}  # Reduced from 1.2
    elif slow_swoosh:
        return {'swoosh_quality': 'slow', 'missed_confidence': 1.25}  # Increased from 1.15
    else:
        return {'swoosh_quality': 'uncertain', 'confidence': 0.95}  # Reduced from 1.0
```

**Expected Impact**: Improve detection of rim bounces that eventually go through

---

### Phase 3: Conservative Confidence Formula (High Priority)

**Change 4**: Make confidence calculation less optimistic
```python
def calculate_fusion_confidence(self, near_shot: Dict, far_shot: Dict) -> Dict:
    # ... existing feature scoring ...

    # Calculate weighted score
    weighted_score = sum(weights[k] * scores[k] for k in weights)

    # NEW: More conservative formula
    # Old: final_confidence = base_conf * (0.7 + 0.6 * weighted_score)
    # New: Reduce multiplier, add penalty for low scores

    if weighted_score < 0.5:
        # Low feature agreement → reduce confidence significantly
        multiplier = 0.6 + 0.3 * weighted_score  # Max 0.75x at score=0.5
    elif weighted_score < 0.7:
        # Medium feature agreement → modest boost
        multiplier = 0.75 + 0.3 * weighted_score  # 0.75x - 0.96x
    else:
        # High feature agreement → good boost
        multiplier = 0.85 + 0.25 * weighted_score  # 0.935x - 1.1x

    final_confidence = base_conf * multiplier

    return {
        'confidence': min(0.98, final_confidence),  # Cap at 0.98 instead of 0.99
        'feature_scores': scores,
        'base_confidence': base_conf,
        'weighted_score': weighted_score,
        'multiplier': multiplier  # NEW: For debugging
    }
```

**Expected Impact**: Reduce overconfident "made" predictions

---

### Phase 4: Outcome Agreement Strictness (Medium Priority)

**Change 5**: Don't boost confidence when outcomes agree with low individual confidences
```python
def fuse_matched_pair(self, match: Dict) -> Dict:
    near = match['near_shot']
    far = match['far_shot']

    fusion_analysis = self.calculate_fusion_confidence(near, far)

    near_outcome = near.get('outcome', 'undetermined')
    far_outcome = far.get('outcome', 'undetermined')
    near_conf = near.get('detection_confidence', 0.5)
    far_conf = far.get('confidence', far.get('detection_confidence', 0.5))

    if near_outcome == far_outcome:
        final_outcome = near_outcome
        fusion_confidence = fusion_analysis['confidence']

        # NEW: If both angles agree but with low confidence, be skeptical
        if near_outcome == 'made' and (near_conf < 0.7 or far_conf < 0.7):
            fusion_confidence *= 0.85  # Reduce confidence on weak "made" agreement

        fusion_method = 'v2_agreement'
    else:
        final_outcome, fusion_confidence = self.resolve_disagreement(near, far, fusion_analysis)
        fusion_method = 'v2_feature_resolution'

    # ... rest of method ...
```

**Expected Impact**: Reduce false positives from weak "made" agreements

---

## Implementation Plan

### Step 1: Backup Current V2
```bash
cp dual_angle_fusion.py dual_angle_fusion_v2_original.py
git add dual_angle_fusion_v2_original.py
git commit -m "Backup V2 before implementing rim bounce fixes"
```

### Step 2: Implement Phase 1 (Conservative Rim Bounce)
- Update weights in `calculate_fusion_confidence()` (dual_angle_fusion.py:405)
- Add rim bounce penalty in `resolve_disagreement()` (dual_angle_fusion.py:452)

### Step 3: Implement Phase 3 (Conservative Confidence)
- Update confidence formula in `calculate_fusion_confidence()` (dual_angle_fusion.py:435)

### Step 4: Test V2.1 on Game 1
```bash
python3 dual_angle_fusion.py \
  --near_video input/09-23/game1_nearleft.mp4 \
  --far_video input/09-23/Game-1/game1_farright.mp4 \
  --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
  --near_model Uball_near_angle_shot_detection/runs/detect/basketball_yolo11n3/weights/best.pt \
  --far_model Uball_far_angle_shot_detection/runs/detect/basketball_yolo11n2/weights/best.pt \
  --offset_file offsets/09_23_game_1_offsets.json \
  --validate_accuracy \
  --angle RIGHT \
  --skip_video
```

**Expected Results**: Accuracy 92-93%, FP reduced to 2-3

### Step 5: If needed, implement Phase 2 (Swoosh Speed)
- Update `analyze_swoosh_speed()` (dual_angle_fusion.py:352)

### Step 6: If needed, implement Phase 4 (Outcome Strictness)
- Update `fuse_matched_pair()` (dual_angle_fusion.py:500)

### Step 7: Validate on other games
- Game 2 (09-22)
- Game 3 (09-23)

---

## Success Criteria

- [ ] Accuracy ≥ 93% on Game 1
- [ ] False positives ≤ 3
- [ ] Coverage ≥ 88%
- [ ] No increase in false negatives (keep at 0-1)
- [ ] Generalizes to Games 2 & 3

---

## File Locations

- **Main fusion script**: `dual_angle_fusion.py`
- **V2 plan**: `FUSION_V2_PLAN.md`
- **V2 test results**: `results/09-23(game1-R-)_5a0cf0b2-3964-454d-8d53-f797cc6282b7/`
- **V1 baseline results**: `results/09-23(game1-R-)_9ff4c5b5-e7cb-4c86-81b0-04b7c55f3e25/`

---

## Code Locations for Changes

| Change | Method | Line (approx) | File |
|--------|--------|---------------|------|
| **Phase 1: Weights** | `calculate_fusion_confidence()` | 405 | dual_angle_fusion.py |
| **Phase 1: Rim Penalty** | `resolve_disagreement()` | 452 | dual_angle_fusion.py |
| **Phase 2: Swoosh** | `analyze_swoosh_speed()` | 352 | dual_angle_fusion.py |
| **Phase 3: Confidence** | `calculate_fusion_confidence()` | 435 | dual_angle_fusion.py |
| **Phase 4: Outcome** | `fuse_matched_pair()` | 500 | dual_angle_fusion.py |

---

## Quick Start for Next Session

```bash
# Navigate to project
cd /Users/rohitkale/Cellstrat/GitHub_Repositories/Uball_dual_angle_fusion

# Review this plan
cat FUSION_V2_FIX_PLAN.md

# Backup current V2
cp dual_angle_fusion.py dual_angle_fusion_v2_original.py

# Implement Phase 1 & 3 fixes (see detailed code above)
# Edit dual_angle_fusion.py at lines 405, 435, 452

# Test V2.1
python3 dual_angle_fusion.py \
  --near_video input/09-23/game1_nearleft.mp4 \
  --far_video input/09-23/Game-1/game1_farright.mp4 \
  --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
  --near_model Uball_near_angle_shot_detection/runs/detect/basketball_yolo11n3/weights/best.pt \
  --far_model Uball_far_angle_shot_detection/runs/detect/basketball_yolo11n2/weights/best.pt \
  --offset_file offsets/09_23_game_1_offsets.json \
  --validate_accuracy \
  --angle RIGHT \
  --skip_video

# Compare results
# V2.0: 91.0% accuracy, 6 FP
# V2.1 Target: 93%+ accuracy, ≤3 FP
```

---

**Last Updated**: 2025-11-15
**Next Steps**: Implement Phase 1 & 3, test, iterate if needed
