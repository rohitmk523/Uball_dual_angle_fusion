#!/usr/bin/env python3
"""
Debug script to check YOLO model detections
"""

import cv2
from ultralytics import YOLO
import sys

def debug_model(video_path, model_path, start_time=20, end_time=30):
    """Debug what the model detects in a video segment"""

    # Load model
    print(f"Loading model: {model_path}")
    model = YOLO(model_path)

    # Print model info
    print(f"\nModel class names: {model.names}")
    print(f"Number of classes: {len(model.names)}")

    # Open video
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    print(f"\nProcessing frames {start_frame} to {end_frame} ({start_time}s to {end_time}s)")
    print(f"FPS: {fps}")

    frame_count = 0
    detection_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_frame > end_frame:
            break

        # Run detection
        results = model(frame, verbose=False)[0]

        if len(results.boxes) > 0:
            detection_count += 1
            print(f"\n--- Frame {current_frame} (time: {current_frame/fps:.2f}s) ---")

            for box in results.boxes:
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = results.names[class_id]
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                print(f"  {class_name}: confidence={confidence:.3f}, bbox=({x1},{y1},{x2},{y2})")

        frame_count += 1

        # Sample every 10 frames for speed
        if frame_count % 10 == 0:
            print(f"Processed {frame_count} frames...", end='\r')

    cap.release()

    print(f"\n\nSummary:")
    print(f"Total frames processed: {frame_count}")
    print(f"Frames with detections: {detection_count}")
    print(f"Detection rate: {detection_count/frame_count*100:.1f}%")

if __name__ == "__main__":
    video_path = "Game-1/game1_farright.mp4"
    model_path = "runs/detect/basketball_yolo11n/weights/best.pt"

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    if len(sys.argv) > 2:
        model_path = sys.argv[2]

    debug_model(video_path, model_path, start_time=20, end_time=30)
