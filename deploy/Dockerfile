# syntax=docker/dockerfile:1.6
#
# uball-cv-fusion — GPU container for dual-angle basketball shot detection.
# Runs as an AWS Batch GPU job: pulls the two 1080p angle videos from S3,
# fetches versioned YOLOv11 weights from S3, invokes dual_angle_fusion.py
# with --skip_video, then uploads detection_results.json back to S3.
#
# Built against CUDA 12.2 / cuDNN 8 to match the g4dn.xlarge driver fleet
# that the transcode pipeline already runs on.

FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: Python 3.10, ffmpeg (for OpenCV video I/O), libs needed by
# cv2 in headless mode. curl+ca-certs for any runtime S3 SDK bootstrapping.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3.10 \
      python3-pip \
      python3-venv \
      ffmpeg \
      libgl1 \
      libsm6 \
      libxext6 \
      libxrender1 \
      curl \
      ca-certificates \
 && ln -sf /usr/bin/python3.10 /usr/local/bin/python3 \
 && ln -sf /usr/bin/python3.10 /usr/local/bin/python \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer) so source changes don't invalidate
# the pip install layer.
COPY deploy/requirements.lock /app/deploy/requirements.lock
RUN pip3 install --upgrade pip setuptools wheel \
 && pip3 install -r /app/deploy/requirements.lock

# Copy the fusion orchestrator + its two sub-detectors. Model weights are
# NOT baked in — they're fetched from S3 at runtime via MANIFEST.json.
COPY dual_angle_fusion.py /app/
COPY Uball_near_angle_shot_detection /app/Uball_near_angle_shot_detection
COPY Uball_far_angle_shot_detection /app/Uball_far_angle_shot_detection
COPY deploy/entrypoint.py /app/deploy/entrypoint.py
COPY deploy/cv_metrics.py /app/deploy/cv_metrics.py

# Strip any committed model weights so we're sure runtime uses the S3 version.
RUN find /app/Uball_near_angle_shot_detection/runs -name '*.pt' -delete 2>/dev/null || true \
 && find /app/Uball_far_angle_shot_detection/runs -name '*.pt' -delete 2>/dev/null || true

# Runtime workspace (weights cache + inputs + results) lives under /tmp
# so the image stays read-only friendly.
RUN mkdir -p /tmp/models /tmp/inputs /app/results

ENTRYPOINT ["python3", "/app/deploy/entrypoint.py"]
