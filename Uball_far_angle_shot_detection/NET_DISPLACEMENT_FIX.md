# Net Vertical Displacement Fix - Rim Bounce Discriminator

## Problem Identified

**After previous fixes:**
- False Negatives: 16 → 11 (✓ improved)
- False Positives: 6 → 11 (✗ worsened)
- Net result: 0% accuracy improvement

**Root Cause**: Relaxed "2+ crossings = made" rule catches rim bounces that came back OUT.

### False Positive Pattern:
```
1192.2s: 4 crossings, 2 points → MADE (but actually MISSED)
1644.2s: 5 crossings, 4 points, 248px bounce → MADE (but actually MISSED)
2001.2s: 6 crossings, 4 points → MADE (but actually MISSED)
```

**The Issue**: Ball can have:
- ✓ Multiple line crossings (bouncing up/down on rim)
- ✓ Points inside (ball in bbox while bouncing)
- ✓ NOT extreme bounce (166-274px < 300px threshold)
- ✗ But ball bounced back OUT, not through!

## The Discriminator: Net Vertical Displacement

**Key Insight**:
- **Made shots**: Ball goes DOWN through hoop → ends BELOW starting point
- **Missed shots**: Ball bounces OUT → ends at same level or HIGHER

### Implementation:

```python
# Calculate net vertical displacement
start_y = ball_positions[0][1]
end_y = ball_positions[-1][1]
net_vertical_displacement = end_y - start_y

# Positive = ball went down (MADE)
# Negative or small = ball bounced back up (MISSED)
```

### Updated Rules:

#### Rule 3: Made Shot (with net downward check)
```python
elif (line_crossings >= 2 or (line_crossings >= 1 and points_inside_with_depth >= 2))
     and net_vertical_displacement > 20:
    outcome = 'made'
```

**Requirements**:
- Line crossings: ≥2 OR (≥1 with 2+ points at depth)
- **AND** ball ends >20px lower than start

#### Rule 3x: Rim Bounce Back Out (NEW)
```python
elif (line_crossings >= 1 and points_inside >= 2)
     and net_vertical_displacement <= 20:
    outcome = 'missed'
    reason = 'rim_bounce_back_out'
```

**Catches**:
- Ball has crossings and points (looks like made)
- BUT net displacement ≤20px (didn't go down through)
- → Ball bounced on rim and came back out!

## Expected Impact

### False Positives (Should Fix):
Current false positives with crossings/points but bounced out:
- 1192.2s (4 crossings, 2 points)
- 1644.2s (5 crossings, 4 points)
- 2001.2s (6 crossings, 4 points)
- Others with rim bounces

**If these have net_disp ≤20px → will now be MISSED ✓**

### False Negatives (Should NOT Break):
Current correctly detected made shots:
- Should have net_disp >20px (ball went down through)
- Will continue to be classified as MADE ✓

### Expected Results:

**Conservative**:
- False Positives: 11 → **4-6** (fix 5-7 rim bounces)
- False Negatives: 11 (unchanged or +1-2)
- Accuracy: 56.1% → **65-68%**

**Optimistic**:
- False Positives: 11 → **2-4** (fix 7-9 rim bounces)
- False Negatives: 11 (unchanged)
- Accuracy: 56.1% → **68-72%**

## Physics Behind Solution

**Y-axis in images**: Increases downward
```
Y=0   ← Top of frame
  |
  v
Y=max ← Bottom of frame
```

**Made shot**:
```
Start: Y=300 (ball entering zone)
End:   Y=450 (ball exited zone below)
Net displacement: +150px (went down) → MADE ✓
```

**Rim bounce out**:
```
Start: Y=300 (ball entering zone)
End:   Y=310 (ball bounced back to similar height)
Net displacement: +10px (minimal down) → MISSED ✓
```

**Why 20px threshold?**:
- Small threshold (5-10px): Too sensitive, normal variance
- Large threshold (50px+): Might miss shallow made shots
- 20px: Reasonable minimum for ball to have gone "through"

## Test Cases

### Should Now Be MISSED (fix false positives):
- 1192.2s (4 crossings, likely net_disp ≤20px)
- 1644.2s (5 crossings, 248px bounce, likely net_disp ≤20px)
- 2001.2s (6 crossings, likely net_disp ≤20px)

### Should Still Be MADE (preserve correct):
- 362.8s (made with 251px bounce, net_disp >20px)
- 1615.7s (2 crossings made, net_disp >20px)
- All other correctly classified made shots

### Should Still Be MISSED (preserve correct):
- 37.7s (ball_in_front_of_hoop)
- All other correctly classified missed shots

## Summary

**Key Addition**: Net vertical displacement check
**Purpose**: Distinguish made shots (down through) from rim bounces (back out)
**Threshold**: Ball must end >20px lower than start for made shot
**Expected**: Reduce false positives by 60-80% while maintaining false negatives
