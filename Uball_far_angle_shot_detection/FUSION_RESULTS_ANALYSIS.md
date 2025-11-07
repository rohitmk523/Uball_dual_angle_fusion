# Fusion Results Analysis - 09-22 Game-3

## Critical Finding: Far Angle is WORSE than Near Angle

**Near Angle Performance**: 89.61% (69/77 correct)
**Far Angle Performance**: 64.94% (50/77 correct)
**Fusion Performance**: 67.53% (52/77 correct)

**Result**: Fusion DECREASED accuracy by overriding good near angle detections with bad far angle ones.

## Problem with Current Fusion Strategy

### Original Assumption (WRONG):
- Near angle: ~89% matched accuracy with 8-9 errors per game
- Far angle would be better at specific error-prone patterns

### Reality:
- Near angle: 89.61% (excellent!)
- Far angle: 64.94% (**25% worse!**)
- Far angle is not a specialist - it's just worse overall

## Fusion Rule Breakdown

### Rules That Broke Things:

**1. 3pt_insufficient_overlap_far_override** (24 shots, 62.5% accurate)
- Applied to ALL 3PT shots with near confidence < 0.85
- But near angle was 89.61% accurate overall!
- Broke 9 correct near angle 3PT detections

**2. weighted_fusion_moderate_confidence** (13 shots, 61.5% accurate)
- Applied to moderate confidence shots (0.70-0.85)
- Gave 65% weight to far angle for 3PT
- Broke multiple correct near angle detections

**3. layup_occlusion_far_angle_correction** (4 shots, 0% accurate)
- **100% failure rate!**
- ALL 4 layup overrides were wrong
- Near angle was correct, far angle broke them all

**4. steep_entry_far_angle_override** (5 shots, 20% accurate)
- Only 1/5 correct
- Fixed 1 error but broke 4 correct detections

### Rules That Worked:

**1. near_angle_high_confidence_dominant** (3 shots, 100% accurate)
- Preserved high-confidence near angle detections
- This is the right approach!

**2. layup_confirmed_both_angles_cautious** (12 shots, 91.7% accurate)
- Both angles agreed - high accuracy
- Cautious approach works

**3. far_angle_higher_confidence_fallback** (9 shots, 88.9% accurate)
- Only when far angle had higher confidence
- This is reasonable

## Why Far Angle Performed Poorly

Need to investigate:
1. Different hoop position/perspective in far angle?
2. Far angle parameters need tuning for these games?
3. Far angle better suited for different shot types?

## Revised Fusion Strategy

### Core Principle: PRESERVE Near Angle (it's good!)

**Conservative Override Rules**:

1. **Only override if**:
   - Near confidence < 0.70 AND far confidence > 0.85
   - Confidence difference > 0.20 in favor of far angle

2. **Agreement boost**:
   - When both angles agree with high confidence → boost confidence

3. **Low confidence delegation**:
   - When near confidence < 0.65 → use far angle as fallback

4. **NO pattern-based overrides** unless far angle proves better for that pattern

## Next Steps

1. **Analyze far angle errors** - understand why it's performing poorly
2. **Tune far angle parameters** if needed
3. **Re-implement conservative fusion** with minimal overrides
4. **Test on 09-23 Game-1** to see if pattern holds

## Expected Results with Conservative Fusion

**Target**: Preserve 89.61% near angle accuracy, maybe improve to 90-92%

**Approach**:
- Fix 2-3 low-confidence near angle errors
- Don't break any high-confidence correct detections
- Net improvement: +1-3 percentage points (not -22!)

## Lesson Learned

**Don't override a 90% accurate detector with a 65% accurate one!**

The fusion strategy was based on assumption that far angle would be better at specific patterns. In reality, far angle is worse across the board for this game pair. Need to:

1. Understand WHY far angle is worse
2. Fix far angle issues OR
3. Use extremely conservative fusion that barely touches near angle
