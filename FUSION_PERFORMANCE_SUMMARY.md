## Dual-Angle Shot Detection Summary

### Far-Angle (Farright) Line-Intersection Detector
- **Implementation**: `Uball_far_angle_shot_detection/simple_line_intersection_test.py`.
- **Execution**: `python3 simple_line_intersection_test.py --mode full --video "09-22/Game-2/game2_farright.mp4" --model "runs/detect/basketball_yolo11n2/weights/best.pt" --output_dir "results/simple_line_test_v4_game2" --ground_truth "results/game2-farright_d795805c-17be-40f5-b56f-e02002363d7d/ground_truth.json"`.
- **Key Outputs**: `results/simple_line_test_v4_game{1,2,3}/detection_results.json`.
- **Matched-Shot Accuracy** (after sync: Game 1 offset 0 s, Game 2 offset 0 s, Game 3 offset −3 s):  
  - Game 1 (09-23): 57 correct of 67 matched (85.1%).  
  - Game 2 (09-22): 29 correct of 49 matched (59.2%).  
  - Game 3 (09-22): 51 correct of 68 matched (75.0%).
- **Failure Themes**:
  - `complete_pass_through` and `entered_from_top` label rim-outs or free throws as made when post-hoop motion is upward.
  - `no_top_crossing` drops true makes when the ball track slips near the hoop.
  - Vertical depth gate (`MIN/MAX_BALL_HOOP_RATIO`) rejects clean swishes on steep arcs.
- **Improvements**:
  - Require continued downward velocity (or disappearance below rim) before accepting `complete_pass_through/entered_from_top`.
  - Detect lateral exits and up-bounces (>20 px) to override to missed.
  - Add tracker re-seed/zone widening for fast break pull-ups and baseline drives.

### Near-Angle (Nearleft) Overlap Detector
- **Session Artifacts**: `Uball_near_angle_shot_detection/results/09-23(1-NL)_*/`, `09-22(2-NL)_*/`, `09-22(3-NL)_*/`.
- **Matched-Shot Accuracy** (after offsets: Game 1 −0.8 s, Game 2 −3.5 s, Game 3 −4.7 s):
  - Game 1: 62/71 matched (87.3%).
  - Game 2: 50/54 matched (92.6%).
  - Game 3: 67/74 matched (90.5%).
- **Primary Misses**:
  - `perfect_overlap_*` and `fast_clean_swish` mislabel rim-outs, free throws, and contested layups as made.
  - `insufficient_overlap` fires on edge-on corner threes when the ball is partially occluded.
- **Improvements**:
  - Post-hoop analysis: validate netward continuation and flag upward motion as rim bounce-outs.
  - Adaptive overlap window or auxiliary cue (ball trajectory, depth) for side-on threes.
  - Confidence-aware downgrade: if near confidence <0.85, consult far-angle verdict during fusion.

### Fusion Considerations
- **Offsets** (sec): Near −0.8/−3.5/−4.7 by game; Far −3.0 for 09-22 Game 3.
- **Ground-Truth Coverage (77 + 57 + 79 = 213 shots)**:
  - Near-only correct: 20 shots (rim scrums, post plays, free throws).
  - Far-only correct: 6 shots (deep wing threes, quick pull-ups).
  - Both wrong: 9 shots (IDs `0f1c87d2`, `fe63d19f`, `6a5c12c6`, `0046c4d4`, `fd57aa72`, `16de9311`, etc.).
  - Both missed: 7 shots (camera pans, congested layups/free throws).
- **Fusion Roadmap**:
  - Arbitration rules: trust near when far claims `complete_pass_through/entered_from_top` but near shows rim-bounce cues; trust far when near reports `insufficient_overlap` with low confidence and far enforces `no_top_crossing`.
  - Bounce detection: share a rim-plane check to veto “made” when any angle detects upward rebound within 0.5 s.
  - Tracking recovery: inject clock/whistle cues to re-init tracking after pans (covers both-missed scenarios).
  - Confidence gating: suppress far-only detections below 0.9 when near has no supporting activity within ±2 s.

### Next Steps
1. Patch far logic to include downward-velocity confirmation and bounce override.
2. Extend near overlap heuristics with net-exit validation or far-angle assist.
3. Encode sync offsets in config so validators and fusion always align timestamps.
4. Update fusion engine to leverage angle-specific failure reasons and handle “both wrong” IDs explicitly.



Incorrect Matches (per game)
Game 1 – 09‑23
Near angle (9 mismatches)
379.8 s GT miss → detected made (fast_clean_swish, 0.75)
938.9 s GT miss → detected made (perfect_overlap_layup, 0.95)
1404.7 s GT miss → detected made (perfect_overlap_steep_entry, 0.85)
1642.5 s GT make → detected miss (steep_entry_bounce_back, 0.85)
1698.6 s GT miss → detected made (perfect_overlap_steep_entry, 0.85)
2289.7 s GT make → detected miss (steep_entry_bounce_back, 0.85)
2554.6 s GT miss → detected made (perfect_overlap, 0.75)
2637.0 s GT make → detected miss (insufficient_overlap, 0.80)
2860.9 s GT make → detected miss (insufficient_overlap, 0.65)
Far angle (10 mismatches)
26.8 s make → miss (no_top_crossing)
91.7 s miss → made (entered_from_top)
125.5 s miss → made (complete_pass_through)
243.9 s make → miss (no_top_crossing)
494.1 s miss → made (complete_pass_through)
938.9 s miss → made (entered_from_top)
1055.1 s miss → made (complete_pass_through)
1548.8 s miss → made (complete_pass_through)
1937.4 s miss → made (complete_pass_through)
2250.0 s miss → made (complete_pass_through)
Game 2 – 09‑22
Near angle (4 mismatches)
37.7 s FT miss → made (perfect_overlap, 0.75)
973.9 s FT miss → made (perfect_overlap_steep_entry, 0.85)
1836.0 s 3PT make → miss (insufficient_overlap, 0.80)
2895.0 s FT miss → made (perfect_overlap_steep_entry, 0.85)
Far angle (20 mismatches)
37.7 s miss → made (entered_from_top)
584.8 s miss → made (complete_pass_through)
609.6 s miss → made (complete_pass_through)
682.7 s make → miss (no_top_crossing)
902.8 s make → miss (wrong_depth_or_direction)
973.9 s miss → made (complete_pass_through)
1114.9 s make → miss (no_top_crossing)
1259.3 s miss → made (entered_from_top)
1275.5 s make → miss (wrong_depth_or_direction)
1615.7 s make → miss (wrong_depth_or_direction)
1644.2 s miss → made (complete_pass_through)
1696.9 s miss → made (complete_pass_through)
1710.6 s miss → made (entered_from_top)
1954.9 s miss → made (entered_from_top)
2001.2 s miss → made (complete_pass_through)
2373.7 s make → miss (wrong_depth_or_direction)
2397.0 s make → miss (wrong_depth_or_direction)
2630.3 s miss → made (entered_from_top)
2895.0 s miss → made (entered_from_top)
3125.2 s miss → made (complete_pass_through)
Game 3 – 09‑22
Near angle (7 mismatches)
330.3 s miss → made (perfect_overlap_layup, 0.95)
583.8 s make → miss (insufficient_overlap, 0.65)
1120.9 s miss → made (perfect_overlap_steep_entry, 0.85)
2257.3 s miss → made (perfect_overlap_steep_entry, 0.85)
2836.2 s make → miss (insufficient_overlap, 0.80)
2886.2 s miss → made (fast_clean_swish, 0.75)
2924.8 s miss → made (perfect_overlap_steep_entry, 0.85)
Far angle (17 mismatches)
149.7 s make → miss (no_top_crossing)
169.0 s miss → made (complete_pass_through)
264.4 s make → miss (rim_bounce_out)
283.8 s miss → made (complete_pass_through)
330.3 s miss → made (entered_from_top)
396.7 s make → miss (no_top_crossing)
437.3 s make → miss (wrong_depth_or_direction)
698.7 s make → miss (no_top_crossing)
769.7 s make → miss (no_top_crossing)
984.8 s miss → made (entered_from_top)
1089.2 s miss → made (complete_pass_through)
1120.9 s miss → made (entered_from_top)
2019.1 s make → miss (no_top_crossing)
2257.3 s miss → made (entered_from_top)
2836.2 s make → miss (no_top_crossing)
2924.8 s miss → made (complete_pass_through)
2936.1 s make → miss (no_top_crossing)