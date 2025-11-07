# Depth Check Implementation - Ball Size Analysis

## Problem Identified

**User's Brilliant Insight:**
> "Free throw issue is because ball's center passes through bounding box two times - even when missed, the first time it passes through as it comes straight in front of the hoop. We need to add ball-hoop size ratio because when ball is near hoop its size is less than when ball is not near hoop but seems to be overlapping (which will have bigger ball size)."

### The Core Issue:
In far-angle 2D projection:
- Ball **AT/THROUGH hoop** (farther from camera) = **smaller bbox**
- Ball **IN FRONT of hoop** (closer to camera) = **larger bbox**

When ball passes in front of the hoop:
- ✅ Line crossings detected (2D projection overlaps)
- ✅ Points inside hoop bbox (2D overlap)
- ❌ But ball is actually IN FRONT, not through!

**Example**: Shot 37.7s (GT: missed)
- Detected: 1 line crossing, 4 points inside → MADE ❌
- Reality: Ball passed IN FRONT of hoop
- Solution: Check ball size to determine depth

## Implementation

### 1. Track Ball Size
```python
# In update_shot_tracking()
self.ball_trajectory.append({
    'frame': self.frame_count,
    'position': ball['center'],
    'bbox': ball['bbox'],
    'ball_size': ball['width'] * ball['height'],  # Ball area for depth
    'in_zone': False
})

# In current_shot_sequence
'ball_sizes': [ball['width'] * ball['height']]  # Track all ball sizes
```

### 2. Calculate Average Ball Size
```python
# In classify_shot()
ball_sizes = shot_sequence.get('ball_sizes', [])
avg_ball_size = sum(ball_sizes) / len(ball_sizes) if ball_sizes else 0
```

### 3. Depth-Corrected Point Counting
```python
points_inside = 0
points_inside_with_depth = 0  # Depth-corrected count

for i, ball_center in enumerate(ball_positions):
    ball_x, ball_y = ball_center
    if hoop_x1 <= ball_x <= hoop_x2 and hoop_y1 <= ball_y <= hoop_y2:
        points_inside += 1

        # Depth check: ball should be similar or smaller when through hoop
        if ball_sizes and i < len(ball_sizes):
            ball_size = ball_sizes[i]
            # If ball is >30% larger than average → IN FRONT of hoop
            if avg_ball_size > 0 and ball_size <= avg_ball_size * 1.3:
                points_inside_with_depth += 1
```

**Logic**:
- Ball at hoop depth should be ≤ average size
- Ball >30% larger = closer to camera = IN FRONT

### 4. Updated Classification Rules

#### Rule 3: Made Shot (Depth-Corrected)
```python
elif line_crossings >= 1 and points_inside_with_depth >= 2:
    outcome = 'made'
    reason = f'trajectory_through_hoop ({line_crossings} crossings, {points_inside_with_depth} points at depth)'
```

#### Rule 3b: Ball In Front of Hoop (NEW)
```python
elif line_crossings >= 1 and points_inside >= 2 and points_inside_with_depth < 2:
    outcome = 'missed'
    reason = f'ball_in_front_of_hoop ({points_inside} points but only {points_inside_with_depth} at correct depth)'
```

**This catches**: Shots with line crossings + points inside but ball too large (in front)

### 5. Relaxed Ratio Threshold
```python
# Before (too strict):
elif upward > 100 and up_down_ratio > 1.0:

# After (with depth check handling false positives):
elif upward > 100 and up_down_ratio > 1.15:
```

Depth check handles false positives better, so we can relax ratio to reduce false negatives.

## Expected Impact

### False Positives (Missed→Made)
**Previous**: 7 errors
- Example: 37.7s with 4 points inside but ball IN FRONT

**After Depth Check**: Should catch these!
- Balls passing in front will have larger size
- `points_inside_with_depth` will be low
- Classified as MISSED via Rule 3b

### False Negatives (Made→Missed)
**Previous**: 18 errors (too strict with ratio 1.0)
- Many made shots with ratio 1.00-1.15 rejected

**After Relaxed Ratio**: Should improve!
- Ratio threshold 1.15 allows more legitimate made shots
- Depth check prevents false positives

## Physics Behind the Solution

**Perspective Projection**:
```
Object size in image ∝ 1 / distance_from_camera

Ball at hoop (far):  size = k / d_far  → smaller
Ball in front (near): size = k / d_near → larger
```

**Depth Estimation**:
- Average ball size ≈ typical distance from camera
- Ball >30% larger → significantly closer → in front of hoop
- Ball ≤average → at or behind hoop → legitimate shot

## Test Case: 37.7s

**Ground Truth**: MISSED (free throw that bounced off front of rim)

**Before Depth Check**:
- 1 line crossing ✓
- 4 points inside ✓
- 215px rim bounce
- Result: MADE ❌

**After Depth Check**:
- 1 line crossing ✓
- 4 points inside (2D)
- But ball size likely >1.3x average when "inside"
- points_inside_with_depth = 0-1 (< 2)
- Result: MISSED (ball_in_front_of_hoop) ✓

## Summary

**Key Innovation**: Use ball bounding box size as depth proxy
**Core Insight**: Larger ball = closer to camera = in front of hoop
**Implementation**: Filter "points inside" by depth using ball size ratio
**Benefit**: Catch false positives from 2D projection overlap

**Expected Results**:
- False Positives: 7 → 0-2 (depth check catches front passes)
- False Negatives: 18 → 8-10 (relaxed ratio helps)
- Overall Accuracy: 50.9% → **65-70%**
