# Dual-Angle Fusion V2 - Feature-Based Accuracy Improvement Plan

## Current Status (V1)
- **Accuracy**: 91.2% (high recall mode)
- **Coverage**: 88.3% (68/77 GT shots)
- **Missing GT shots**: 9 (11.7%)
- **Incorrect predictions**: 7 shots

## V2 Goal
- **Target Accuracy**: 94%+ (from 91.2%)
- **Target Coverage**: 92%+ (from 88.3%)
- **Approach**: Leverage EXISTING features from single-angle detection JSON files

---

## Phase 1: Exploit Existing Features (ZERO new detection runs needed!)

### Available Rich Features

#### Near Angle Features (Already in JSON)
```json
{
  "entry_angle": 58.57,
  "is_rim_bounce": false,
  "rim_bounce_confidence": 0.0,
  "max_overlap_percentage": 98.5,
  "avg_overlap_percentage": 54.4,
  "weighted_overlap_score": 1.8,
  "post_hoop_analysis": {
    "ball_continues_down": false,
    "ball_bounces_back": false,
    "downward_movement": -84,
    "upward_movement": 84
  },
  "decision_confidence": 0.8,
  "outcome_reason": "insufficient_overlap"
}
```

#### Far Angle Features (Already in JSON)
```json
{
  "valid_top_crossings": 1,
  "valid_bottom_crossings": 1,
  "avg_size_ratio": 0.85,
  "bounced_back_out": false,
  "bounce_upward_pixels": 0,
  "spatial_features": {
    "ball_hoop_horizontal_offset": -1.0,
    "ball_hoop_vertical_offset": -20.0,
    "ball_distance_to_hoop": 20.0,
    "lateral_velocity": 2.2,
    "ball_size": 26
  },
  "outcome_reason": "clean_make"
}
```

### V2 Feature-Based Fusion Logic

#### 1. Rim Bounce Agreement (High Priority)
**Current Issue**: 4/7 incorrect predictions are "made" when GT is "missed" (likely rim bounces)

**Solution**:
```python
def check_rim_bounce_agreement(near_shot, far_shot):
    """
    Both angles should agree on rim bounce detection
    """
    near_bounce = near_shot.get('is_rim_bounce', False)
    far_bounce = far_shot.get('bounced_back_out', False)

    # Agreement cases
    if near_bounce and far_bounce:
        return {'agreement': True, 'is_bounce': True, 'confidence': 0.95}
    elif not near_bounce and not far_bounce:
        return {'agreement': True, 'is_bounce': False, 'confidence': 0.9}
    else:
        # Disagreement - trust near angle (better rim visibility)
        return {'agreement': False, 'is_bounce': near_bounce, 'confidence': 0.7}
```

**Expected Impact**: Fix 3-4 of the "made → missed" errors

---

#### 2. Entry Angle Consistency (High Priority)
**Current Issue**: If entry angles differ significantly, it's likely a different shot or tracking error

**Solution**:
```python
def check_entry_angle_consistency(near_shot, far_shot):
    """
    Entry angles should be similar for the same shot
    Near: measured from side view
    Far: derived from trajectory slope
    """
    near_angle = near_shot.get('entry_angle', None)

    # Far angle doesn't have entry_angle directly, but we can derive from:
    # - valid_top_crossings and spatial_features
    # - If top crossing exists, entry was from above (steep angle)

    far_top_crossings = far_shot.get('valid_top_crossings', 0)

    # Rough mapping:
    # Near entry_angle > 50° = steep (from above)
    # Near entry_angle < 40° = shallow (line drive)

    if near_angle and near_angle > 50 and far_top_crossings > 0:
        return {'consistent': True, 'confidence_boost': 1.1}
    elif near_angle and near_angle < 40 and far_top_crossings == 0:
        return {'consistent': True, 'confidence_boost': 1.05}
    else:
        return {'consistent': False, 'confidence_penalty': 0.9}
```

**Expected Impact**: Improve temporal matching accuracy

---

#### 3. Swoosh Speed Analysis (Medium Priority)
**Current Issue**: Clean makes have fast ball disappearance, rim bounces linger

**Solution**:
```python
def analyze_swoosh_speed(near_shot, far_shot):
    """
    Fast disappearance = clean make
    Slow/oscillating = rim bounce or miss
    """
    # Near angle: use post_hoop_analysis
    near_downward = near_shot.get('post_hoop_analysis', {}).get('downward_movement', 0)
    near_continues_down = near_shot.get('post_hoop_analysis', {}).get('ball_continues_down', False)

    # Far angle: use size_ratio progression
    far_size_ratio = far_shot.get('avg_size_ratio', 0)
    far_bottom_crossings = far_shot.get('valid_bottom_crossings', 0)

    # Fast swoosh indicators:
    # - Near: ball continues downward smoothly
    # - Far: size decreases (ball going away), bottom crossing exists

    if near_continues_down and far_bottom_crossings > 0 and far_size_ratio > 0.6:
        return {'swoosh_quality': 'fast', 'made_confidence': 1.2}
    elif not near_continues_down and far_bottom_crossings == 0:
        return {'swoosh_quality': 'slow', 'missed_confidence': 1.15}
    else:
        return {'swoosh_quality': 'uncertain', 'confidence': 1.0}
```

**Expected Impact**: Fix 2-3 of the "missed → made" errors

---

#### 4. Weighted Confidence Scoring (High Priority)
**Current Fusion** (V1):
```python
# Simple average
fusion_confidence = (near_conf + far_conf) / 2
if outcome_agreement:
    fusion_confidence *= 1.15
```

**New Fusion** (V2):
```python
def calculate_fusion_confidence(near_shot, far_shot, match_data):
    """
    Feature-weighted confidence calculation
    """
    base_conf = (near_shot['detection_confidence'] + far_shot['detection_confidence']) / 2

    # Feature weights
    weights = {
        'outcome_agreement': 0.30,
        'rim_bounce_agreement': 0.20,
        'entry_angle_consistency': 0.15,
        'swoosh_speed': 0.15,
        'overlap_quality': 0.10,  # Near angle
        'line_intersection': 0.10   # Far angle
    }

    scores = {}

    # 1. Outcome agreement
    if near_shot['outcome'] == far_shot['outcome']:
        scores['outcome_agreement'] = 1.0
    else:
        scores['outcome_agreement'] = 0.0

    # 2. Rim bounce agreement
    rim_check = check_rim_bounce_agreement(near_shot, far_shot)
    scores['rim_bounce_agreement'] = 1.0 if rim_check['agreement'] else 0.5

    # 3. Entry angle consistency
    angle_check = check_entry_angle_consistency(near_shot, far_shot)
    scores['entry_angle_consistency'] = 1.0 if angle_check['consistent'] else 0.4

    # 4. Swoosh speed
    swoosh = analyze_swoosh_speed(near_shot, far_shot)
    scores['swoosh_speed'] = 1.0 if swoosh['swoosh_quality'] == 'fast' else 0.6

    # 5. Overlap quality (near angle)
    near_overlap = near_shot.get('weighted_overlap_score', 0) / 2.0  # Normalize to 0-1
    scores['overlap_quality'] = min(1.0, near_overlap)

    # 6. Line intersection (far angle)
    far_crossings = (far_shot.get('valid_top_crossings', 0) +
                     far_shot.get('valid_bottom_crossings', 0))
    scores['line_intersection'] = min(1.0, far_crossings / 2.0)

    # Calculate weighted score
    weighted_score = sum(weights[k] * scores[k] for k in weights)

    # Apply to base confidence
    final_confidence = base_conf * (0.7 + 0.6 * weighted_score)

    return {
        'confidence': min(0.99, final_confidence),
        'feature_scores': scores,
        'base_confidence': base_conf
    }
```

**Expected Impact**: Better confidence differentiation, reduce false positives

---

#### 5. Disagreement Resolution (High Priority)
**Current Issue**: When angles disagree, V1 uses simple confidence comparison

**New Approach**:
```python
def resolve_disagreement(near_shot, far_shot, fusion_scores):
    """
    Use feature analysis to resolve disagreements
    """
    # Get feature scores
    feature_scores = fusion_scores['feature_scores']

    # High confidence indicators for MADE:
    made_indicators = [
        feature_scores['rim_bounce_agreement'] < 0.6,  # Both say no bounce
        feature_scores['swoosh_speed'] > 0.8,          # Fast swoosh
        feature_scores['line_intersection'] > 0.8,     # Clean pass through
        feature_scores['overlap_quality'] > 0.7         # High overlap
    ]

    # High confidence indicators for MISSED:
    missed_indicators = [
        feature_scores['rim_bounce_agreement'] > 0.8 and
            (near_shot.get('is_rim_bounce') or far_shot.get('bounced_back_out')),
        feature_scores['swoosh_speed'] < 0.4,
        feature_scores['line_intersection'] < 0.3,
        feature_scores['overlap_quality'] < 0.4
    ]

    made_score = sum(made_indicators)
    missed_score = sum(missed_indicators)

    if made_score > missed_score:
        return 'made', 0.8 + (made_score * 0.05)
    elif missed_score > made_score:
        return 'missed', 0.8 + (missed_score * 0.05)
    else:
        # Fall back to higher individual confidence
        if near_shot['detection_confidence'] > far_shot['detection_confidence']:
            return near_shot['outcome'], near_shot['detection_confidence'] * 0.9
        else:
            return far_shot['outcome'], far_shot['detection_confidence'] * 0.9
```

**Expected Impact**: Fix 3-4 disagreement errors

---

## Phase 2: Implementation Steps

### Step 1: Update `fuse_matched_pair()` method
```python
def fuse_matched_pair(self, match: Dict) -> Dict:
    """Enhanced fusion with feature-based scoring"""
    near = match['near']
    far = match['far']

    # Calculate feature-based confidence
    fusion_analysis = calculate_fusion_confidence(near, far, match)

    # Determine outcome
    if near['outcome'] == far['outcome']:
        outcome = near['outcome']
        confidence = fusion_analysis['confidence']
    else:
        # Resolve disagreement using features
        outcome, confidence = resolve_disagreement(near, far, fusion_analysis)

    return {
        'timestamp_seconds': near['timestamp_seconds'],
        'outcome': outcome,
        'fusion_method': 'feature_weighted_v2',
        'fusion_confidence': confidence,
        'outcome_agreement': near['outcome'] == far['outcome'],
        'feature_analysis': fusion_analysis,
        'near_detection': {
            'outcome': near['outcome'],
            'confidence': near['detection_confidence'],
            'entry_angle': near.get('entry_angle'),
            'is_rim_bounce': near.get('is_rim_bounce'),
            'overlap_score': near.get('weighted_overlap_score')
        },
        'far_detection': {
            'outcome': far['outcome'],
            'confidence': far['detection_confidence'],
            'top_crossings': far.get('valid_top_crossings'),
            'bottom_crossings': far.get('valid_bottom_crossings'),
            'bounced_back': far.get('bounced_back_out')
        }
    }
```

### Step 2: Test on Game 1 with existing results
```bash
# Use existing single-angle results (NO re-detection needed!)
python3 dual_angle_fusion.py \
  --use_existing_near "Uball_near_angle_shot_detection/results/09-23(1-NL)_UUID" \
  --use_existing_far "Uball_far_angle_shot_detection/results/09-23(1-FR)_UUID" \
  --near_video input/09-23/Game-1/game1_nearleft.mp4 \
  --far_video input/09-23/Game-1/game1_farright.mp4 \
  --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
  --near_model Uball_near_angle_shot_detection/runs/detect/basketball_yolo11n3/weights/best.pt \
  --far_model Uball_far_angle_shot_detection/runs/detect/basketball_yolo11n2/weights/best.pt \
  --offset_file offsets/09_23_game_1_offsets.json \
  --validate_accuracy \
  --angle RIGHT \
  --skip_video
```

**Time: ~5 seconds** (no video, no detection - just fusion logic!)

### Step 3: Analyze results and iterate
- Compare V2 vs V1 accuracy
- Identify which features contribute most
- Tune weights if needed

### Step 4: Validate on other games
- Game 2 (09-22)
- Game 3 (09-23)
- Ensure improvements generalize

---

## Phase 3: Optional - New Features (If Phase 1 insufficient)

Only implement if we don't reach 94% accuracy with existing features.

### Potential New Features
1. **Net movement detection** (near angle)
   - Detect net swaying after shot
   - Strong indicator for made shots
   - Requires: New video analysis in near angle detector

2. **Ball spin analysis** (far angle)
   - Backspin correlation with makes
   - Requires: Optical flow or frame differencing

3. **Trajectory smoothness** (both angles)
   - Kalman filter for ball tracking
   - Smooth trajectory = likely made
   - Requires: Re-running detection with Kalman

---

## Expected Results

### Phase 1 Targets (Using Existing Features Only)
| Metric | V1 (Current) | V2 (Target) | Improvement |
|--------|-------------|-------------|-------------|
| **Accuracy** | 91.2% | **94.0%** | +2.8% |
| **Coverage** | 88.3% | **92.0%** | +3.7% |
| **Incorrect Matches** | 7 | **4** | -3 |
| **Missing GT** | 9 | **6** | -3 |

### Error Reduction by Category
| Error Type | V1 Count | V2 Target | Fix Method |
|------------|----------|-----------|------------|
| Made → Missed (false positive) | 4 | 1 | Rim bounce agreement |
| Missed → Made (false negative) | 3 | 1 | Swoosh speed analysis |
| Temporal mismatch | 2 | 1 | Entry angle consistency |

---

## Implementation Timeline

| Phase | Task | Time | Status |
|-------|------|------|--------|
| **1.1** | Implement feature extraction helpers | 2 hours | Pending |
| **1.2** | Update `fuse_matched_pair()` with weighted scoring | 3 hours | Pending |
| **1.3** | Implement disagreement resolution | 2 hours | Pending |
| **1.4** | Test on Game 1 | 10 seconds | Pending |
| **1.5** | Analyze results and tune weights | 1 hour | Pending |
| **1.6** | Validate on Games 2 & 3 | 30 seconds | Pending |
| **1.7** | Document and commit V2 | 1 hour | Pending |
| **TOTAL** | | **~10 hours** | |

---

## Key Advantages of This Approach

1. **Zero re-detection needed** - All features already in JSON files
2. **Fast iteration** - Test changes in 5-10 seconds with `--skip_video` + `--use_existing_*`
3. **Explainable** - Feature-based decisions are transparent
4. **Transferable** - Feature weights can be tuned per game if needed
5. **Backward compatible** - V1 fusion still available as fallback

---

## Success Criteria

- [x] V1 baseline: 91.2% accuracy, 88.3% coverage ✅
- [ ] V2 Phase 1: 94%+ accuracy, 92%+ coverage
- [ ] Reduce incorrect matches from 7 to ≤4
- [ ] Explainable feature contributions in output JSON
- [ ] Validated across multiple games

---

**Next Steps**:
1. User approval of this plan
2. Create `dual_angle_fusion_v2.py` with feature-based logic
3. Run comparative analysis V1 vs V2

**Last Updated**: 2025-11-15
