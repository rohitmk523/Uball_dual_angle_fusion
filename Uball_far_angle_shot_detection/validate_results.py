#!/usr/bin/env python3
"""
Standalone Validation Script

Validates existing detection results against ground truth without re-processing video.
"""

import argparse
import logging
from pathlib import Path
import sys

from accuracy_validator import AccuracyValidator


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_session(
    session_json_path: str,
    game_id: str,
    angle: str,
    video_path: str = None,
    processed_video_path: str = None,
    start_time: float = None,
    end_time: float = None
) -> dict:
    """Validate existing session results

    Args:
        session_json_path: Path to session JSON file
        game_id: Game UUID from Supabase
        angle: Camera angle (LEFT or RIGHT)
        video_path: Optional original video path
        processed_video_path: Optional processed video path
        start_time: Optional start time filter
        end_time: Optional end time filter

    Returns:
        Validation results dictionary
    """
    logger = logging.getLogger(__name__)

    # Validate session JSON exists
    session_json_path = Path(session_json_path)
    if not session_json_path.exists():
        logger.error(f"Session JSON not found: {session_json_path}")
        return {'error': 'Session JSON not found'}

    logger.info(f"Validating session: {session_json_path}")
    logger.info(f"Game ID: {game_id}")
    logger.info(f"Angle: {angle}")

    try:
        # Initialize validator
        validator = AccuracyValidator()

        # Run validation
        results = validator.validate_detection(
            game_id=game_id,
            detection_json_path=str(session_json_path),
            video_path=video_path,
            processed_video_path=processed_video_path,
            start_seconds=start_time,
            end_seconds=end_time,
            angle=angle
        )

        if results.get('success'):
            logger.info("\n" + "="*50)
            logger.info("✅ VALIDATION COMPLETED SUCCESSFULLY")
            logger.info("="*50)
            logger.info(f"\n📁 Results Folder: {results['session_dir']}")

            # Print quick stats
            quick_stats = results.get('quick_stats', {})
            logger.info("\n📊 Accuracy Summary:")
            logger.info("-" * 50)
            for key, value in quick_stats.items():
                logger.info(f"  {key}: {value}")

            logger.info("\n📄 Files Generated:")
            logger.info("-" * 50)
            for file_name, file_path in results['files'].items():
                logger.info(f"  {file_name}: {file_path}")

            return results
        else:
            logger.error(f"❌ Validation failed: {results.get('error', 'Unknown error')}")
            return results

    except Exception as e:
        logger.error(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description='Validate Existing Basketball Shot Detection Results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Validate existing session JSON
  python validate_results.py \\
      --session_json Game-1/game1_farright_session.json \\
      --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \\
      --angle RIGHT

  # Include video paths in results
  python validate_results.py \\
      --session_json Game-1/game1_farright_session.json \\
      --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \\
      --angle RIGHT \\
      --video_path Game-1/game1_farright.mp4 \\
      --processed_video Game-1/game1_farright_detected.mp4

  # Validate specific time range
  python validate_results.py \\
      --session_json Game-1/game1_farright_session.json \\
      --game_id c56b96a1-6e85-469e-8ebe-6a86b929bad9 \\
      --angle RIGHT \\
      --start_time 0 \\
      --end_time 600
        """
    )

    # Required arguments
    parser.add_argument(
        '--session_json',
        type=str,
        required=True,
        help='Path to session JSON file (e.g., game1_farright_session.json)'
    )

    parser.add_argument(
        '--game_id',
        type=str,
        required=True,
        help='Game UUID from Supabase'
    )

    parser.add_argument(
        '--angle',
        type=str,
        required=True,
        choices=['LEFT', 'RIGHT'],
        help='Camera angle (LEFT or RIGHT)'
    )

    # Optional arguments
    parser.add_argument(
        '--video_path',
        type=str,
        help='Path to original video file (optional, for metadata)'
    )

    parser.add_argument(
        '--processed_video',
        type=str,
        help='Path to processed/annotated video file (optional, will be copied to results)'
    )

    parser.add_argument(
        '--start_time',
        type=float,
        help='Start time in seconds (for time range validation)'
    )

    parser.add_argument(
        '--end_time',
        type=float,
        help='End time in seconds (for time range validation)'
    )

    args = parser.parse_args()

    logger.info("="*50)
    logger.info("Basketball Shot Detection - Standalone Validation")
    logger.info("="*50)

    # Run validation
    results = validate_session(
        session_json_path=args.session_json,
        game_id=args.game_id,
        angle=args.angle,
        video_path=args.video_path,
        processed_video_path=args.processed_video,
        start_time=args.start_time,
        end_time=args.end_time
    )

    if results.get('success'):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
