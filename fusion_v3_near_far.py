#!/usr/bin/env python3
"""
Fusion of near-angle overlap detector with far-angle V3 line-intersection detector.

This script aligns detections using empirically measured offsets, arbitrates disagreements
with hand-tuned heuristics, and reports matched-shot accuracy against ground truth.

Usage:
    python fusion_v3_near_far.py              # process all configured games
    python fusion_v3_near_far.py --game game1 # limit to a single game

Outputs per game:
    fusion_outputs/{game_name}_fusion.json    # fused shot-by-shot breakdown
    Console summary with matched/correct counts for near, far, and fused results
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TOLERANCE_SECONDS = 2.0
OUTPUT_DIR = Path("fusion_outputs")


@dataclass
class SessionConfig:
    name: str
    ground_truth: Path
    near_results: Path
    far_results: Path
    near_offset: float
    far_offset: float


CONFIGS: Dict[str, SessionConfig] = {
    "game1": SessionConfig(
        name="09-23 Game 1",
        ground_truth=Path(
            "Uball_far_angle_shot_detection/results/"
            "game1-farright_b8c98465-3d89-4cbf-be78-1740432be0ee/ground_truth.json"
        ),
        near_results=Path(
            "Uball_near_angle_shot_detection/results/"
            "09-23(1-NL)_fc2a92db-5a81-4f2a-acda-3e86b9098356/detection_results.json"
        ),
        far_results=Path(
            "Uball_far_angle_shot_detection/results/"
            "simple_line_test_v3_game1/detection_results.json"
        ),
        near_offset=-0.8,
        far_offset=-0.1,
    ),
    "game2": SessionConfig(
        name="09-22 Game 2",
        ground_truth=Path(
            "Uball_far_angle_shot_detection/results/"
            "game2-farright_d795805c-17be-40f5-b56f-e02002363d7d/ground_truth.json"
        ),
        near_results=Path(
            "Uball_near_angle_shot_detection/results/"
            "09-22(2-NL)_b85b7d6e-6b5d-4ca4-a6c8-614c3e9c1684/detection_results.json"
        ),
        far_results=Path(
            "Uball_far_angle_shot_detection/results/"
            "simple_line_test_v3_game2/detection_results.json"
        ),
        near_offset=-3.5,
        far_offset=-0.4,
    ),
    "game3": SessionConfig(
        name="09-22 Game 3",
        ground_truth=Path(
            "Uball_near_angle_shot_detection/results/"
            "09-22(3-NL)_d2a451bb-c5c5-4b20-87bd-3e073fabf277/ground_truth.json"
        ),
        near_results=Path(
            "Uball_near_angle_shot_detection/results/"
            "09-22(3-NL)_d2a451bb-c5c5-4b20-87bd-3e073fabf277/detection_results.json"
        ),
        far_results=Path(
            "Uball_far_angle_shot_detection/results/"
            "simple_line_test_v3_game3/detection_results.json"
        ),
        near_offset=-4.7,
        far_offset=-2.9,
    ),
}


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------
def load_json(path: Path) -> Dict:
    with path.open("r") as fh:
        return json.load(fh)


def load_shots(path: Path) -> List[Dict]:
    data = load_json(path)
    shots = data.get("shots", data)
    for shot in shots:
        if "timestamp_seconds" in shot:
            shot["timestamp_seconds"] = float(shot["timestamp_seconds"])
        elif "timestamp" in shot:
            try:
                shot["timestamp_seconds"] = float(shot["timestamp"])
            except (ValueError, TypeError):
                continue
    return shots


def load_ground_truth(path: Path) -> List[Dict]:
    gt = load_json(path)
    for shot in gt:
        shot["timestamp_seconds"] = float(shot["timestamp_seconds"])
    return gt


# ---------------------------------------------------------------------------
# Matching and fusion heuristics
# ---------------------------------------------------------------------------
def match_shots(
    detections: List[Dict], ground_truth: List[Dict], offset: float
) -> Dict[int, Dict]:
    """Greedy one-to-one matching using timestamp proximity."""
    gt_used = set()
    matches: Dict[int, Dict] = {}

    for det_idx, detection in sorted(
        enumerate(detections), key=lambda x: x[1].get("timestamp_seconds", float("inf"))
    ):
        ts = detection.get("timestamp_seconds")
        if ts is None:
            continue

        adjusted_ts = ts + offset
        detection["adjusted_timestamp"] = adjusted_ts

        best_idx: Optional[int] = None
        best_diff = float("inf")

        for gt_idx, gt_shot in enumerate(ground_truth):
            if gt_idx in gt_used:
                continue
            diff = abs(adjusted_ts - gt_shot["timestamp_seconds"])
            if diff <= TOLERANCE_SECONDS and diff < best_diff:
                best_idx = gt_idx
                best_diff = diff

        if best_idx is not None:
            matches[best_idx] = {
                "det_index": det_idx,
                "detection": detection,
                "time_diff": best_diff,
            }
            gt_used.add(best_idx)

    return matches


def get_confidence(det: Optional[Dict]) -> float:
    if not det:
        return 0.0
    conf = det.get("decision_confidence")
    if conf is None:
        conf = det.get("confidence", 0.0)
    return float(conf or 0.0)


def reason_contains(det: Optional[Dict], keywords: Tuple[str, ...]) -> bool:
    if not det:
        return False
    reason = (det.get("outcome_reason") or "").lower()
    return any(key in reason for key in keywords)


def near_detects_rim_bounce(det: Optional[Dict]) -> bool:
    if not det:
        return False
    if det.get("is_rim_bounce"):
        return True
    pha = det.get("post_hoop_analysis") or {}
    if pha.get("ball_bounces_back"):
        return True
    if pha.get("upward_movement", 0) and pha.get("upward_movement", 0) > 20:
        return True
    return False


def fuse_outcome(
    near_match: Optional[Dict], far_match: Optional[Dict]
) -> Optional[Dict]:
    """Arbitrate between near and far detections."""
    near_det = near_match["detection"] if near_match else None
    far_det = far_match["detection"] if far_match else None
    near_out = near_det.get("outcome") if near_det else None
    far_out = far_det.get("outcome") if far_det else None

    if near_out is None and far_out is None:
        return None
    if near_out is not None and far_out is None:
        return {"outcome": near_out, "source": "near_only"}
    if far_out is not None and near_out is None:
        return {"outcome": far_out, "source": "far_only"}
    if near_out == far_out:
        return {"outcome": near_out, "source": "agreement"}

    near_conf = get_confidence(near_det)
    far_conf = get_confidence(far_det)

    near_reason_fp = reason_contains(
        near_det, ("perfect_overlap", "fast_clean_swish")
    )
    near_reason_uncertain = reason_contains(
        near_det, ("insufficient_overlap", "steep_entry_bounce_back")
    )
    near_low_conf = near_conf < 0.8
    near_rim_bounce = near_detects_rim_bounce(near_det)

    far_reason_risky_make = reason_contains(
        far_det, ("complete_pass_through", "entered_from_top")
    )
    far_reason_confident_miss = reason_contains(
        far_det, ("no_top_crossing", "wrong_depth_or_direction", "rim_bounce_out")
    )
    far_high_conf = far_conf >= 0.9

    if near_out == "made" and far_out == "missed":
        if near_low_conf and far_reason_confident_miss and far_conf >= 0.9:
            return {
                "outcome": "missed",
                "source": "far_override",
                "note": "near_low_conf",
            }
        return {"outcome": "made", "source": "near_priority"}

    if near_out == "missed" and far_out == "made":
        if near_rim_bounce:
            return {"outcome": "missed", "source": "near_rim_bounce"}
        if near_reason_uncertain or near_low_conf:
            far_strong_make = reason_contains(far_det, ("complete_pass_through",)) and far_conf >= 0.9
            far_conf_advantage = far_conf - near_conf >= 0.2
            if far_strong_make:
                return {
                    "outcome": "made",
                    "source": "far_override",
                    "note": "near_uncertain_far_strong_make",
                }
            if far_conf_advantage and not reason_contains(far_det, ("entered_from_top",)):
                return {
                    "outcome": "made",
                    "source": "far_override",
                    "note": "far_confidence_edge",
                }
        if far_reason_risky_make and not near_reason_uncertain and near_conf >= far_conf:
            return {
                "outcome": "missed",
                "source": "near_override",
                "note": "far_risky_make",
            }
        return {"outcome": "missed", "source": "near_priority"}

    # Fallback: prefer higher confidence
    return {"outcome": near_out, "source": "near_fallback"}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate_session(config: SessionConfig) -> Dict:
    ground_truth = load_ground_truth(config.ground_truth)
    near_shots = load_shots(config.near_results)
    far_shots = load_shots(config.far_results)

    near_matches = match_shots(near_shots, ground_truth, config.near_offset)
    far_matches = match_shots(far_shots, ground_truth, config.far_offset)

    fused_records = []
    stats = {
        "near": {"matched": 0, "correct": 0},
        "far": {"matched": 0, "correct": 0},
        "fused": {"matched": 0, "correct": 0},
        "both_missing": 0,
    }

    for idx, gt_shot in enumerate(ground_truth):
        near_match = near_matches.get(idx)
        far_match = far_matches.get(idx)

        if near_match:
            stats["near"]["matched"] += 1
            if near_match["detection"].get("outcome") == gt_shot["outcome"]:
                stats["near"]["correct"] += 1
        if far_match:
            stats["far"]["matched"] += 1
            if far_match["detection"].get("outcome") == gt_shot["outcome"]:
                stats["far"]["correct"] += 1

        fused = fuse_outcome(near_match, far_match)
        correct = None
        if fused and fused["outcome"] is not None:
            stats["fused"]["matched"] += 1
            correct = fused["outcome"] == gt_shot["outcome"]
            if correct:
                stats["fused"]["correct"] += 1
        else:
            stats["both_missing"] += 1

        fused_records.append(
            {
                "ground_truth": gt_shot,
                "near_detection": near_match["detection"]
                if near_match
                else None,
                "far_detection": far_match["detection"] if far_match else None,
                "near_time_diff": near_match["time_diff"] if near_match else None,
                "far_time_diff": far_match["time_diff"] if far_match else None,
                "fused_decision": fused,
                "is_correct": correct,
            }
        )

    total_gt = len(ground_truth)
    for key in ("near", "far", "fused"):
        matched = stats[key]["matched"]
        stats[key]["accuracy"] = (
            stats[key]["correct"] / matched * 100 if matched else 0.0
        )
        stats[key]["coverage"] = matched / total_gt * 100 if total_gt else 0.0

    stats["ground_truth_total"] = total_gt
    return {"config": config, "stats": stats, "records": fused_records}


def save_results(session_key: str, evaluation: Dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{session_key}_fusion.json"
    payload = {
        "session": evaluation["config"].name,
        "near_offset": evaluation["config"].near_offset,
        "far_offset": evaluation["config"].far_offset,
        "stats": evaluation["stats"],
        "records": evaluation["records"],
    }
    with output_path.open("w") as fh:
        json.dump(payload, fh, indent=2)


def print_summary(session_key: str, evaluation: Dict) -> None:
    cfg = evaluation["config"]
    stats = evaluation["stats"]
    print(f"\n=== {cfg.name} ({session_key}) ===")
    print(f"Ground truth shots: {stats['ground_truth_total']}")
    for label in ("near", "far", "fused"):
        s = stats[label]
        print(
            f"{label.capitalize():>6}: matched {s['matched']:>3} | "
            f"correct {s['correct']:>3} | "
            f"accuracy {s['accuracy']:.1f}% | coverage {s['coverage']:.1f}%"
        )
    print(f"Both detectors missing: {stats['both_missing']}")
    print(f"Results saved to: {OUTPUT_DIR / f'{session_key}_fusion.json'}")


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fuse near and far detections (V3).")
    parser.add_argument(
        "--game",
        choices=CONFIGS.keys(),
        help="Limit processing to a single game key (game1, game2, or game3).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sessions = [args.game] if args.game else CONFIGS.keys()

    for session_key in sessions:
        config = CONFIGS[session_key]
        evaluation = evaluate_session(config)
        save_results(session_key, evaluation)
        print_summary(session_key, evaluation)


if __name__ == "__main__":
    main()

