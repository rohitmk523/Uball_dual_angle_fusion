#!/usr/bin/env python3
"""AWS Batch entrypoint for the uball-cv-fusion container.

Flow:
  1. Read env config (see ENV block below).
  2. Fetch MANIFEST.json + versioned model weights from S3 (cached in /tmp
     across warm Batch invocations).
  3. Download the two 1080p angle videos from S3.
  4. Invoke dual_angle_fusion.py with --skip_video (no Supabase GT lookup).
  5. Retry up to 3x on subprocess failure (exponential backoff).
  6. Stamp session_info with model version + SHAs + side tag.
  7. Upload detection_results.json + session_summary.json to RESULT_S3_PREFIX.

For local testing, set LOCAL_MODE=true plus LOCAL_{NEAR,FAR}_{VIDEO,MODEL} to
skip all S3 traffic and write results under /app/results/.

ENV (required in production):
  NEAR_S3_KEY               S3 key of the "near" 1080p video
  FAR_S3_KEY                S3 key of the "far" 1080p video
  GAME_ID                   Game UUID (Supabase games.id)
  SIDE                      "A" (FR+NR) or "B" (FL+NL)
  INPUTS_BUCKET             S3 bucket holding the 1080p videos
  RESULTS_BUCKET            S3 bucket to write detection JSON into
  MODELS_BUCKET             S3 bucket holding versioned YOLOv11 weights
  RESULT_S3_PREFIX          Key prefix to upload results under (no leading /)

ENV (optional):
  AWS_REGION                default: us-east-1
  MODEL_VERSION             default: v1
  NEAR_MODEL_KEY            default: yolov11/{MODEL_VERSION}/near/best.pt
  FAR_MODEL_KEY             default: yolov11/{MODEL_VERSION}/far/best.pt
  MODELS_MANIFEST_KEY       default: yolov11/{MODEL_VERSION}/MANIFEST.json
  TEMPORAL_WINDOW           default: 3.0 (seconds, passed to fusion)
  PRIORITIZE_COVERAGE       default: false (passed to fusion as --prioritize_coverage)

ENV (local-mode overrides — any one of these triggers local mode):
  LOCAL_MODE=true           skip all S3 uploads; write results to FUSION_APP_DIR/results
  LOCAL_NEAR_VIDEO          local path to near-angle MP4
  LOCAL_FAR_VIDEO           local path to far-angle MP4
  LOCAL_NEAR_MODEL          local path to near YOLO weights
  LOCAL_FAR_MODEL           local path to far YOLO weights
  START_TIME                fusion --start_time (seconds, optional)
  END_TIME                  fusion --end_time (seconds, optional, handy for smoke tests)

ENV (container/host binding — defaults match Dockerfile layout; override for host runs):
  FUSION_APP_DIR            default: /app — where dual_angle_fusion.py + sub-detectors live
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [cv-fusion] %(message)s",
)
log = logging.getLogger("cv-fusion")


# ---------------------------------------------------------------------------
# env helpers
# ---------------------------------------------------------------------------
def _env(key: str, default: Optional[str] = None, *, required: bool = False) -> Optional[str]:
    val = os.environ.get(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


IS_LOCAL = _env_bool("LOCAL_MODE")
FUSION_APP_DIR = Path(_env("FUSION_APP_DIR", "/app"))
FUSION_SCRIPT = FUSION_APP_DIR / "dual_angle_fusion.py"
RESULTS_DIR = FUSION_APP_DIR / "results"


# ---------------------------------------------------------------------------
# S3 (only loaded when not in LOCAL_MODE to avoid boto dep at test time)
# ---------------------------------------------------------------------------
def _s3_client():
    import boto3
    return boto3.client("s3", region_name=_env("AWS_REGION", "us-east-1"))


# ---------------------------------------------------------------------------
# file helpers
# ---------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _s3_download(bucket: str, key: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("s3://%s/%s -> %s", bucket, key, dest)
    _s3_client().download_file(bucket, key, str(dest))


def _s3_upload(src: Path, bucket: str, key: str) -> None:
    log.info("%s -> s3://%s/%s", src, bucket, key)
    _s3_client().upload_file(str(src), bucket, key)


# ---------------------------------------------------------------------------
# model weight acquisition
# ---------------------------------------------------------------------------
MODELS_CACHE = Path("/tmp/models")


def _fetch_manifest(bucket: str, key: str) -> dict:
    try:
        dest = MODELS_CACHE / "MANIFEST.json"
        _s3_download(bucket, key, dest)
        return json.loads(dest.read_text())
    except Exception as e:
        log.warning("manifest fetch failed (%s); proceeding without SHA verification", e)
        return {}


def _fetch_model(name: str, bucket: str, key: str, expected_sha: Optional[str]) -> Path:
    """Download + verify a model weight. Cached by filename under /tmp/models/{name}."""
    cache_dir = MODELS_CACHE / name
    cache_dir.mkdir(parents=True, exist_ok=True)
    local = cache_dir / Path(key).name

    if local.exists() and expected_sha:
        if _sha256(local) == expected_sha:
            log.info("model cache hit: %s (%s)", local, expected_sha[:12])
            return local
        log.warning("cached %s sha mismatch; re-downloading", local)

    _s3_download(bucket, key, local)
    actual = _sha256(local)
    if expected_sha and actual != expected_sha:
        raise RuntimeError(
            f"model sha mismatch for {name}: expected={expected_sha} got={actual}"
        )
    log.info("model ready: %s (sha256=%s)", local, actual[:12])
    return local


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def _run_fusion(near_video: Path, far_video: Path, near_model: Path, far_model: Path,
                game_id: str, temporal_window: str, prioritize_coverage: bool,
                start_time: Optional[str], end_time: Optional[str]) -> None:
    cmd = [
        "python3", str(FUSION_SCRIPT),
        "--near_video", str(near_video),
        "--far_video", str(far_video),
        "--game_id", game_id,
        "--near_model", str(near_model),
        "--far_model", str(far_model),
        "--skip_video",
        "--temporal_window", temporal_window,
    ]
    if start_time is not None:
        cmd.extend(["--start_time", start_time])
    if end_time is not None:
        cmd.extend(["--end_time", end_time])
    if prioritize_coverage:
        cmd.append("--prioritize_coverage")
    log.info("invoke: %s", " ".join(cmd))

    last_err: Optional[subprocess.CalledProcessError] = None
    for attempt in range(1, 4):
        try:
            subprocess.run(cmd, cwd=str(FUSION_APP_DIR), check=True)
            log.info("fusion completed (attempt %d)", attempt)
            return
        except subprocess.CalledProcessError as e:
            last_err = e
            tail = (e.stderr or "")[-500:] if e.stderr else ""
            log.warning("attempt %d failed (rc=%d): %s", attempt, e.returncode, tail)
            if attempt < 3:
                time.sleep(2 ** attempt)  # 2s, 4s backoff
    assert last_err is not None
    raise RuntimeError(
        f"dual_angle_fusion failed after 3 attempts: rc={last_err.returncode}"
    )


def _find_latest_results_dir(root: Path) -> Path:
    if not root.exists():
        raise RuntimeError(f"results/ dir missing after fusion: {root}")
    dirs = [p for p in root.iterdir() if p.is_dir()]
    if not dirs:
        raise RuntimeError(f"No run dirs in {root}")
    return max(dirs, key=lambda p: p.stat().st_mtime)


# UBA-238: each near-angle camera is physically fixed on one hoop, so the
# hoop a shot occurred at is fully determined by which side processed it.
# Side A processes FR+NR (the "right" pair) → right hoop.
# Side B processes FL+NL (the "left" pair)  → left hoop.
_SIDE_TO_HOOP = {"A": "right", "B": "left"}


def _stamp_metadata(detection_json: Path, *, model_version: str, side: str,
                    near_sha: Optional[str], far_sha: Optional[str]) -> None:
    """Stamp session-level metadata + per-shot `hoop_side`.

    Per UBA-238 (3.6), each shot gets a `hoop_side` field derived from the
    SIDE env. The merge container reads this to attribute the shot to the
    correct team (via plays_sync.py's existing `team="left"|"right"` →
    `leftTeam`/`rightTeam` mapping). No ML model change — pure post-process.
    """
    try:
        data = json.loads(detection_json.read_text())

        # ---- session-level metadata ----
        info = data.setdefault("session_info", {})
        info["model_version"] = model_version
        info["side"] = side
        hoop_side = _SIDE_TO_HOOP.get(side)
        if hoop_side:
            info["hoop_side"] = hoop_side
        if near_sha:
            info["near_model_sha256"] = near_sha
        if far_sha:
            info["far_model_sha256"] = far_sha

        # ---- per-shot hoop_side stamping (UBA-238) ----
        stamped = 0
        if hoop_side:
            for shot in data.get("shots", []) or []:
                # Don't overwrite a hoop_side already present (forward-compat
                # for a future per-shot detector that could override this).
                if shot.get("hoop_side") in ("left", "right"):
                    continue
                shot["hoop_side"] = hoop_side
                stamped += 1

        detection_json.write_text(json.dumps(data, indent=2))
        log.info(
            "stamped session_info with model_version=%s side=%s hoop_side=%s; "
            "set hoop_side on %d shot(s)",
            model_version, side, hoop_side, stamped,
        )
    except Exception as e:
        log.warning("failed to stamp metadata (%s) — results still uploaded", e)


def main() -> int:
    # Ensure the metrics module is importable from /app/deploy/.
    sys.path.insert(0, str(FUSION_APP_DIR / "deploy"))
    import cv_metrics

    _fusion_started_at = time.time()

    # Required inputs (both modes)
    game_id = _env("GAME_ID", required=True)
    side = _env("SIDE", required=True)
    if side not in ("A", "B"):
        raise RuntimeError(f"SIDE must be 'A' or 'B', got: {side}")

    # Optional knobs
    model_version = _env("MODEL_VERSION", "v1")
    temporal_window = _env("TEMPORAL_WINDOW", "3.0")
    prioritize_coverage = _env_bool("PRIORITIZE_COVERAGE")
    start_time = _env("START_TIME")
    end_time = _env("END_TIME")

    log.info("start game_id=%s side=%s model_version=%s local_mode=%s",
             game_id, side, model_version, IS_LOCAL)

    near_sha: Optional[str] = None
    far_sha: Optional[str] = None

    if IS_LOCAL:
        # ---------- local mode ----------
        near_video = Path(_env("LOCAL_NEAR_VIDEO", required=True))
        far_video = Path(_env("LOCAL_FAR_VIDEO", required=True))
        near_model = Path(_env("LOCAL_NEAR_MODEL", required=True))
        far_model = Path(_env("LOCAL_FAR_MODEL", required=True))
        for p in (near_video, far_video, near_model, far_model):
            if not p.exists():
                raise RuntimeError(f"local path does not exist: {p}")
    else:
        # ---------- S3 / production mode ----------
        near_s3_key = _env("NEAR_S3_KEY", required=True)
        far_s3_key = _env("FAR_S3_KEY", required=True)
        inputs_bucket = _env("INPUTS_BUCKET", required=True)
        results_bucket = _env("RESULTS_BUCKET", required=True)
        models_bucket = _env("MODELS_BUCKET", required=True)
        result_prefix = _env("RESULT_S3_PREFIX", required=True).rstrip("/")

        near_model_key = _env("NEAR_MODEL_KEY", f"yolov11/{model_version}/near/best.pt")
        far_model_key = _env("FAR_MODEL_KEY", f"yolov11/{model_version}/far/best.pt")
        manifest_key = _env("MODELS_MANIFEST_KEY", f"yolov11/{model_version}/MANIFEST.json")

        manifest = _fetch_manifest(models_bucket, manifest_key)
        near_sha = manifest.get("near", {}).get("sha256")
        far_sha = manifest.get("far", {}).get("sha256")

        near_model = _fetch_model("near", models_bucket, near_model_key, near_sha)
        far_model = _fetch_model("far", models_bucket, far_model_key, far_sha)

        inputs_dir = Path("/tmp/inputs")
        inputs_dir.mkdir(parents=True, exist_ok=True)
        near_video = inputs_dir / Path(near_s3_key).name
        far_video = inputs_dir / Path(far_s3_key).name
        _s3_download(inputs_bucket, near_s3_key, near_video)
        _s3_download(inputs_bucket, far_s3_key, far_video)

    # ---------- run fusion ----------
    _run_fusion(
        near_video=near_video,
        far_video=far_video,
        near_model=near_model,
        far_model=far_model,
        game_id=game_id,
        temporal_window=temporal_window,
        prioritize_coverage=prioritize_coverage,
        start_time=start_time,
        end_time=end_time,
    )

    # ---------- collect outputs ----------
    run_dir = _find_latest_results_dir(RESULTS_DIR)
    detection_json = run_dir / "detection_results.json"
    if not detection_json.exists():
        raise RuntimeError(f"detection_results.json missing: {detection_json}")

    _stamp_metadata(detection_json,
                    model_version=model_version, side=side,
                    near_sha=near_sha, far_sha=far_sha)

    # ---------- metrics (before upload so they fire even if S3 is flaky) ----------
    try:
        import json as _json
        _payload = _json.loads(detection_json.read_text())
        shots = _payload.get("shots", []) or []
        dims = {"Stage": "fusion", "Side": side}
        cv_metrics.emit("ShotsDetectedPerGame", len(shots),
                        dimensions=dims)
        if shots:
            conf_vals = [float(s.get("fusion_confidence", 0)) for s in shots]
            cv_metrics.emit("MeanConfidence", sum(conf_vals) / len(conf_vals),
                            unit="None", dimensions=dims)
        cv_metrics.emit("CVJobDurationSeconds", time.time() - _fusion_started_at,
                        unit="Seconds", dimensions=dims)
        cv_metrics.emit("CVJobSuccess", 1, dimensions=dims)
    except Exception as _e:
        log.warning("metric emission skipped: %s", _e)

    if IS_LOCAL:
        log.info("local mode: results left at %s", run_dir)
        # Print the emission point so the operator can inspect.
        print(str(detection_json))
        return 0

    # ---------- upload ----------
    _s3_upload(detection_json, results_bucket,
               f"{result_prefix}/detection_results.json")
    session_json = run_dir / "session_summary.json"
    if session_json.exists():
        _s3_upload(session_json, results_bucket,
                   f"{result_prefix}/session_summary.json")
    log.info("done; uploaded to s3://%s/%s/", results_bucket, result_prefix)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log.exception("entrypoint failed: %s", e)
        # Best-effort failure metric
        try:
            sys.path.insert(0, str(FUSION_APP_DIR / "deploy"))
            import cv_metrics as _cm
            _cm.emit("CVJobFailure", 1,
                     dimensions={"Stage": "fusion",
                                 "Side": os.environ.get("SIDE", "unknown")})
        except Exception:
            pass
        sys.exit(1)
