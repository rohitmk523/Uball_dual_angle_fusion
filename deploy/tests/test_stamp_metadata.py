"""Unit tests for the `_stamp_metadata` post-processing step in the
fusion entrypoint — focused on the UBA-238 hoop_side stamping.

The function:
  * Sets session_info.{model_version, side, hoop_side, *_model_sha256}
  * Adds `hoop_side` to every shot in `shots` (unless already set)

These tests stay free of S3, boto3, and the actual fusion run — they
just exercise the JSON read/write transformation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the entrypoint module importable.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "deploy"))

import entrypoint as ep  # noqa: E402


# ---------------------------------------------------------------- fixtures
@pytest.fixture
def detection_file(tmp_path: Path) -> Path:
    p = tmp_path / "detection_results.json"
    p.write_text(json.dumps({
        "session_info": {"existing_field": "kept"},
        "shots": [
            {"timestamp_seconds": 12.3, "outcome": "made",   "fusion_confidence": 0.91},
            {"timestamp_seconds": 45.6, "outcome": "missed", "fusion_confidence": 0.62},
            {"timestamp_seconds": 78.9, "outcome": "made",   "fusion_confidence": 0.85},
        ],
    }))
    return p


# ---------------------------------------------------------------- tests
def test_side_A_stamps_right_hoop_on_every_shot(detection_file: Path):
    ep._stamp_metadata(
        detection_file, model_version="v1", side="A",
        near_sha="abc", far_sha="def",
    )
    data = json.loads(detection_file.read_text())

    assert data["session_info"]["side"] == "A"
    assert data["session_info"]["hoop_side"] == "right"
    assert data["session_info"]["model_version"] == "v1"
    assert data["session_info"]["near_model_sha256"] == "abc"
    assert data["session_info"]["far_model_sha256"] == "def"
    assert data["session_info"]["existing_field"] == "kept"  # session_info preserved

    for shot in data["shots"]:
        assert shot["hoop_side"] == "right"


def test_side_B_stamps_left_hoop_on_every_shot(detection_file: Path):
    ep._stamp_metadata(
        detection_file, model_version="v1", side="B",
        near_sha=None, far_sha=None,
    )
    data = json.loads(detection_file.read_text())

    assert data["session_info"]["side"] == "B"
    assert data["session_info"]["hoop_side"] == "left"
    # Optional sha fields shouldn't be added when None
    assert "near_model_sha256" not in data["session_info"]
    assert "far_model_sha256" not in data["session_info"]

    for shot in data["shots"]:
        assert shot["hoop_side"] == "left"


def test_does_not_overwrite_existing_hoop_side(tmp_path: Path):
    """Forward-compat: a future per-shot hoop detector could set hoop_side
    to a different value than the side-derived default. Don't clobber it."""
    p = tmp_path / "detection_results.json"
    p.write_text(json.dumps({
        "shots": [
            {"timestamp_seconds": 1.0, "hoop_side": "left",  "outcome": "made"},   # explicit
            {"timestamp_seconds": 2.0,                       "outcome": "missed"}, # implicit
            {"timestamp_seconds": 3.0, "hoop_side": "right", "outcome": "made"},   # explicit
        ],
    }))

    ep._stamp_metadata(p, model_version="v1", side="A", near_sha=None, far_sha=None)
    data = json.loads(p.read_text())

    # Shot 0 keeps its explicit "left" even though side=A would have stamped "right".
    assert data["shots"][0]["hoop_side"] == "left"
    # Shot 1 was implicit → gets side-derived "right".
    assert data["shots"][1]["hoop_side"] == "right"
    # Shot 2 keeps its explicit "right".
    assert data["shots"][2]["hoop_side"] == "right"


def test_empty_shots_list_is_safe(tmp_path: Path):
    p = tmp_path / "detection_results.json"
    p.write_text(json.dumps({"shots": []}))

    ep._stamp_metadata(p, model_version="v1", side="A", near_sha=None, far_sha=None)

    data = json.loads(p.read_text())
    assert data["session_info"]["hoop_side"] == "right"
    assert data["shots"] == []


def test_missing_shots_key_is_safe(tmp_path: Path):
    p = tmp_path / "detection_results.json"
    p.write_text(json.dumps({}))

    ep._stamp_metadata(p, model_version="v1", side="B", near_sha=None, far_sha=None)

    data = json.loads(p.read_text())
    assert data["session_info"]["hoop_side"] == "left"


def test_invalid_side_skips_hoop_stamping(tmp_path: Path):
    """If SIDE is somehow not 'A' or 'B' (shouldn't happen — main() already
    rejects bad values — but defend against it). Should not crash, and
    should not add a wrong hoop_side."""
    p = tmp_path / "detection_results.json"
    p.write_text(json.dumps({
        "shots": [{"timestamp_seconds": 1.0, "outcome": "made"}],
    }))

    ep._stamp_metadata(p, model_version="v1", side="UNKNOWN",
                       near_sha=None, far_sha=None)

    data = json.loads(p.read_text())
    assert data["session_info"]["side"] == "UNKNOWN"
    assert "hoop_side" not in data["session_info"]
    assert "hoop_side" not in data["shots"][0]
