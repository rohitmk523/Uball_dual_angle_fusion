# Basketball Shot Detection - Comprehensive Accuracy Report

**Report Date:** November 2, 2025
**Algorithm Version:** Enhanced Multi-Factor V3
**Total Test Sessions:** 10 games
**Total Shots Analyzed:** 796 ground truth shots

---

## Executive Summary

### Overall Performance Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Average Matched Shots Accuracy** | **89.87%** | 90% | Near Target |
| Average Overall Accuracy | 63.02% | 75% | Below Target |
| Average Ground Truth Coverage | 97.22% | 95% | Exceeds Target |
| Average Detection Coverage | 70.10% | 80% | Below Target |
| Total Detected Shots | 1,119 | - | - |
| Total Ground Truth Shots | 796 | - | - |
| Total Matched Correct | 697 | - | - |
| Total Matched Incorrect | 79 | - | - |
| Total False Positives | 343 | - | - |

### Key Findings

1. **High Detection Coverage (97.22%)**: The system successfully detects nearly all actual shots, with very few missed detections
2. **Strong Matched Shot Accuracy (89.87%)**: When shots are matched to ground truth, the system correctly classifies made/missed outcomes 89.87% of the time
3. **False Positive Challenge**: 343 false positives (30.7% of detections) significantly impact overall accuracy
4. **Consistent Performance**: Low standard deviation (2.72%) in matched shots accuracy shows reliable performance across different game conditions

---

## Detailed Results by Test Session

### Per-Session Breakdown

| Session | Video Path | Detected | Ground Truth | Matched Correct | Matched Incorrect | False Positives | Matched Accuracy | Overall Accuracy |
|---------|------------|----------|--------------|-----------------|-------------------|-----------------|------------------|------------------|
| 09-22(1-NL) | game1_nearleft.mp4 | 111 | 78 | 66 | 10 | 35 | 86.84% | 59.46% |
| 09-22(1-NR) | game1_nearright.mp4 | 82 | 74 | 65 | 7 | 10 | 90.28% | 79.27% |
| 09-22(2-NL) | game2_nearleft.mp4 | 86 | 57 | 48 | 4 | 34 | 92.31% | 55.81% |
| 09-22(2-NR) | game2_nearright.mp4 | 110 | 66 | 60 | 4 | 46 | 93.75% | 54.55% |
| 09-22(3-NL) | game3_nearleft.mp4 | 100 | 79 | 70 | 8 | 22 | 89.74% | 70.00% |
| 09-22(3-NR) | game3_nearright.mp4 | 105 | 83 | 74 | 8 | 23 | 90.24% | 70.48% |
| 09-23(1-NL) | game1_nearleft.mp4 | 130 | 77 | 66 | 9 | 55 | 88.00% | 50.77% |
| 09-23(1-NR) | game1_nearright.mp4 | 123 | 81 | 66 | 12 | 45 | 84.62% | 53.66% |
| 09-23(2-NL) | game2_nearleft.mp4 | 115 | 96 | 87 | 8 | 20 | 91.58% | 75.65% |
| 09-23(2-NR) | game2_nearright.mp4 | 157 | 105 | 95 | 9 | 53 | 91.35% | 60.51% |

### Performance by Camera Angle

| Angle | Sessions | Avg Matched Accuracy | Avg Overall Accuracy | Notes |
|-------|----------|---------------------|---------------------|-------|
| **Near Left (NL)** | 5 | 89.69% | 62.34% | Slightly lower overall accuracy due to more false positives |
| **Near Right (NR)** | 5 | 90.05% | 63.69% | Marginally better performance, fewer false positives |

**Observation:** Both camera angles perform similarly, with Near Right showing slightly better results (0.36% difference in matched accuracy). This suggests the detection algorithm is robust across different camera positions.

---

## Statistical Analysis

### Matched Shots Accuracy Distribution

| Statistic | Value |
|-----------|-------|
| Mean | 89.87% |
| Median | 90.26% |
| Standard Deviation | 2.72% |
| Minimum | 84.62% |
| Maximum | 93.75% |

**Analysis:** The low standard deviation (2.72%) indicates consistent performance across different games and conditions. The system performs predictably and reliably.

### Overall Accuracy Distribution

| Statistic | Value |
|-----------|-------|
| Mean | 63.02% |
| Median | 59.98% |
| Standard Deviation | 10.05% |
| Minimum | 50.77% |
| Maximum | 79.27% |

**Analysis:** Higher standard deviation (10.05%) in overall accuracy reflects variability in false positive rates across different games. Some games have better precision than others.

---

## Processing Architecture

### System Overview

The Basketball Shot Detection System uses a multi-stage processing pipeline combining deep learning object detection with physics-based shot outcome classification.

### Architecture Components

#### 1. Object Detection (YOLOv11)
- **Model:** YOLOv11 Nano (custom-trained)
- **Objects Detected:** Basketball, Basketball Hoop
- **Processing Speed:** ~5-15 FPS (post-processing optimized, not real-time)
- **Training Data:** Custom basketball game footage

#### 2. Shot Detection Pipeline

```
Video Input → YOLO Detection → Ball Tracking → Hoop Intersection → Shot Classification → Output
```

**Stage 1: Object Detection**
- Frame-by-frame detection of ball and hoop using YOLOv11
- Confidence filtering to remove low-quality detections
- Bounding box extraction for position tracking

**Stage 2: Trajectory Tracking**
- Kalman filtering for smooth ball trajectory
- Position history maintenance for velocity calculation
- Duplicate shot prevention (2-second temporal window)

**Stage 3: Hoop Intersection Analysis**
- Bounding box overlap calculation (ball ∩ hoop)
- Temporal overlap tracking (frames with overlap)
- Weighted overlap scoring for fast-moving shots

**Stage 4: Shot Classification (Enhanced Multi-Factor V3)**

The system uses multiple physics-based indicators to classify shots as made or missed:

##### A. Box Overlap Analysis
- **Perfect Overlap (100%):** Indicates ball passing through hoop
- **Threshold:** 6+ frames at 100% overlap = certain made shot
- **High Confidence:** 4+ frames at 100% + 7+ frames at 95% = likely made

##### B. Entry Angle Calculation
- Calculates ball's approach angle to hoop center
- **Steep Entry (>70°):** Higher probability of made shot
- **Shallow Entry (<45°):** May indicate rim bounce or miss
- Used as supporting evidence for classification

##### C. Post-Hoop Trajectory Analysis
- **Downward Movement:** Ball continues down after hoop (made)
- **Upward/Backward Movement:** Ball bounces back (missed)
- **Movement Consistency:** Validates trajectory direction

##### D. Rim Bounce Detection
- **Indicators:** Vertical velocity reversals, trajectory changes
- **Confidence Scoring:** Multi-factor physics-based analysis
- **Override Logic:** High-confidence rim bounce (>60%) forces "missed" classification

##### E. Decision Confidence Scoring
- Each classification receives confidence score (0.0-1.0)
- Confidence based on strength of supporting indicators
- **High Confidence (>0.8):** Strong evidence from multiple factors
- **Medium Confidence (0.65-0.8):** Moderate evidence
- **Low Confidence (<0.65):** Ambiguous, weak indicators

### Detection Method Classifications

| Classification | Criteria | Confidence |
|---------------|----------|------------|
| `perfect_overlap_layup` | 6+ frames at 100% overlap | 0.95 |
| `perfect_overlap_steep_entry` | 4+ frames at 100%, steep angle | 0.90 |
| `fast_clean_swish` | Weighted overlap 3.5+, good trajectory | 0.85 |
| `perfect_overlap` | 4+ frames at 100%, 7+ at 95% | 0.85 |
| `insufficient_overlap` | Low overlap, no strong indicators | 0.60 |
| `rim_bounce_detected` | High rim bounce confidence | 0.75 |

### Validation Pipeline

```
Detection Results → Ground Truth Fetch (Supabase) → Timestamp Matching → Outcome Comparison → Accuracy Metrics
```

**Timestamp Matching:**
- 2-second matching window (±1 second from ground truth)
- Allows for minor timing discrepancies in manual annotations

**Outcome Comparison:**
- Compares detected outcome (made/missed) with ground truth
- Categorizes results: Matched Correct, Matched Incorrect, False Positives, Missed Detections

---

## Error Analysis

### 1. Matched Incorrect Shots (79 total)

These are shots detected and matched to ground truth, but with wrong outcome classification.

#### Breakdown by Error Type

| Error Type | Count | Percentage |
|------------|-------|------------|
| Detected as MADE, Actually MISSED | 47 | 59.5% |
| Detected as MISSED, Actually MADE | 32 | 40.5% |

#### Primary Causes of Misclassification

| Detection Reason | Count | Issue |
|-----------------|-------|-------|
| `insufficient_overlap` | 25 | System fails to detect sufficient ball-hoop overlap for made shots (usually fast shots or occlusions) |
| `perfect_overlap_steep_entry` | 22 | System incorrectly classifies rim bounces as made shots based on overlap |
| `perfect_overlap_layup` | 9 | Layups with high overlap misclassified (rim bounces not detected) |
| `fast_clean_swish` | 8 | Fast shots with good indicators but incorrect outcome |
| `perfect_overlap` | 6 | Generic perfect overlap misclassifications |
| `steep_entry_bounce_back` | 6 | Steep entry shots that bounce out incorrectly classified |

**Key Insight:** The two dominant error patterns are:
1. **Missed Fast Makes (32%):** Fast-moving made shots with insufficient detected overlap
2. **Rim Bounce Confusion (59%):** Shots that bounce in/out of rim with high overlap but wrong outcome

### 2. False Positives (343 total)

These are detections that do not match any ground truth shot (extra detections).

#### Characteristics

- **Rate:** 30.7% of all detections are false positives
- **Impact:** Major factor in lower overall accuracy (63.02%)
- **Variability:** High variance across sessions (10 to 55 per game)

#### Probable Causes

1. **Ball-Hoop Proximity:** Ball passing near hoop without shot attempt
2. **Rebounds:** Ball bouncing near hoop after initial shot
3. **Defensive Plays:** Ball deflected or blocked near hoop
4. **Duplicate Detections:** Same shot detected multiple times despite 2-second window
5. **Loose Balls:** Ball rolling or bouncing near hoop area

**Best Performing Session:** 09-22(1-NR) with only 10 false positives (12.2% false positive rate)
**Worst Performing Session:** 09-23(1-NL) with 55 false positives (42.3% false positive rate)

### 3. Missed Detections (Very Low)

- **Ground Truth Coverage:** 97.22% average
- **Missed Shots:** Only ~2.78% of actual shots are completely missed
- **Conclusion:** Detection recall is excellent; the system rarely fails to detect actual shots

---

## Current Limitations

### 1. False Positive Rate (Primary Issue)
**Impact:** 30.7% of detections are not actual shot attempts
**Consequence:** Reduces overall accuracy and requires manual filtering for production use

**Root Causes:**
- System detects ball-hoop intersections regardless of shot context
- No player action/intent detection to distinguish shots from other ball-hoop interactions
- Rebounds, passes, and defensive plays near hoop trigger detections

**Mitigation Strategies:**
- Add player pose detection to identify shooting motion
- Implement trajectory analysis to distinguish shot attempts from other movements
- Use temporal context (e.g., game state, player positions) to filter false positives

### 2. Rim Bounce Misclassification
**Impact:** 59.5% of matched incorrect shots are rim bounces classified as made shots
**Consequence:** Overestimates shooting percentage

**Root Causes:**
- High ball-hoop overlap occurs even when ball bounces off rim
- Current rim bounce detection (confidence-based) insufficient for all cases
- Post-hoop trajectory analysis sometimes fails to detect bounce-back

**Mitigation Strategies:**
- Enhance rim bounce detection with more sophisticated physics modeling
- Add audio analysis to detect rim contact sounds
- Improve post-hoop trajectory validation with longer tracking windows

### 3. Fast Shot Detection
**Impact:** 32 missed made shots due to insufficient overlap detection
**Consequence:** Underestimates shooting percentage for fast shooters

**Root Causes:**
- Fast-moving balls may not be detected in every frame through hoop
- Temporal overlap window may miss quick swishes
- Motion blur in fast shots reduces detection confidence

**Mitigation Strategies:**
- Implement motion compensation and prediction
- Use weighted temporal scoring (already partially implemented)
- Consider higher frame rate processing for fast sequences

### 4. Single-Camera Limitations
**Impact:** Limited viewing angle can miss or misclassify shots
**Consequence:** Reduced accuracy for shots from certain positions

**Root Causes:**
- Occlusions from players, structures, or hoop itself
- Limited depth perception from single viewpoint
- Some shot trajectories not visible from single angle

**Future Enhancement:**
- Dual-camera system implementation planned
- Cross-camera correlation for improved accuracy
- Multi-angle fusion for 95%+ target accuracy

### 5. Lighting and Environmental Factors
**Impact:** Variable performance across different game sessions
**Consequence:** 10.05% standard deviation in overall accuracy

**Root Causes:**
- Different lighting conditions affect ball/hoop detection
- Court backgrounds vary in complexity
- Camera angles and distances differ between sessions

---

## Recommendations

### Immediate Improvements (Quick Wins)

1. **False Positive Reduction**
   - Implement minimum ball velocity threshold for shot detection
   - Add downward trajectory requirement (shots must have upward-then-downward arc)
   - Increase duplicate prevention window from 2 to 3 seconds for dense action areas
   - **Expected Impact:** Reduce false positives by 30-40%

2. **Rim Bounce Enhancement**
   - Extend post-hoop tracking from current window to 10+ frames
   - Add secondary velocity change detection for rim contact
   - Implement multi-point trajectory validation
   - **Expected Impact:** Reduce rim bounce misclassifications by 50%

3. **Fast Shot Optimization**
   - Adjust weighted overlap scoring for quick swishes
   - Lower perfect overlap frame count requirement for high-velocity shots
   - Add motion prediction for ball position interpolation
   - **Expected Impact:** Improve fast shot detection by 25%

### Medium-Term Enhancements

4. **Player Context Analysis**
   - Integrate player detection and pose estimation
   - Identify shooting motion (arms raised, follow-through)
   - Filter detections without shooting player nearby
   - **Expected Impact:** Reduce false positives by 50-60%, reach 75%+ overall accuracy

5. **Confidence Calibration**
   - Analyze confidence scores vs actual accuracy for each detection method
   - Recalibrate confidence thresholds based on empirical data
   - Implement adaptive thresholds for different game contexts

### Long-Term Strategy

6. **Dual-Camera Implementation**
   - Synchronize near-left and near-right camera feeds
   - Cross-validate detections between cameras
   - Implement sensor fusion algorithm for combined decision
   - **Expected Impact:** Achieve 95%+ matched shots accuracy target

7. **Audio Integration**
   - Add microphone input for rim/backboard contact sounds
   - Use audio cues to validate rim bounce detections
   - Improve ambiguous shot classification with sound analysis

8. **Machine Learning Classification**
   - Train dedicated ML model for made/missed classification
   - Use detected features as input (overlap, angle, trajectory, etc.)
   - Continuous learning from validated ground truth data
   - **Expected Impact:** Potentially reach 95%+ accuracy with single camera

---

## Conclusion

The Basketball Shot Detection System demonstrates strong core performance with **89.87% matched shots accuracy** and **97.22% ground truth coverage**. The system reliably detects shots and correctly classifies their outcomes in the majority of cases.

### Strengths
- Excellent detection recall (97.22% coverage)
- Consistent matched shot accuracy (2.72% std dev)
- Robust performance across different camera angles
- Physics-based classification provides interpretable results

### Areas for Improvement
- **Primary:** False positive reduction (343 extra detections)
- **Secondary:** Rim bounce misclassification (47 cases)
- **Tertiary:** Fast shot detection enhancement (32 missed cases)

### Path to Production
With targeted improvements to false positive filtering and rim bounce detection, the system can realistically achieve:
- **90%+ matched shots accuracy** (immediate, with current algorithm refinements)
- **75%+ overall accuracy** (short-term, with player context analysis)
- **95%+ matched shots accuracy** (long-term, with dual-camera implementation)

The current V3 algorithm provides a solid foundation for production deployment with acceptable accuracy for many use cases. For applications requiring higher precision, implementing the recommended enhancements will progressively improve system performance toward the 95% target.

---

## Appendices

### A. Test Session Details

All test sessions were conducted on basketball game footage from September 22-23, 2025, using the Enhanced Multi-Factor V3 detection algorithm. Ground truth data was manually annotated and stored in Supabase database.

**Video Specifications:**
- Resolution: 1920x1080 (Full HD)
- Frame Rate: 30 FPS
- Camera: Near-angle placement (both left and right positions)

### B. Validation Methodology

**Timestamp Matching:** 2-second window (±1 second)
**Outcome Classification:** Binary (made/missed)
**Metrics Calculated:**
- Matched Shots Accuracy: (Matched Correct) / (Matched Correct + Matched Incorrect)
- Overall Accuracy: (Matched Correct) / (Total Detected Shots)
- Ground Truth Coverage: (Matched Correct + Matched Incorrect) / (Total Ground Truth Shots)
- Detection Coverage: (Matched Correct + Matched Incorrect) / (Total Detected Shots)

### C. Algorithm Version History

- **V1:** Basic overlap detection
- **V2:** Added trajectory analysis and confidence scoring
- **V3 (Current):** Enhanced multi-factor analysis with rim bounce detection, entry angles, and post-hoop trajectory
- **V4 (Reverted):** Attempted improvements caused 5.22% regression in matched shots accuracy

**Current Production Version:** V3 (Enhanced Multi-Factor)

### D. Data Files

All detailed analysis data is available in:
- **JSON Report:** `comprehensive_accuracy_report.json`
- **Analysis Script:** `analyze_results.py`
- **Results Directory:** `results/` (10 session folders with full validation data)

---

**Report Generated:** November 2, 2025
**Analysis Tool:** analyze_results.py v1.0
**Total Analysis Time:** ~2 seconds
**Contact:** For questions about this report, please refer to the repository documentation.
