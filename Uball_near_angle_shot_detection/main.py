#!/usr/bin/env python3
"""
Basketball Shot Detection System - Main Application

This is the main entry point for the basketball shot detection system.
Supports live camera feed, video processing, and batch processing modes.

Usage:
    python main.py --action live                                    # Live camera detection
    python main.py --action video --video_path game.mp4             # Process single video
    python main.py --action batch --video_dir videos/               # Process multiple videos
"""

import argparse
import cv2
import time
from pathlib import Path
import json
from shot_detection import ShotAnalyzer
from accuracy_validator import AccuracyValidator

def live_detection(model_path='runs/detect/basketball_yolo11n3/weights/best.pt', camera_index=0, save_session=True):
    """Run live basketball detection from camera feed"""
    
    print("="*60)
    print("LIVE BASKETBALL SHOT DETECTION")
    print("="*60)
    print(f"Model: {model_path}")
    print(f"Camera: {camera_index}")
    print("Controls: 'q' to quit, 's' to save session")
    print("="*60)
    
    # Initialize shot analyzer
    analyzer = ShotAnalyzer(model_path)
    
    # Initialize camera
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"❌ Failed to open camera {camera_index}")
        return False
        
    # Set camera properties for better performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Set up frame-based timing for live detection
    camera_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    analyzer.set_video_timing(camera_fps, 0)
    
    print("🏀 Starting live detection... Press 'q' to quit")
    
    frame_count = 0
    fps_start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read frame from camera")
                break
                
            frame_count += 1
            
            # Update frame number for timestamp calculation
            analyzer.update_frame_number(frame_count)
            
            # Run detection
            detections = analyzer.detect_objects(frame)
            
            # Update shot tracking
            analyzer.update_shot_tracking(detections)
            
            # Draw overlay
            annotated_frame = analyzer.draw_overlay(frame, detections)
            
            # Calculate and display FPS
            if frame_count % 30 == 0:
                fps_end_time = time.time()
                fps = 30 / (fps_end_time - fps_start_time)
                fps_start_time = fps_end_time
                
            # Add FPS to display
            cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (10, annotated_frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Display frame
            cv2.imshow('Basketball Shot Detection', annotated_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save current session
                filename = analyzer.save_session_data()
                print(f"Session saved: {filename}")
                
    except KeyboardInterrupt:
        print("\n⚠️ Detection interrupted by user")
        
    finally:
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        
        # Save session data
        if save_session:
            filename = analyzer.save_session_data()
            print(f"\n✓ Final session data saved: {filename}")
            
        # Print session summary
        print(f"\n📊 SESSION SUMMARY")
        print(f"Total Shots: {analyzer.stats['total_shots']}")
        print(f"Made: {analyzer.stats['made_shots']}")
        print(f"Missed: {analyzer.stats['missed_shots']}")
        print(f"Undetermined: {analyzer.stats['undetermined_shots']}")
        
        if analyzer.stats['made_shots'] + analyzer.stats['missed_shots'] > 0:
            shooting_pct = analyzer.stats['made_shots'] / (analyzer.stats['made_shots'] + analyzer.stats['missed_shots']) * 100
            print(f"Shooting %: {shooting_pct:.1f}%")
            
    return True

def process_video(video_path, model_path='runs/detect/basketball_yolo11n3/weights/best.pt', output_path=None, save_session=True, start_time=None, end_time=None, game_id=None, validate_accuracy=False, angle=None):
    """Process single video file for basketball detection"""
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return False
        
    if output_path is None:
        output_path = video_path.parent / f"{video_path.stem}_detected.mp4"
        
    print("="*60)
    print("VIDEO BASKETBALL SHOT DETECTION")
    print("="*60)
    print(f"Input: {video_path}")
    print(f"Output: {output_path}")
    print(f"Model: {model_path}")
    print("="*60)
    
    # Initialize shot analyzer
    analyzer = ShotAnalyzer(model_path)
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Failed to open video: {video_path}")
        return False
        
    # Get video properties (keep FPS as float for accuracy, cap to 2 decimal places)
    fps = round(cap.get(cv2.CAP_PROP_FPS), 2)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video: {width}x{height} @ {fps}fps, {total_frames} frames")
    
    # Parse time parameters
    def time_to_seconds(time_str):
        """Convert HH:MM:SS to seconds"""
        if not time_str:
            return None
        parts = time_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(parts[0])
    
    start_seconds = time_to_seconds(start_time) if start_time else 0
    end_seconds = time_to_seconds(end_time) if end_time else None
    
    start_frame = int(start_seconds * fps)
    end_frame = int(end_seconds * fps) if end_seconds else total_frames
    
    # Set video timing for frame-based timestamps
    analyzer.set_video_timing(fps, start_frame)
    
    # Validate frame range
    start_frame = max(0, min(start_frame, total_frames - 1))
    end_frame = max(start_frame + 1, min(end_frame, total_frames))
    
    if start_time or end_time:
        print(f"Processing: {start_time or '00:00:00'} to {end_time or 'end'} (frames {start_frame}-{end_frame})")
    
    # Seek to start frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    # Setup video writer (use same FPS as input for consistency)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    frame_count = start_frame
    processing_start_time = time.time()
    frames_processed = 0
    
    try:
        while frame_count < end_frame:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            frames_processed += 1
            
            # Update frame number for timestamp calculation
            analyzer.update_frame_number(frame_count)
            
            # Run detection
            detections = analyzer.detect_objects(frame)
            
            # Update shot tracking
            analyzer.update_shot_tracking(detections)
            
            # Draw overlay
            annotated_frame = analyzer.draw_overlay(frame, detections)
            
            # Write frame
            out.write(annotated_frame)
            
            # Progress update
            if frames_processed % 100 == 0:
                progress = (frames_processed / (end_frame - start_frame)) * 100
                elapsed = time.time() - processing_start_time
                eta = (elapsed / frames_processed) * ((end_frame - start_frame) - frames_processed) if frames_processed > 0 else 0
                print(f"Progress: {progress:.1f}% ({frames_processed}/{end_frame - start_frame}) ETA: {eta:.1f}s")
                
    except KeyboardInterrupt:
        print("\n⚠️ Processing interrupted by user")
        
    finally:
        # Cleanup
        cap.release()
        out.release()
        
        # Save session data
        session_filename = None
        if save_session:
            session_filename = video_path.stem + "_session.json"
            analyzer.save_session_data(session_filename)
            print(f"✓ Session data saved: {session_filename}")
            
        # Validate accuracy if requested
        if validate_accuracy and game_id and session_filename:
            print(f"\n🔍 VALIDATING ACCURACY")
            print(f"Game ID: {game_id}")
            
            # Convert time parameters to seconds for validation
            def time_to_seconds(time_str):
                if not time_str:
                    return None
                parts = time_str.split(':')
                if len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                elif len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                else:
                    return int(parts[0])
            
            validation_start_seconds = time_to_seconds(start_time) if start_time else None
            validation_end_seconds = time_to_seconds(end_time) if end_time else None
            
            if validation_start_seconds is not None or validation_end_seconds is not None:
                print(f"Time range: {start_time or '00:00:00'} to {end_time or 'end'}")
            
            try:
                validator = AccuracyValidator()
                validation_result = validator.validate_detection(
                    game_id=game_id,
                    detection_json_path=session_filename,
                    video_path=str(video_path),
                    processed_video_path=str(output_path),
                    start_seconds=validation_start_seconds,
                    end_seconds=validation_end_seconds,
                    angle=angle
                )
                
                if validation_result.get('success'):
                    print(f"✅ Accuracy validation completed!")
                    print(f"📁 Results saved to: {validation_result['session_dir']}")
                    print(f"📊 Accuracy Summary:")
                    for key, value in validation_result['quick_stats'].items():
                        print(f"   {key}: {value}")
                else:
                    print(f"❌ Accuracy validation failed: {validation_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"⚠️ Accuracy validation error: {e}")
            
        # Print processing summary
        elapsed_time = time.time() - processing_start_time
        print(f"\n📊 PROCESSING SUMMARY")
        print(f"Processed: {frames_processed} frames in {elapsed_time:.1f}s")
        print(f"Speed: {frames_processed/elapsed_time:.1f} fps" if elapsed_time > 0 else "Speed: N/A")
        print(f"Total Shots: {analyzer.stats['total_shots']}")
        print(f"Made: {analyzer.stats['made_shots']}")
        print(f"Missed: {analyzer.stats['missed_shots']}")
        print(f"Output saved: {output_path}")
        
    return True

def batch_process(video_dir, model_path='runs/detect/basketball_yolo11n3/weights/best.pt', output_dir=None):
    """Process multiple videos in batch"""
    
    video_dir = Path(video_dir)
    if not video_dir.exists():
        print(f"❌ Video directory not found: {video_dir}")
        return False
        
    if output_dir is None:
        output_dir = video_dir / "processed"
    else:
        output_dir = Path(output_dir)
        
    output_dir.mkdir(exist_ok=True)
    
    # Find video files
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']
    video_files = []
    for ext in video_extensions:
        video_files.extend(video_dir.glob(f'*{ext}'))
        video_files.extend(video_dir.glob(f'*{ext.upper()}'))
        
    if not video_files:
        print(f"❌ No video files found in: {video_dir}")
        return False
        
    print("="*60)
    print("BATCH VIDEO PROCESSING")
    print("="*60)
    print(f"Input directory: {video_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Model: {model_path}")
    print(f"Videos found: {len(video_files)}")
    print("="*60)
    
    # Process each video
    batch_results = []
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n📹 Processing video {i}/{len(video_files)}: {video_file.name}")
        
        output_path = output_dir / f"{video_file.stem}_detected.mp4"
        
        success = process_video(
            video_path=video_file,
            model_path=model_path,
            output_path=output_path,
            save_session=True
        )
        
        batch_results.append({
            'video': str(video_file),
            'output': str(output_path) if success else None,
            'success': success
        })
        
    # Save batch summary
    batch_summary = {
        'batch_info': {
            'input_directory': str(video_dir),
            'output_directory': str(output_dir),
            'model_path': model_path,
            'total_videos': len(video_files),
            'successful': sum(1 for r in batch_results if r['success']),
            'failed': sum(1 for r in batch_results if not r['success'])
        },
        'results': batch_results
    }
    
    summary_file = output_dir / "batch_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(batch_summary, f, indent=2)
        
    print(f"\n📊 BATCH SUMMARY")
    print(f"Processed: {batch_summary['batch_info']['successful']}/{batch_summary['batch_info']['total_videos']} videos")
    print(f"Summary saved: {summary_file}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Basketball Shot Detection System')
    parser.add_argument('--action', type=str, required=True,
                       choices=['live', 'video', 'batch'],
                       help='Action to perform')
    parser.add_argument('--model', type=str, default='runs/detect/basketball_yolo11n3/weights/best.pt',
                       help='Path to YOLO model')
    parser.add_argument('--camera', type=int, default=0,
                       help='Camera index for live detection')
    parser.add_argument('--video_path', type=str,
                       help='Path to video file for single video processing')
    parser.add_argument('--video_dir', type=str,
                       help='Directory containing videos for batch processing')
    parser.add_argument('--output_dir', type=str,
                       help='Output directory for processed videos')
    parser.add_argument('--no_save', action='store_true',
                       help='Do not save session data')
    parser.add_argument('--start_time', type=str,
                       help='Start time for video processing (HH:MM:SS or MM:SS or SS)')
    parser.add_argument('--end_time', type=str,
                       help='End time for video processing (HH:MM:SS or MM:SS or SS)')
    parser.add_argument('--game_id', type=str,
                       help='Game ID for accuracy validation against Supabase data')
    parser.add_argument('--validate_accuracy', action='store_true',
                       help='Validate accuracy against ground truth data from Supabase')
    parser.add_argument('--angle', type=str, choices=['LEFT', 'RIGHT'],
                       help='Filter ground truth by shooting angle (LEFT or RIGHT)')
    
    args = parser.parse_args()
    
    if args.action == 'live':
        success = live_detection(
            model_path=args.model,
            camera_index=args.camera,
            save_session=not args.no_save
        )
        
    elif args.action == 'video':
        if not args.video_path:
            print("❌ --video_path required for video processing")
            return
        success = process_video(
            video_path=args.video_path,
            model_path=args.model,
            save_session=not args.no_save,
            start_time=args.start_time,
            end_time=args.end_time,
            game_id=args.game_id,
            validate_accuracy=args.validate_accuracy,
            angle=args.angle
        )
        
    elif args.action == 'batch':
        if not args.video_dir:
            print("❌ --video_dir required for batch processing")
            return
        success = batch_process(
            video_dir=args.video_dir,
            model_path=args.model,
            output_dir=args.output_dir
        )
        
    if success:
        print("\n🏀 Basketball detection completed successfully!")
    else:
        print("\n❌ Basketball detection failed")

if __name__ == "__main__":
    main()