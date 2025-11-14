# Far Angle Shot Detection V5 - Enhancement Plan

**Date:** 2025-11-13
**Current Version:** V4 (Line Intersection Logic)
**Target:** V5 (Multi-Factor Enhanced Detection)
**Goal:** Increase accuracy from ~70% to 85%+ (matching near angle performance)

---

## ⚠️ **V5 TEST RESULTS - FAILED** ⚠️

**Test Date:** 2025-11-13
**Status:** REVERTED TO V4

### Test Results (Full Game 1):

| Metric | V4 (Current) | V5 (Tested) | Change |
|--------|-------------|------------|--------|
| **Matched shots accuracy** | **80.56%** | **77.78%** | **-2.78%** ❌ |
| Matched correct | 58 | 56 | -2 |
| Matched incorrect | 14 | 16 | +2 |
| Overall accuracy | 49.57% | 47.86% | -1.71% |

### Conclusion:
V5 multi-factor weighted scoring **deteriorated accuracy by 2.78%** instead of improving it. The added features (entry angle, downward consistency, bbox overlap, post-hoop analysis, weighted decision) caused more false positives and incorrect classifications.

**Action Taken:** Immediately reverted to V4 backup.

**Lesson Learned:** Near angle features do not directly translate to far angle due to different viewing perspectives and detection challenges.

---

## Original Plan (Not Implemented)

## 📊 Current Performance Analysis

### Game Results Comparison (09-23 Games - Far Right vs Near Left)

| Metric | Far Angle (FR) | Near Angle (NL) | Gap |
|--------|----------------|-----------------|-----|
| **Game 1** | | | |
| Detected Shots | 117 | 130 | -13 |
| Ground Truth | 77 | 77 | 0 |
| Accuracy | ~66% | ~88% | -22% |
| **Game 2** | | | |
| Detected Shots | TBD | TBD | TBD |
| **Game 3** | | | |
| Detected Shots | 119 | TBD | TBD |

### Current Far Angle Features (V4)

**Detection Features:**
```json
{
  "timestamp_seconds": 11.0,
  "start_frame": 305,
  "end_frame": 352,
  "outcome": "missed",
  "outcome_reason": "no_top_crossing (never entered from top)",
  "confidence": 0.9,
  "valid_top_crossings": 0,
  "valid_bottom_crossings": 0,
  "avg_size_ratio": 0,
  "bounced_back_out": false,
  "bounce_upward_pixels": 0,
  "frames_in_zone": 44,
  "spatial_features": {
    "ball_hoop_horizontal_offset": -76.0,
    "ball_hoop_vertical_offset": 32.5,
    "ball_distance_to_hoop": 82.66,
    "ball_moving_left": false,
    "ball_moving_right": false,
    "lateral_velocity": 0.6,
    "ball_size": 24
  }
}
```

### Near Angle Features (V3) - What We're Missing

**Additional Features in Near Angle:**
```json
{
  "entry_angle": 58.57,  // ← MISSING!
  "max_overlap_percentage": 98.51,  // ← MISSING!
  "avg_overlap_percentage": 54.44,  // ← MISSING!
  "frames_with_100_percent": 0,  // ← MISSING!
  "frames_with_95_percent": 1,  // ← MISSING!
  "frames_with_90_percent": 3,  // ← MISSING!
  "weighted_overlap_score": 1.8,  // ← MISSING!
  "total_overlaps_in_sequence": 26,  // ← MISSING!
  "is_rim_bounce": false,
  "rim_bounce_confidence": 0.0,
  "post_hoop_analysis": {  // ← MISSING!
    "ball_continues_down": false,
    "ball_bounces_back": false,
    "downward_movement": -84,
    "upward_movement": 84,
    "downward_consistency": 0.44,
    "upward_consistency": 0.48
  },
  "detection_method": "enhanced_multi_factor_v3"
}
```

---

## 🎯 New Features for V5

### Priority 1: Entry Angle Calculation ⭐⭐⭐
**Impact:** HIGH (+5-8% accuracy)

**What:** Calculate the angle at which the ball enters the hoop zone
- Steep angle (60°-90°) = more likely made
- Shallow angle (<40°) = more likely missed or rim bounce

**Implementation:**
```python
def _calculate_entry_angle(self, ball_positions, hoop_center):
    """Calculate ball entry angle relative to hoop (vertical = 90°, horizontal = 0°)"""
    if len(ball_positions) < 5:
        return None

    # Get last 5 positions before hoop crossing
    recent_points = ball_positions[-5:]

    # Calculate velocity vector
    first_point = recent_points[0]
    last_point = recent_points[-1]

    dx = last_point[0] - first_point[0]
    dy = last_point[1] - first_point[1]  # Positive = downward

    # Calculate angle from horizontal (0° = horizontal, 90° = straight down)
    if dx == 0:
        angle = 90.0 if dy > 0 else -90.0
    else:
        angle_rad = math.atan2(dy, abs(dx))
        angle = math.degrees(angle_rad)

    return abs(angle)
```

**Where to add:** `simple_line_intersection_test.py` lines 230-384 in `classify_shot()`

---

### Priority 2: Downward Consistency Scoring ⭐⭐⭐
**Impact:** HIGH (+4-6% accuracy)

**What:** Track how consistently the ball moves downward after crossing the hoop
- High consistency (>70%) = likely made
- Low consistency or upward movement = likely missed/rim bounce

**Implementation:**
```python
def _calculate_downward_consistency(self, ball_positions, start_idx):
    """Calculate how consistently ball moves downward after crossing"""
    if start_idx >= len(ball_positions) - 1:
        return 0.0

    # Get Y positions after crossing
    y_positions = [pos[1] for pos in ball_positions[start_idx:]]

    if len(y_positions) < 2:
        return 0.0

    # Calculate frame-to-frame deltas
    deltas = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]

    # Count downward movements (positive Y = downward)
    downward_count = sum(1 for d in deltas if d > 1)

    return downward_count / len(deltas) if deltas else 0.0
```

**Where to add:** `simple_line_intersection_test.py` after line 309

---

### Priority 3: Bbox Overlap Tracking ⭐⭐
**Impact:** MEDIUM (+3-5% accuracy)

**What:** Track how many frames the ball bbox overlaps with hoop bbox
- More frames with high overlap = higher confidence made
- Similar to near angle's frames_with_100%, frames_with_95%

**Implementation:**
```python
def _calculate_bbox_overlap_frames(self, ball_positions, ball_sizes, hoop_bbox):
    """Calculate frames with different overlap percentages"""
    overlap_frames = {
        '100': 0,
        '95': 0,
        '90': 0,
        '80': 0
    }

    for i, ball_center in enumerate(ball_positions):
        if i >= len(ball_sizes):
            continue

        ball_size = ball_sizes[i]
        ball_radius = int(np.sqrt(ball_size) / 2)

        # Create ball bbox from center and size
        ball_bbox = (
            ball_center[0] - ball_radius,
            ball_center[1] - ball_radius,
            ball_center[0] + ball_radius,
            ball_center[1] + ball_radius
        )

        # Calculate overlap
        overlap_pct = self._check_box_overlap(ball_bbox, hoop_bbox)

        if overlap_pct >= 100:
            overlap_frames['100'] += 1
        if overlap_pct >= 95:
            overlap_frames['95'] += 1
        if overlap_pct >= 90:
            overlap_frames['90'] += 1
        if overlap_pct >= 80:
            overlap_frames['80'] += 1

    return overlap_frames

def _check_box_overlap(self, ball_bbox, hoop_bbox):
    """Calculate overlap percentage between ball and hoop bounding boxes"""
    ball_x1, ball_y1, ball_x2, ball_y2 = ball_bbox
    hoop_x1, hoop_y1, hoop_x2, hoop_y2 = hoop_bbox

    # Calculate intersection area
    overlap_x = max(0, min(ball_x2, hoop_x2) - max(ball_x1, hoop_x1))
    overlap_y = max(0, min(ball_y2, hoop_y2) - max(ball_y1, hoop_y1))
    intersection_area = overlap_x * overlap_y

    # Calculate ball area
    ball_area = (ball_x2 - ball_x1) * (ball_y2 - ball_y1)

    # Return overlap percentage
    if ball_area > 0:
        overlap_percentage = (intersection_area / ball_area) * 100
        return overlap_percentage
    return 0
```

**Where to add:** `simple_line_intersection_test.py` after line 169

---

### Priority 4: Post-Hoop Trajectory Analysis ⭐⭐
**Impact:** MEDIUM (+2-4% accuracy)

**What:** Analyze ball behavior after crossing hoop boundaries
- Continues down = made
- Bounces up = rim bounce (missed)
- Track downward/upward movement and consistency

**Implementation:**
```python
def _analyze_post_hoop_trajectory(self, ball_positions, crossing_idx):
    """Analyze ball behavior after hoop interaction"""
    if crossing_idx >= len(ball_positions) - 1:
        return {
            'ball_continues_down': False,
            'ball_bounces_back': False,
            'downward_movement': 0,
            'upward_movement': 0,
            'downward_consistency': 0.0,
            'upward_consistency': 0.0
        }

    # Get Y positions after crossing
    y_positions = [pos[1] for pos in ball_positions[crossing_idx:]]

    first_y = y_positions[0]
    last_y = y_positions[-1]

    # Calculate movement
    downward_movement = last_y - first_y  # Positive = downward
    upward_movement = first_y - last_y    # Positive = upward

    # Calculate consistency
    if len(y_positions) >= 3:
        deltas = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]
        positive_deltas = sum(1 for d in deltas if d > 2)  # Downward
        negative_deltas = sum(1 for d in deltas if d < -2)  # Upward

        total_deltas = len(deltas)
        downward_consistency = positive_deltas / total_deltas if total_deltas > 0 else 0
        upward_consistency = negative_deltas / total_deltas if total_deltas > 0 else 0
    else:
        downward_consistency = 0.5
        upward_consistency = 0.5

    return {
        'ball_continues_down': downward_movement > 15 and downward_consistency > 0.6,
        'ball_bounces_back': upward_movement > 15 and upward_consistency > 0.5,
        'downward_movement': downward_movement,
        'upward_movement': upward_movement,
        'downward_consistency': downward_consistency,
        'upward_consistency': upward_consistency
    }
```

**Where to add:** `simple_line_intersection_test.py` after line 313

---

### Priority 5: Multi-Factor Weighted Decision ⭐⭐⭐
**Impact:** HIGH (+5-7% accuracy)

**What:** Replace binary decision logic with weighted multi-factor scoring
- Combine all factors (angle, consistency, crossings, overlap, trajectory)
- Score-based decision (made if score >= threshold)

**Implementation:**
```python
def _calculate_weighted_decision_score(self, factors):
    """Calculate weighted score for shot outcome (0-100)"""
    score = 0
    max_score = 100

    # Factor 1: Boundary Crossings (30 points)
    if factors['valid_top_crossings'] >= 2:
        score += 30
    elif factors['valid_top_crossings'] >= 1:
        score += 20

    if factors['valid_bottom_crossings'] >= 2:
        score += 10
    elif factors['valid_bottom_crossings'] >= 1:
        score += 5

    # Factor 2: Entry Angle (20 points)
    if factors.get('entry_angle'):
        if factors['entry_angle'] >= 60:  # Very steep
            score += 20
        elif factors['entry_angle'] >= 45:  # Steep
            score += 15
        elif factors['entry_angle'] >= 30:  # Moderate
            score += 10
        else:  # Shallow
            score += 5

    # Factor 3: Downward Consistency (20 points)
    if factors.get('downward_consistency'):
        if factors['downward_consistency'] >= 0.8:
            score += 20
        elif factors['downward_consistency'] >= 0.6:
            score += 15
        elif factors['downward_consistency'] >= 0.4:
            score += 10

    # Factor 4: Bbox Overlap (15 points)
    overlap_frames = factors.get('overlap_frames', {})
    if overlap_frames.get('100', 0) >= 3:
        score += 15
    elif overlap_frames.get('95', 0) >= 3:
        score += 12
    elif overlap_frames.get('90', 0) >= 3:
        score += 9
    elif overlap_frames.get('80', 0) >= 3:
        score += 6

    # Factor 5: Size Ratio Quality (10 points)
    ideal_ratio = (0.18 + 0.28) / 2  # 0.23
    ratio_deviation = abs(factors['avg_size_ratio'] - ideal_ratio)
    if ratio_deviation <= 0.02:
        score += 10
    elif ratio_deviation <= 0.04:
        score += 7
    elif ratio_deviation <= 0.06:
        score += 4

    # Factor 6: Post-Hoop Analysis (5 points)
    post_hoop = factors.get('post_hoop_analysis', {})
    if post_hoop.get('ball_continues_down'):
        score += 5

    # Penalty: Rim Bounce (-30 points)
    if factors.get('bounced_back_out'):
        score -= 30

    # Penalty: Upward Bounce (-20 points)
    if post_hoop.get('ball_bounces_back'):
        score -= 20

    return score, max_score

# Decision logic:
score, max_score = self._calculate_weighted_decision_score(factors)

if score >= 60:
    outcome = 'made'
    confidence = min(0.95, score / max_score + 0.35)
elif score >= 40:
    outcome = 'made'
    confidence = 0.70
else:
    outcome = 'missed'
    confidence = min(0.90, (max_score - score) / max_score + 0.40)
```

**Where to add:** `simple_line_intersection_test.py` replace lines 336-370 in `classify_shot()`

---

## 📝 Implementation Checklist

### Phase 1: Add Feature Calculations (Day 1)
- [ ] Add `_calculate_entry_angle()` method
- [ ] Add `_calculate_downward_consistency()` method
- [ ] Add `_calculate_bbox_overlap_frames()` method
- [ ] Add `_check_box_overlap()` method
- [ ] Add `_analyze_post_hoop_trajectory()` method

### Phase 2: Enhanced Decision Logic (Day 1)
- [ ] Add `_calculate_weighted_decision_score()` method
- [ ] Update `classify_shot()` to use weighted scoring
- [ ] Add new fields to shot output JSON

### Phase 3: Testing (Day 2)
- [ ] Test on Game 1 (first 5 minutes)
- [ ] Test on incorrect timestamps
- [ ] Run full Game 1
- [ ] Compare with ground truth
- [ ] Adjust thresholds if needed

### Phase 4: Validation (Day 2-3)
- [ ] Run all 3 games
- [ ] Compare with near angle accuracy
- [ ] Document improvements
- [ ] Finalize V5

---

## 🧪 Testing Commands

### Step 1: Test First 5 Minutes (Quick Validation)

**Game 1:**
```bash
cd Uball_far_angle_shot_detection

python main.py --action video \
    --video_path input/09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 0 \
    --end_time 300 \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --validate_accuracy \
    --angle RIGHT

# Check results
LATEST=$(ls -t results/ | head -1)
cat "results/$LATEST/accuracy_analysis.json" | jq '.metrics'
```

**Game 2:**
```bash
python main.py --action video \
    --video_path input/09-23/Game-2/game2_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 0 \
    --end_time 300 \
    --game_id 86c25ddc-d64b-4ffe-93c7-6e102c8c17d6 \
    --validate_accuracy \
    --angle RIGHT
```

**Game 3:**
```bash
python main.py --action video \
    --video_path input/09-23/Game-3/game3_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --start_time 0 \
    --end_time 300 \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle RIGHT
```

### Step 2: Test Problematic Timestamps

**Find timestamps with low confidence or misclassifications:**
```bash
# Game 1 - Find incorrect detections
cat results/09-23\(1-FR\)_*/accuracy_analysis.json | jq '.matches | .incorrect_made, .incorrect_missed' | head -20

# Test specific timestamps (example)
python simple_line_intersection_test.py \
    --mode test \
    --video input/09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --timestamps "11.0,25.8,45.2"
```

### Step 3: Run Full Games

**Game 1 (Full):**
```bash
python main.py --action video \
    --video_path input/09-23/Game-1/game1_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --validate_accuracy \
    --angle RIGHT

# Results will be in: results/09-23(1-FR)_<uuid>/
```

**Game 2 (Full):**
```bash
python main.py --action video \
    --video_path input/09-23/Game-2/game2_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id 86c25ddc-d64b-4ffe-93c7-6e102c8c17d6 \
    --validate_accuracy \
    --angle RIGHT
```

**Game 3 (Full):**
```bash
python main.py --action video \
    --video_path input/09-23/Game-3/game3_farright.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --game_id a3c9c041-6762-450a-8444-413767bb6428 \
    --validate_accuracy \
    --angle RIGHT
```

---

## 📊 Expected Improvements

### Current (V4):
- Accuracy: ~70%
- Precision: ~60%
- Recall: ~75%
- F1 Score: ~67%
- False Positive Rate: ~30%

### Target (V5):
- Accuracy: **85%+** (+15%)
- Precision: **80%+** (+20%)
- Recall: **85%+** (+10%)
- F1 Score: **82%+** (+15%)
- False Positive Rate: **<15%** (-15%)

### Feature-Specific Expected Gains:
1. Entry Angle: +5-8%
2. Downward Consistency: +4-6%
3. Bbox Overlap Tracking: +3-5%
4. Post-Hoop Analysis: +2-4%
5. Weighted Decision: +5-7%

**Total Expected Gain: +19-30%** (compounding effects may be lower, realistic: +15-20%)

---

## 🔍 Comparison Matrix

| Feature | V4 (Current) | V5 (Planned) | Near Angle V3 |
|---------|-------------|--------------|---------------|
| Boundary Crossing | ✅ | ✅ | ❌ |
| Size Ratio Validation | ✅ | ✅ | ❌ |
| Rim Bounce Detection | ✅ Basic | ✅ Enhanced | ✅ Multi-factor |
| Entry Angle | ❌ | ✅ NEW | ✅ |
| Downward Consistency | ❌ | ✅ NEW | ✅ |
| Bbox Overlap Tracking | ❌ | ✅ NEW | ✅ |
| Post-Hoop Analysis | ❌ | ✅ NEW | ✅ |
| Weighted Decision | ❌ | ✅ NEW | ✅ |
| Spatial Features | ✅ | ✅ | ✅ |

---

## 📦 Output JSON Structure (V5)

```json
{
  "timestamp_seconds": 88.3,
  "start_frame": 2639,
  "end_frame": 2651,
  "outcome": "made",
  "outcome_reason": "weighted_score_high (score=75/100)",
  "confidence": 0.92,

  // Existing features
  "valid_top_crossings": 1,
  "valid_bottom_crossings": 1,
  "avg_size_ratio": 0.273,
  "bounced_back_out": false,
  "bounce_upward_pixels": 0,
  "frames_in_zone": 10,

  // NEW V5 features
  "entry_angle": 65.3,
  "downward_consistency": 0.85,
  "overlap_frames": {
    "100": 2,
    "95": 4,
    "90": 6,
    "80": 8
  },
  "max_overlap_percentage": 100.0,
  "weighted_overlap_score": 2.8,
  "post_hoop_analysis": {
    "ball_continues_down": true,
    "ball_bounces_back": false,
    "downward_movement": 45,
    "upward_movement": 0,
    "downward_consistency": 0.85,
    "upward_consistency": 0.0
  },
  "decision_score": 75,
  "decision_max_score": 100,

  "spatial_features": {
    "ball_hoop_horizontal_offset": 23.5,
    "ball_hoop_vertical_offset": 72.5,
    "ball_distance_to_hoop": 76.21,
    "ball_moving_left": true,
    "ball_moving_right": false,
    "lateral_velocity": -78.0,
    "ball_size": 26
  },

  "detection_method": "line_intersection_v5_multi_factor"
}
```

---

## 🚀 Next Steps

1. **Implement Phase 1** (Feature Calculations)
   - Add all 5 new calculation methods
   - Test each method individually

2. **Implement Phase 2** (Decision Logic)
   - Add weighted scoring
   - Update classify_shot()
   - Update JSON output

3. **Test & Validate** (Phase 3)
   - Quick test (5 minutes)
   - Problematic timestamps
   - Full game runs

4. **Compare & Iterate** (Phase 4)
   - Compare with near angle
   - Adjust thresholds
   - Finalize V5

---

## 📝 Notes

- Keep V4 logic as backup (rename file to `simple_line_intersection_test_v4_backup.py`)
- All changes in `simple_line_intersection_test.py`
- Same `main.py` - no changes needed
- Compatible with existing result structure
- Can run V4 and V5 side-by-side for comparison

**File to modify:** `Uball_far_angle_shot_detection/simple_line_intersection_test.py`

**Methods to add:** ~150 lines of new code

**Expected development time:** 1-2 days

**Expected accuracy improvement:** +15-20% (70% → 85-90%)

This will bring far angle performance to near angle levels! 🎯
