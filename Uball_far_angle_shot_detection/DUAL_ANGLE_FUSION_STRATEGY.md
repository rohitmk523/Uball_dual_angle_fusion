# Dual Angle Fusion Strategy

**Goal**: Combine Near Angle (88% accuracy) + Far Angle (68% accuracy) → **>90% accuracy**

---

## Repository Structure

```
Uball_dual_angle_fusion/
├── README.md
├── requirements.txt
├── .env
│
├── dual_fusion.py              # Main fusion engine
├── fusion_config.yaml          # Configuration
├── match_shots.py              # Timestamp matching
├── fusion_rules.py             # Decision logic
├── validate_fusion.py          # Validation against ground truth
│
├── repositories/               # Git submodules
│   ├── Uball_near_angle_shot_detection/
│   └── Uball_far_angle_shot_detection/
│
├── input/                      # Input videos
│   └── [game]/
│       ├── near_left.mp4
│       ├── near_right.mp4
│       ├── far_left.mp4
│       └── far_right.mp4
│
└── results/                    # Fusion results
    └── [uuid]/
        ├── near_session.json
        ├── far_session.json
        ├── fused_session.json
        ├── fusion_analysis.json
        └── accuracy_report.json
```

---

## Workflow

### Phase 1: Independent Processing

```bash
# 1. Process Near Angle
cd repositories/Uball_near_angle_shot_detection
python main.py --action video \
    --video_path ../../input/game1/near_left.mp4 \
    --model runs/detect/best.pt \
    --output ../../results/[uuid]/near_session.json

# 2. Process Far Angle
cd repositories/Uball_far_angle_shot_detection
python main.py --action video \
    --video_path ../../input/game1/far_right.mp4 \
    --model runs/detect/basketball_yolo11n2/weights/best.pt \
    --output ../../results/[uuid]/far_session.json
```

### Phase 2: Fusion

```bash
# 3. Fuse detections
python dual_fusion.py \
    --near_session results/[uuid]/near_session.json \
    --far_session results/[uuid]/far_session.json \
    --output results/[uuid]/fused_session.json \
    --config fusion_config.yaml
```

### Phase 3: Validation

```bash
# 4. Validate fused results
python validate_fusion.py \
    --fused_session results/[uuid]/fused_session.json \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --angle LEFT \
    --output results/[uuid]/accuracy_report.json
```

---

## Fusion Logic

### Shot Matching

```python
def match_shots(near_shots, far_shots, tolerance=2.0):
    """
    Match shots from both angles by timestamp

    Args:
        near_shots: List of near angle shots
        far_shots: List of far angle shots
        tolerance: Timestamp tolerance in seconds

    Returns:
        matched_pairs: [(near_shot, far_shot), ...]
        near_only: Shots only detected by near angle
        far_only: Shots only detected by far angle
    """

    matched_pairs = []
    near_only = []
    far_only = []

    for near_shot in near_shots:
        near_ts = near_shot['timestamp_seconds']

        # Find matching far shot within tolerance
        far_match = None
        for far_shot in far_shots:
            far_ts = far_shot['timestamp_seconds']
            if abs(near_ts - far_ts) <= tolerance:
                far_match = far_shot
                break

        if far_match:
            matched_pairs.append((near_shot, far_match))
        else:
            near_only.append(near_shot)

    # Find far shots without near match
    for far_shot in far_shots:
        if not any(pair[1] == far_shot for pair in matched_pairs):
            far_only.append(far_shot)

    return matched_pairs, near_only, far_only
```

### Fusion Decision Rules

```python
def fuse_shot(near_shot, far_shot):
    """
    Fuse two matched shots into single decision

    Priority Rules:

    1. AGREEMENT: If both angles agree
       → Use agreed outcome (HIGH confidence)

    2. NEAR MADE + FAR MISSED:
       → Check far angle reason:
         - If 'rim_bounce' + confidence > 0.90
           → Use FAR (MISSED) ✅ Far angle advantage
         - Else
           → Use NEAR (MADE) ✅ Near is primary

    3. NEAR MISSED + FAR MADE:
       → Check far angle reason:
         - If 'clean_swish' + confidence > 0.90
           → Use FAR (MADE) ✅ Far angle advantage
         - Else
           → Use NEAR (MISSED) ✅ Near is primary

    4. ONE ANGLE ONLY:
       → Use that angle if confidence > threshold
       → Otherwise mark as 'undetermined'
    """

    near_outcome = near_shot['outcome']
    far_outcome = far_shot['outcome']

    # Rule 1: Agreement
    if near_outcome == far_outcome:
        return {
            'outcome': near_outcome,
            'method': 'agreement',
            'confidence': min(0.99, (near_shot['confidence'] + far_shot['confidence']) / 2 + 0.1),
            'near_shot': near_shot,
            'far_shot': far_shot
        }

    # Rule 2: Near MADE, Far MISSED
    if near_outcome == 'made' and far_outcome == 'missed':
        far_reason = far_shot['outcome_reason']
        far_conf = far_shot['decision_confidence']

        # Far angle advantage: Rim bounce detection
        if 'rim_bounce' in far_reason and far_conf >= 0.90:
            return {
                'outcome': 'missed',
                'method': 'far_rim_bounce_override',
                'confidence': far_conf,
                'reason': f'Far angle detected rim bounce: {far_reason}',
                'near_shot': near_shot,
                'far_shot': far_shot
            }
        else:
            # Near angle is primary
            return {
                'outcome': 'made',
                'method': 'near_primary',
                'confidence': near_shot['confidence'],
                'reason': 'Near angle is primary, far not confident',
                'near_shot': near_shot,
                'far_shot': far_shot
            }

    # Rule 3: Near MISSED, Far MADE
    if near_outcome == 'missed' and far_outcome == 'made':
        far_reason = far_shot['outcome_reason']
        far_conf = far_shot['decision_confidence']

        # Far angle advantage: Clean swish detection
        if 'swish' in far_reason and far_conf >= 0.90:
            return {
                'outcome': 'made',
                'method': 'far_swish_override',
                'confidence': far_conf,
                'reason': f'Far angle detected clean swish: {far_reason}',
                'near_shot': near_shot,
                'far_shot': far_shot
            }
        else:
            # Near angle is primary
            return {
                'outcome': 'missed',
                'method': 'near_primary',
                'confidence': near_shot['confidence'],
                'reason': 'Near angle is primary, far not confident',
                'near_shot': near_shot,
                'far_shot': far_shot
            }
```

### Single Angle Handling

```python
def handle_single_angle(shot, angle_type, min_confidence=0.75):
    """
    Handle shots detected by only one angle

    Args:
        shot: The detected shot
        angle_type: 'near' or 'far'
        min_confidence: Minimum confidence to accept

    Returns:
        Fused shot or None
    """

    confidence = shot['decision_confidence']

    if confidence >= min_confidence:
        return {
            'outcome': shot['outcome'],
            'method': f'{angle_type}_only',
            'confidence': confidence,
            'reason': f'Only detected by {angle_type} angle',
            f'{angle_type}_shot': shot
        }
    else:
        return {
            'outcome': 'undetermined',
            'method': f'{angle_type}_low_confidence',
            'confidence': confidence,
            'reason': f'{angle_type} confidence too low: {confidence:.2f}',
            f'{angle_type}_shot': shot
        }
```

---

## Configuration (fusion_config.yaml)

```yaml
fusion:
  # Timestamp matching
  timestamp_tolerance: 2.0  # seconds

  # Confidence thresholds
  min_agreement_confidence: 0.80
  min_single_angle_confidence: 0.75
  far_override_confidence: 0.90

  # Far angle advantages (when to override near)
  far_advantages:
    rim_bounce:
      enabled: true
      min_confidence: 0.90
      keywords: ['rim_bounce']

    clean_swish:
      enabled: true
      min_confidence: 0.90
      keywords: ['swish', 'clean']

  # Primary angle
  primary_angle: 'near'

  # Output
  include_both_detections: true
  save_fusion_analysis: true
```

---

## Expected Performance

### Current Performance

| Metric | Near Angle | Far Angle |
|--------|------------|-----------|
| Matched Shot Accuracy | 88% | 68% |
| Far Correct, Near Wrong | - | 8 cases |
| Near Correct, Far Wrong | 29 cases | - |

### Expected Fusion Performance

**Optimistic Scenario** (All 8 far wins applied):
- Start: 66/75 correct (88%)
- Add: 8 far corrections
- Remove: 0 (near still correct in those)
- **Result: 74/75 = 98.7%** 🎯

**Realistic Scenario** (6/8 far wins applied):
- Start: 66/75 correct (88%)
- Add: 6 far corrections (high confidence only)
- Remove: 1 mistake
- **Result: 71/75 = 94.7%** ✅

**Conservative Scenario** (4/8 far wins applied):
- Start: 66/75 correct (88%)
- Add: 4 far corrections
- Remove: 2 mistakes
- **Result: 68/75 = 90.7%** ✅

**Target: >90% matched shot accuracy**

---

## Implementation Steps

### Step 1: Repository Setup
```bash
# Create new repository
mkdir Uball_dual_angle_fusion
cd Uball_dual_angle_fusion

# Initialize git
git init

# Add submodules
git submodule add ../Uball_near_angle_shot_detection repositories/near_angle
git submodule add ../Uball_far_angle_shot_detection repositories/far_angle
```

### Step 2: Core Implementation
```bash
# Create files
touch dual_fusion.py
touch match_shots.py
touch fusion_rules.py
touch validate_fusion.py
touch fusion_config.yaml
touch requirements.txt
touch README.md
```

### Step 3: Dependencies
```txt
# requirements.txt
ultralytics>=8.0.0
opencv-python>=4.8.0
numpy>=1.24.0
python-dotenv>=1.0.0
python-dateutil>=2.8.0
supabase>=2.0.0
pyyaml>=6.0
```

### Step 4: Testing
```bash
# Test on Game-1
python dual_fusion.py \
    --near_session ../Uball_near_angle_shot_detection/results/09-23\(1-NL\)_*/detection_results.json \
    --far_session ../Uball_far_angle_shot_detection/results/game1-farright_*/detection_results.json \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \
    --angle LEFT \
    --validate
```

### Step 5: Validation
```bash
# Compare results
python validate_fusion.py \
    --fused_session results/[uuid]/fused_session.json \
    --near_session [near_results] \
    --far_session [far_results] \
    --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9

# Expected output:
# Near Accuracy: 88.0%
# Far Accuracy: 68.0%
# Fused Accuracy: 92-95% ✅
```

---

## Success Metrics

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| **Matched Shot Accuracy** | >90% | >95% |
| **Rim Bounce Detection** | 100% | 100% |
| **Clean Swish Detection** | >95% | >98% |
| **False Positives** | <30 | <20 |
| **Ground Truth Coverage** | >95% | >98% |

---

## Next Steps

1. ✅ **Complete far angle optimization** (In progress)
2. ⏳ **Create dual fusion repository**
3. ⏳ **Implement fusion logic**
4. ⏳ **Test on Game-1**
5. ⏳ **Validate and measure accuracy**
6. ⏳ **Deploy to production**

---

**Target Launch**: After far angle reaches 68%+ accuracy
**Expected Timeline**: 1-2 days for fusion implementation
**Expected Outcome**: >90% matched shot accuracy 🎯

---

**End of Fusion Strategy** | Last Updated: November 5, 2025
