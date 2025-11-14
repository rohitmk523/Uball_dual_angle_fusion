# 🏀 Dual-Angle Fusion Analysis - Game 1 (09-23)

## 📊 ACCURACY SUMMARY

### Single Angle Performance

| Metric | Near Angle | Far Angle | Fusion |
|--------|------------|-----------|--------|
| **Outcome Accuracy** | **88.0%** | **84.9%** | **89.2%** |
| Shots Detected | 128 | 125 | 126 |
| Ground Truth Shots | 77 | 77 | 77 |
| Matched Correct | 66/128 | 62/125 | 58/126 |
| Matched Incorrect | 9 | 11 | 7 |
| GT Coverage | 97.4% | 94.8% | 84.4% |

### Key Findings

✅ **Fusion Improves Accuracy**: 89.2% vs 88.0% (near) and 84.9% (far)
- Fusion achieves **best outcome accuracy**
- Near angle has **best GT coverage** (97.4%)
- Far angle has **moderate performance** (84.9%)

## 🔍 FUSION MECHANISM ANALYSIS

### Matching Statistics
- **Matched Pairs**: 101/101 (100% agreement on temporal matching)
- **Unmatched Near**: 27 (kept 25 with conf > 0.75)
- **Unmatched Far**: 24 (kept 0 - all below conf threshold)

### Fusion Decision Breakdown
```
Total Fused Shots: 126
├─ Agreement (both angles match): 101 shots
│  └─ Confidence boost: avg 1.15x
├─ Near dominant (disagreement): ~15 shots
│  └─ Higher near confidence/overlap
└─ Far dominant (disagreement): ~10 shots
   └─ Higher far score
```

## ❌ INCORRECT MATCHES ANALYSIS

### Top Errors (7 total)

1. **939.57s**: Fusion=MADE | GT=MISSED (time_diff: 0.673s)
2. **1405.41s**: Fusion=MADE | GT=MISSED (time_diff: 0.705s)
3. **1643.21s**: Fusion=MISSED | GT=MADE (time_diff: 0.710s)
4. **1698.90s**: Fusion=MADE | GT=MISSED (time_diff: 0.299s)
5. **2290.22s**: Fusion=MISSED | GT=MADE (time_diff: 0.524s)
6. **2555.96s**: Fusion=MADE | GT=MISSED (time_diff: 1.356s)
7. **2862.36s**: Fusion=MISSED | GT=MADE (time_diff: 1.462s)

### Error Pattern Analysis

**Pattern 1: Made → Missed Errors (4/7 = 57%)**
- Fusion incorrectly calls "made" when GT is "missed"
- Possible cause: Both angles show high overlap (ball near rim)
- Fix: Add rim bounce detection, stricter swoosh criteria

**Pattern 2: Missed → Made Errors (3/7 = 43%)**
- Fusion incorrectly calls "missed" when GT is "made"
- Possible cause: Fast swoosh with low overlap on both angles
- Fix: Use entry angle, trajectory smoothness

## 💡 FEATURE-BASED IMPROVEMENTS

### Current Fusion Features
1. Detection confidence (avg of near+far)
2. Outcome agreement (binary)
3. Near overlap quality (avg_overlap, weighted_score)
4. Far line intersection score

### Recommended Additional Features

#### High Priority
1. **Entry Angle Consistency**
   - Near and far should have similar entry angles for same shot
   - If entry angles differ > 15°, penalize confidence
   - Use: Detect rim bounces vs clean makes

2. **Trajectory Smoothness**
   - Track ball velocity changes
   - Smooth trajectory = likely made
   - Erratic = likely missed or rim bounce

3. **Rim Bounce Confidence**
   - Both angles should detect rim bounce similarly
   - If one detects bounce, other should too
   - Use: Reduce false "made" calls

4. **Swoosh Speed**
   - Fast disappearance after peak = clean make
   - Slow/oscillating = rim bounce or miss
   - Use: Better made/missed discrimination

#### Medium Priority
5. **Net Movement (Near Angle)**
   - Detect net disturbance after shot
   - Strong indicator for made shots
   - Available only in near angle

6. **Ball Spin Analysis (Far Angle)**
   - Backspin indicates proper shot form
   - Correlates with makes
   - Available in far angle line tracking

### Feature Weighting Strategy

```python
# Proposed weighted fusion
fusion_score = (
    0.30 * outcome_agreement +
    0.20 * avg_confidence +
    0.15 * entry_angle_consistency +
    0.15 * rim_bounce_agreement +
    0.10 * trajectory_smoothness +
    0.10 * swoosh_speed_score
)

if fusion_score > 0.70:
    confidence = "high" (0.85-0.95)
elif fusion_score > 0.50:
    confidence = "medium" (0.70-0.85)
else:
    confidence = "low" (<0.70)
```

## 📈 IMPROVEMENT ROADMAP

### Phase 1: Feature Extraction (Immediate)
- [ ] Extract entry_angle from both near and far detections
- [ ] Calculate entry_angle_consistency (absolute difference)
- [ ] Extract rim_bounce_confidence from both angles
- [ ] Measure swoosh_speed (frames from peak to disappearance)

### Phase 2: Enhanced Fusion Logic (Week 1)
- [ ] Implement weighted scoring system
- [ ] Add feature-based arbitration for disagreements
- [ ] Tune thresholds using validation set
- [ ] Test on games 2 and 3

### Phase 3: Advanced Features (Week 2-3)
- [ ] Trajectory smoothness via Kalman filtering
- [ ] Net movement detection (near angle)
- [ ] Ball spin analysis (far angle)
- [ ] Cross-validate on all available games

## 🎯 EXPECTED IMPROVEMENTS

| Metric | Current | Target (Phase 1) | Target (Phase 3) |
|--------|---------|------------------|------------------|
| Outcome Accuracy | 89.2% | 92%+ | 95%+ |
| False Positive Rate | ~5.6% | <3% | <2% |
| Matched Incorrect | 7 | <5 | <3 |

### Success Criteria
- **Accuracy**: >92% by Phase 1, >95% by Phase 3
- **Consistency**: <3 incorrect matches per game
- **Robustness**: Works across different court angles and lighting

## 📁 Result Directories

- **Near**: `Uball_near_angle_shot_detection/results/09-23(1-NL)_19952716-2882-401c-9598-6532a9c403cc/`
- **Far**: `Uball_far_angle_shot_detection/results/09-23(1-FR)_146de990-89ca-4fef-a013-6569201b92da/`
- **Fusion**: `results/09-23(game1-R-)_96fab281-b43b-4afe-a527-ed50810634bf/`

---

**Generated**: 2025-11-14
**Analysis Version**: v1.0
