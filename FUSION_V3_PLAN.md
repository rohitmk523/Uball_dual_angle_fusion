# Fusion V3 Plan: Advanced Cross-Angle Validation

## Executive Summary

**Current V2.2 Performance**: 91.97% average accuracy (Game1: 92.6%, Game2: 89.7%, Game3: 93.6%)
**Target V3 Performance**: >95% accuracy
**Gap to close**: ~3-5% (approximately 10-15 errors across 3 games)

## Critical Finding from V2.2 Error Analysis

**89.5% of errors (17/19) occur when angles DISAGREE on outcome**

This is the key insight: When both angles agree, fusion is very accurate (only 2 errors). The problem is the disagreement resolution logic choosing the wrong angle.

### V2.2 Error Breakdown
- **Total errors**: 19
  - False Positives (called made, was missed): 10
  - False Negatives (called missed, was made): 9
- **Agreement errors**: 2 (10.5%) - Both angles wrong, indicates underlying detection issues
- **Disagreement errors**: 17 (89.5%) - **THIS IS WHERE V3 MUST IMPROVE**

## Root Cause Analysis

### Pattern 1: Far Angle Line Intersection Over-Trust
**Observed in 7+ errors**

When far angle detects `line_intersection=1.0` (ball crossed top line), fusion heavily favors far angle's "made" call, even when:
- Near angle says "missed" with high confidence
- No other features support "made"
- Ground truth confirms it was actually missed

**Examples**:
- Game 1 @ 1549.7s: Near=missed (0.898), Far=made (0.950), line_cross=1.0 → Fusion chose "made" (WRONG)
- Game 1 @ 1938.3s: Near=missed (0.891), Far=made (0.950), line_cross=1.0 → Fusion chose "made" (WRONG)

**Why this happens**: Far angle's top-down view sees ball crossing rim top line, but this can happen on:
- Rim bounces that roll in then out
- Near-rim misses that touch the rim
- Ball hitting front rim and bouncing back

### Pattern 2: Near Angle Missed Detection
**Observed in 5+ errors**

When near angle detects "made" but far angle says "missed", fusion sometimes incorrectly chooses "missed":
- Game 1 @ 25.8s: Near=made (0.886), Far=missed (0.900) → Fusion chose "missed" (WRONG)
- Game 2 @ 688.8s: Near=made, Far=missed → Fusion chose "missed" (WRONG)

**Why this happens**: Current V2.2 weights rim_bounce_agreement at 30%, and if far angle thinks it's a miss with no line cross, it overpowers near angle's detection.

### Pattern 3: Confidence Doesn't Reflect Angle Reliability
Both near and far angles have similar confidence scores (0.85-0.95), but their **reliability varies by shot type**:
- **Far angle is more reliable for**: Clean makes with clear arc, rim-out bounces
- **Near angle is more reliable for**: Swishes, close-rim makes, bank shots

V2.2 treats all high-confidence detections equally, missing this nuance.

## V3 Strategy: Angle-Specific Reliability Modeling

###Core Concept
Add **context-aware angle weighting** that dynamically adjusts which angle to trust based on shot characteristics.

### V3.1: Shot Type Classification

Add shot type classifier to each detection:

```python
shot_types = {
    'clean_swish': {
        'indicators': {'line_intersection': 1.0, 'swoosh_speed': >0.7, 'rim_bounce': False},
        'reliable_angle': 'both',  # Both angles should agree
        'confidence_boost': 1.2
    },
    'rim_make': {
        'indicators': {'line_intersection': 1.0, 'swoosh_speed': 0.3-0.7, 'rim_bounce': True},
        'reliable_angle': 'near',  # Near better at rim contact
        'confidence_boost_near': 1.3,
        'confidence_boost_far': 0.8
    },
    'rim_bounce_out': {
        'indicators': {'line_intersection': 0.5-1.0, 'bounced_back_out': True},
        'reliable_angle': 'near',  # Near sees bounce better
        'confidence_boost_near': 1.4,
        'confidence_boost_far': 0.7
    },
    'clean_miss': {
        'indicators': {'line_intersection': 0.0, 'rim_bounce': False},
        'reliable_angle': 'both',
        'confidence_boost': 1.1
    },
    'near_rim_miss': {
        'indicators': {'line_intersection': 0.3-0.7, 'overlap_quality': >0.5, 'rim_bounce': True},
        'reliable_angle': 'near',  # Near distinguishes rim touch vs make
        'confidence_boost_near': 1.3,
        'confidence_boost_far': 0.8
    }
}
```

### V3.2: Enhanced Disagreement Resolution

When angles disagree, use shot type to weight votes:

```python
def resolve_disagreement_v3(near_shot, far_shot, fusion_scores):
    # Classify shot type
    shot_type = classify_shot_type(fusion_scores['feature_scores'], near_shot, far_shot)

    # Get base vote weights
    near_vote = near_conf * (1.0 + made_feature_support if near_out=='made' else 1.0 + miss_feature_support)
    far_vote = far_conf * (1.0 + made_feature_support if far_out=='made' else 1.0 + miss_feature_support)

    # Apply shot-type-specific reliability boosts
    if shot_type['reliable_angle'] == 'near':
        near_vote *= shot_type['confidence_boost_near']
        far_vote *= shot_type.get('confidence_boost_far', 1.0)
    elif shot_type['reliable_angle'] == 'far':
        far_vote *= shot_type['confidence_boost_far']
        near_vote *= shot_type.get('confidence_boost_near', 1.0)

    # Special case: Far says "made" with line_cross=1.0, but near says "missed"
    # Check if this looks like rim bounce out
    if far_out == 'made' and near_out == 'missed':
        if fusion_scores['feature_scores'].get('line_intersection', 0) >= 0.8:
            # Far detected line cross, but near disagrees
            # Check for rim bounce indicators
            if near_shot.get('is_rim_bounce') or far_shot.get('bounced_back_out'):
                # Likely rim bounce - trust near angle more
                near_vote *= 1.5
                far_vote *= 0.6
            elif fusion_scores['feature_scores'].get('swoosh_speed', 0) < 0.5:
                # Slow swoosh suggests rim contact - trust near
                near_vote *= 1.3
                far_vote *= 0.7

    # Return winner
    return near_out if near_vote > far_vote else far_out
```

### V3.3: Cross-Angle Consistency Checks

Add validation layer that flags suspicious cases:

```python
def cross_angle_validation(near_shot, far_shot, fused_outcome):
    flags = []

    # Flag 1: Far says made with line cross, but near shows rim bounce
    if (far_shot['outcome'] == 'made' and
        far_shot.get('valid_top_crossings', 0) > 0 and
        near_shot.get('is_rim_bounce', False)):
        flags.append({
            'type': 'rim_bounce_vs_line_cross',
            'recommended_outcome': 'missed',
            'confidence_penalty': 0.7,
            'reason': 'Far detected line cross but near shows rim bounce - likely bounced in then out'
        })

    # Flag 2: High confidence disagreement with no clear physical reason
    if (abs(near_shot['confidence'] - far_shot['confidence']) < 0.1 and
        near_shot['outcome'] != far_shot['outcome'] and
        not near_shot.get('is_rim_bounce') and
        not far_shot.get('bounced_back_out')):
        flags.append({
            'type': 'unexplained_high_conf_disagreement',
            'recommended_action': 'use_feature_tiebreaker',
            'confidence_penalty': 0.85
        })

    # Apply flags
    for flag in flags:
        if flag.get('recommended_outcome'):
            return flag['recommended_outcome'], fused_confidence * flag['confidence_penalty']

    return fused_outcome, fused_confidence
```

### V3.4: Feature Weight Rebalancing

Based on error analysis, adjust V2.2 weights:

**Current V2.2 weights**:
```python
{
    'outcome_agreement': 0.25,
    'rim_bounce_agreement': 0.30,
    'entry_angle_consistency': 0.15,
    'swoosh_speed': 0.15,
    'overlap_quality': 0.05,
    'line_intersection': 0.15
}
```

**Proposed V3 weights** (for disagreement cases):
```python
{
    'outcome_agreement': 0.20,      # N/A in disagreement, reduce
    'rim_bounce_agreement': 0.35,   # INCREASE - critical for rim bounce detection
    'entry_angle_consistency': 0.12,
    'swoosh_speed': 0.18,           # INCREASE - good indicator of clean vs rim contact
    'overlap_quality': 0.05,
    'line_intersection': 0.10       # DECREASE - over-trusted in V2.2
}
```

### V3.5: Near Angle Overlap Refinement

Enhance near angle's overlap calculation to better distinguish:
- **True makes**: Ball overlaps rim, then disappears (goes through)
- **Rim bounces**: Ball overlaps rim, stays visible (bounces out)
- **Near misses**: Ball briefly overlaps rim edge (touches front/side)

```python
def enhanced_overlap_scoring(overlap_frames, ball_trajectory):
    # Track ball visibility after max overlap
    max_overlap_frame = find_max_overlap(overlap_frames)

    # Check frames after max overlap
    post_overlap_visibility = check_ball_visibility(max_overlap_frame + 1, max_overlap_frame + 10)

    if post_overlap_visibility < 0.3:
        # Ball disappeared - likely went through
        return 'made', 0.9
    elif post_overlap_visibility > 0.7:
        # Ball still very visible - likely bounced out or missed
        return 'missed', 0.8
    else:
        # Ambiguous - use other features
        return 'uncertain', 0.5
```

## Implementation Plan

### Phase 1: Shot Type Classification (Week 1)
1. Implement shot type classifier
2. Test on existing V2.2 results (no re-detection needed)
3. Validate shot type assignments match visual inspection

### Phase 2: Enhanced Disagreement Resolution (Week 1-2)
1. Implement V3.2 logic with reliability boosts
2. Implement V3.3 cross-angle validation
3. Test on all 19 error cases - target: fix 12-15 errors

### Phase 3: Feature Rebalancing (Week 2)
1. Adjust feature weights
2. Test impact on agreement cases (ensure no regression)
3. Fine-tune based on results

### Phase 4: Near Angle Refinement (Week 2-3)
1. Enhance overlap scoring logic
2. Re-run near angle detection with updated logic
3. Re-run fusion with new near detections

### Phase 5: Validation & Iteration (Week 3-4)
1. Run V3 on all 3 games
2. Analyze new errors
3. Iterate until >95% accuracy achieved

## Expected Impact

### Conservative Estimate
- Fix 12/17 disagreement errors → 5 errors remaining
- Agreement errors stay at 2 (requires underlying detection improvements)
- **Total errors: 7** → **Accuracy: 96.3%**

### Optimistic Estimate
- Fix 15/17 disagreement errors → 2 errors remaining
- Fix 1/2 agreement errors with Phase 4 improvements → 1 error remaining
- **Total errors: 3** → **Accuracy: 98.4%**

## Risk Mitigation

1. **Phase-by-phase testing**: Each phase tested independently to catch regressions early
2. **Preserve V2.2**: Keep V2.2 code intact, V3 is additive
3. **A/B comparison**: Run V2.2 and V3 side-by-side on same detections
4. **Visual validation**: Manually inspect fixed errors to ensure they're truly correct

## Success Metrics

- **Primary**: Overall accuracy >95% across all 3 games
- **Secondary**:
  - Disagreement error rate <5% (currently 89.5%)
  - False positive rate ~= False negative rate (balanced)
  - No regression on agreement cases

## Next Steps

1. User approval of V3 plan
2. Begin Phase 1 implementation
3. Create V3 branch for development
4. Set up automated testing pipeline
