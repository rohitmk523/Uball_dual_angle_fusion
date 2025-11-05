#!/usr/bin/env python3
"""
Far Angle Basketball Shot Detection - Main Entry Point

This script processes basketball game videos from far angle cameras to detect
and classify shots using zone-based tracking and vertical passage detection.
"""

import argparse
import cv2
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import sys

from shot_detection import ShotAnalyzer
from accuracy_validator import AccuracyValidator


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def process_video(
    video_path: str,
    model_path: str,
    output_path: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    game_id: Optional[str] = None,
    validate_accuracy: bool = False,
    angle: Optional[str] = None
) -> dict:
    """Process video with far angle shot detection

    Args:
        video_path: Path to input video file
        model_path: Path to trained YOLO model
        output_path: Optional custom output path
        start_time: Optional start time in seconds
        end_time: Optional end time in seconds
        game_id: Optional game UUID for accuracy validation
        validate_accuracy: Whether to validate against ground truth
        angle: Camera angle (LEFT or RIGHT) for validation

    Returns:
        Dictionary with processing results
    """
    logger = logging.getLogger(__name__)

    # Validate inputs
    video_path = Path(video_path)
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return {'error': 'Video file not found'}

    model_path = Path(model_path)
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return {'error': 'Model file not found'}

    logger.info(f"Processing video: {video_path}")
    logger.info(f"Using model: {model_path}")

    # Initialize shot analyzer
    analyzer = ShotAnalyzer(str(model_path))

    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error("Failed to open video file")
        return {'error': 'Failed to open video file'}

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    analyzer.fps = fps

    logger.info(f"Video properties: {width}x{height} @ {fps:.2f} FPS, {total_frames} frames")

    # Calculate frame range
    start_frame = int(start_time * fps) if start_time is not None else 0
    end_frame = int(end_time * fps) if end_time is not None else total_frames

    if start_time is not None:
        logger.info(f"Processing from {start_time}s (frame {start_frame})")
    if end_time is not None:
        logger.info(f"Processing until {end_time}s (frame {end_frame})")

    # Setup output paths
    if output_path is None:
        output_dir = video_path.parent
        output_stem = video_path.stem
        if start_time is not None or end_time is not None:
            time_suffix = f"_{int(start_time or 0)}s-{int(end_time or total_frames/fps)}s"
            output_stem = f"{output_stem}{time_suffix}"
    else:
        output_dir = Path(output_path).parent
        output_stem = Path(output_path).stem

    output_video_path = output_dir / f"{output_stem}_detected.mp4"
    session_json_path = output_dir / f"{output_stem}_session.json"

    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

    if not out.isOpened():
        logger.error("Failed to create output video writer")
        cap.release()
        return {'error': 'Failed to create output video writer'}

    logger.info(f"Output video: {output_video_path}")
    logger.info(f"Output JSON: {session_json_path}")

    # Seek to start frame
    if start_frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    # Process frames
    frame_count = 0
    processed_frames = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_frame > end_frame:
                break

            analyzer.frame_count = current_frame

            # Detect objects
            detections = analyzer.detect_objects(frame)

            # Update shot tracking
            analyzer.update_shot_tracking(detections)

            # Draw overlay
            annotated_frame = analyzer.draw_overlay(frame, detections)

            # Write output frame
            out.write(annotated_frame)

            processed_frames += 1

            # Progress indicator
            if processed_frames % 100 == 0:
                progress = (current_frame - start_frame) / (end_frame - start_frame) * 100
                logger.info(f"Progress: {progress:.1f}% ({processed_frames} frames processed)")

    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return {'error': str(e)}
    finally:
        # Cleanup
        cap.release()
        out.release()

    logger.info(f"Processing complete! Processed {processed_frames} frames")

    # Save session data
    video_info = {
        'video_path': str(video_path),
        'model_path': str(model_path),
        'start_time': datetime.now().isoformat()
    }
    analyzer.save_session_data(str(session_json_path), video_info)

    # Prepare results
    results = {
        'success': True,
        'processed_frames': processed_frames,
        'output_video': str(output_video_path),
        'session_json': str(session_json_path),
        'stats': analyzer.stats.copy()
    }

    # Validate accuracy if requested
    if validate_accuracy:
        if not game_id:
            logger.error("--game_id required for accuracy validation")
            results['validation_error'] = 'Missing game_id'
        elif not angle:
            logger.error("--angle required for accuracy validation (LEFT or RIGHT)")
            results['validation_error'] = 'Missing angle'
        else:
            logger.info(f"Starting accuracy validation for game {game_id}, angle {angle}")
            try:
                validator = AccuracyValidator()
                validation_results = validator.validate_detection(
                    game_id=game_id,
                    detection_json_path=str(session_json_path),
                    video_path=str(video_path),
                    processed_video_path=str(output_video_path),
                    start_seconds=start_time,
                    end_seconds=end_time,
                    angle=angle
                )

                if validation_results.get('success'):
                    logger.info("Accuracy validation completed successfully!")
                    logger.info(f"Results folder: {validation_results['session_dir']}")

                    # Print quick stats
                    quick_stats = validation_results.get('quick_stats', {})
                    logger.info("Accuracy Summary:")
                    for key, value in quick_stats.items():
                        logger.info(f"  {key}: {value}")

                    results['validation'] = validation_results
                else:
                    logger.error(f"Validation failed: {validation_results.get('error', 'Unknown error')}")
                    results['validation_error'] = validation_results.get('error')

            except Exception as e:
                logger.error(f"Error during validation: {e}")
                results['validation_error'] = str(e)

    return results


def process_batch(batch_config: dict) -> list:
    """Process multiple videos in batch

    Args:
        batch_config: Configuration for batch processing

    Returns:
        List of results for each video
    """
    # TODO: Implement batch processing
    pass


def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description='Far Angle Basketball Shot Detection System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Process full video
  python main.py --action video \\
      --video_path Game-1/game1_farleft.mp4 \\
      --model runs/detect/basketball_yolo11n/weights/best.pt

  # Process with time range (testing)
  python main.py --action video \\
      --video_path Game-1/game1_farleft.mp4 \\
      --model runs/detect/basketball_yolo11n/weights/best.pt \\
      --start_time 0 \\
      --end_time 120

  # Validate accuracy against ground truth
  python main.py --action video \\
      --video_path Game-1/game1_farleft.mp4 \\
      --model runs/detect/basketball_yolo11n/weights/best.pt \\
      --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \\
      --validate_accuracy \\
      --angle LEFT
        """
    )

    # Required arguments
    parser.add_argument(
        '--action',
        type=str,
        required=True,
        choices=['video', 'batch'],
        help='Action to perform (video: process single video, batch: process multiple videos)'
    )

    parser.add_argument(
        '--video_path',
        type=str,
        help='Path to input video file (required for video action)'
    )

    # Optional arguments
    parser.add_argument(
        '--model',
        type=str,
        default='runs/detect/basketball_yolo11n/weights/best.pt',
        help='Path to trained YOLO model (default: runs/detect/basketball_yolo11n/weights/best.pt)'
    )

    parser.add_argument(
        '--output_path',
        type=str,
        help='Custom output path (optional)'
    )

    parser.add_argument(
        '--start_time',
        type=float,
        help='Start time in seconds (for testing specific segments)'
    )

    parser.add_argument(
        '--end_time',
        type=float,
        help='End time in seconds (for testing specific segments)'
    )

    parser.add_argument(
        '--game_id',
        type=str,
        help='Game UUID from Supabase (required for accuracy validation)'
    )

    parser.add_argument(
        '--validate_accuracy',
        action='store_true',
        help='Enable accuracy validation against ground truth'
    )

    parser.add_argument(
        '--angle',
        type=str,
        choices=['LEFT', 'RIGHT'],
        help='Camera angle (LEFT or RIGHT) - required for accuracy validation'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.action == 'video':
        if not args.video_path:
            logger.error("--video_path is required for video action")
            parser.print_help()
            sys.exit(1)

    # Process based on action
    if args.action == 'video':
        logger.info("=== Far Angle Shot Detection ===")
        logger.info(f"Video: {args.video_path}")
        logger.info(f"Model: {args.model}")

        results = process_video(
            video_path=args.video_path,
            model_path=args.model,
            output_path=args.output_path,
            start_time=args.start_time,
            end_time=args.end_time,
            game_id=args.game_id,
            validate_accuracy=args.validate_accuracy,
            angle=args.angle
        )

        if results.get('success'):
            logger.info("\n=== Processing Complete ===")
            logger.info(f"Output Video: {results['output_video']}")
            logger.info(f"Session JSON: {results['session_json']}")
            logger.info(f"\nShot Statistics:")
            logger.info(f"  Total Shots: {results['stats']['total_shots']}")
            logger.info(f"  Made: {results['stats']['made_shots']}")
            logger.info(f"  Missed: {results['stats']['missed_shots']}")

            if 'validation' in results:
                logger.info(f"\nValidation Results:")
                logger.info(f"  Results Folder: {results['validation']['session_dir']}")

            sys.exit(0)
        else:
            logger.error(f"Processing failed: {results.get('error', 'Unknown error')}")
            sys.exit(1)

    elif args.action == 'batch':
        logger.error("Batch processing not yet implemented")
        sys.exit(1)


if __name__ == "__main__":
    main()
