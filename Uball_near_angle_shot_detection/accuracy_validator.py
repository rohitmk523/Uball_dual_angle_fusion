#!/usr/bin/env python3
"""
Basketball Shot Detection Accuracy Validator

This module validates shot detection results against ground truth data from Supabase.
It compares detection JSON files with actual game events to calculate accuracy metrics.
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from dateutil import parser as date_parser

# Database imports
try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Supabase client not installed. Install with: pip install supabase")
    exit(1)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AccuracyValidator:
    """Validates shot detection accuracy against ground truth data"""
    
    def __init__(self):
        """Initialize the accuracy validator with Supabase connection"""
        self.supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        self.supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in environment variables")
            
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Define made and miss event types
        self.made_events = {'FG_MAKE', '3PT_MAKE', '4PT_MAKE', 'FREE_THROW_MAKE'}
        self.miss_events = {'FG_MISS', '3PT_MISS', '4PT_MISS', 'FREE_THROW_MISS'}
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
    def create_results_folder(self, base_path: str = "results", video_path: str = None) -> str:
        """Create a new results folder with name based on video path + UUID
        
        Example: input/09-22/game2_nearright.mp4 -> 09-22(2-NR)_a1b2c3d4-e5f6-7890-abcd-ef1234567890
        """
        import re
        results_dir = Path(base_path)
        results_dir.mkdir(exist_ok=True)
        
        # Generate folder name from video path
        if video_path:
            video_path_obj = Path(video_path)
            filename = video_path_obj.stem  # game2_nearright
            parent_name = video_path_obj.parent.name  # 09-22
            
            # Extract date prefix (e.g., "09-22")
            date_prefix = parent_name if re.match(r'\d{2}-\d{2}', parent_name) else None
            
            # Extract game number (e.g., "2" from "game2")
            game_match = re.search(r'game(\d+)', filename, re.IGNORECASE)
            game_num = game_match.group(1) if game_match else None
            
            # Extract and convert angle to code
            angle_mapping = {
                'nearleft': 'NL', 'nearright': 'NR',
                'farleft': 'FL', 'farright': 'FR',
                'left': 'L', 'right': 'R'
            }
            angle_code = None
            for angle_name, code in angle_mapping.items():
                if angle_name in filename.lower():
                    angle_code = code
                    break
            
            # Build folder name: 09-22(2-NR)_<uuid>
            session_uuid = str(uuid.uuid4())
            if date_prefix and game_num and angle_code:
                folder_name = f"{date_prefix}({game_num}-{angle_code})_{session_uuid}"
            elif date_prefix:
                folder_name = f"{date_prefix}_{filename}_{session_uuid}"
            else:
                folder_name = f"{filename.replace('_', '-')}_{session_uuid}"
        else:
            # Fallback to UUID if no video path
            folder_name = str(uuid.uuid4())
        
        session_dir = results_dir / folder_name
        session_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Created results folder: {session_dir}")
        return str(session_dir)
    
    def fetch_ground_truth(self, game_id: str, angle: str = None) -> List[Dict]:
        """Fetch ground truth data from Supabase for a specific game"""
        try:
            # Query the plays table for the specific game
            response = self.supabase.table('plays').select('*').eq('game_id', game_id).execute()
            
            if not response.data:
                self.logger.warning(f"No plays found for game_id: {game_id}")
                return []
            
            # Filter for shot events only
            shot_events = []
            for play in response.data:
                event_type = play.get('classification')
                play_angle = play.get('angle')
                
                # Check if this is a shot event
                if event_type in self.made_events or event_type in self.miss_events:
                    # Apply angle filter if specified
                    if angle is not None and play_angle != angle:
                        continue  # Skip events that don't match the requested angle
                    
                    shot_events.append({
                        'id': play.get('id'),
                        'timestamp_seconds': play.get('timestamp_seconds'),
                        'start_timestamp': play.get('start_timestamp'),
                        'end_timestamp': play.get('end_timestamp'),
                        'created_at': play.get('created_at'),
                        'classification': event_type,
                        'game_id': play.get('game_id'),
                        'outcome': 'made' if event_type in self.made_events else 'missed',
                        'angle': play_angle,
                        'player_a': play.get('player_a'),
                        'player_b': play.get('player_b'),
                        'note': play.get('note')
                    })
            
            # Sort by timestamp for easier comparison
            shot_events.sort(key=lambda x: x.get('timestamp_seconds', 0) or 0)
            
            if angle:
                self.logger.info(f"Found {len(shot_events)} {angle} angle shot events for game {game_id}")
            else:
                self.logger.info(f"Found {len(shot_events)} shot events for game {game_id}")
            return shot_events
            
        except Exception as e:
            self.logger.error(f"Error fetching ground truth data: {e}")
            return []
    
    def parse_detection_results(self, json_file_path: str) -> Dict:
        """Parse detection results JSON file"""
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            if 'shots' not in data:
                self.logger.error("Invalid detection JSON format: missing 'shots' key")
                return {}
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error parsing detection results: {e}")
            return {}
    
    def convert_timestamp_to_seconds(self, timestamp_str: str, start_time_str: str = None) -> float:
        """Convert timestamp string to seconds since start of video"""
        try:
            # Parse the timestamp string
            dt = date_parser.parse(timestamp_str)
            
            # If we have start time, calculate relative seconds
            if start_time_str:
                start_dt = date_parser.parse(start_time_str)
                return (dt - start_dt).total_seconds()
            
            # Fallback: return absolute timestamp (not ideal for matching)
            return dt.timestamp()
        except:
            return 0.0
    
    def match_shots_by_timestamp(self, detected_shots: List[Dict], ground_truth_shots: List[Dict], session_start_time: str = None) -> Dict:
        """Match detected shots with ground truth shots based on simple range matching"""
        
        matched_correct = []
        matched_incorrect = []
        missing_from_ground_truth = []
        unmatched_ground_truth = ground_truth_shots.copy()
        
        for detected_shot in detected_shots:
            # Use timestamp_seconds if available, otherwise convert
            if 'timestamp_seconds' in detected_shot:
                detected_seconds = detected_shot['timestamp_seconds']
            else:
                # Fallback conversion if timestamp_seconds not available
                detected_timestamp_str = detected_shot.get('timestamp', '')
                detected_seconds = self.convert_timestamp_to_seconds(detected_timestamp_str, session_start_time)
                detected_shot['timestamp_seconds'] = detected_seconds
            
            matched_shot = None
            
            # Find ground truth shot where detected timestamp falls between start and end
            for gt_shot in unmatched_ground_truth:
                start_time = gt_shot.get('start_timestamp')
                end_time = gt_shot.get('end_timestamp')
                
                if start_time is None or end_time is None:
                    continue
                
                # Check if detected timestamp is within the range (with 2-second tolerance on both ends)
                tolerance = 2.0  # 2 seconds tolerance for matching precision
                if (start_time - tolerance) <= detected_seconds <= (end_time + tolerance):
                    matched_shot = gt_shot
                    break
            
            if matched_shot:
                # Check if outcomes match
                detected_outcome = detected_shot.get('outcome', '')
                gt_outcome = matched_shot.get('outcome', '')
                outcome_match = detected_outcome == gt_outcome
                
                match_info = {
                    'detected_shot': detected_shot,
                    'ground_truth_shot': matched_shot,
                    'detected_outcome': detected_outcome,
                    'ground_truth_outcome': gt_outcome,
                    'outcome_match': outcome_match,
                    'detected_timestamp_seconds': detected_seconds,
                    'start_timestamp': matched_shot.get('start_timestamp'),
                    'end_timestamp': matched_shot.get('end_timestamp')
                }
                
                if outcome_match:
                    matched_correct.append(match_info)
                else:
                    matched_incorrect.append(match_info)
                    
                unmatched_ground_truth.remove(matched_shot)
            else:
                # Shot not found in ground truth
                shot_info = {
                    'detected_shot': detected_shot,
                    'detected_outcome': detected_shot.get('outcome', ''),
                    'detected_timestamp_seconds': detected_seconds
                }
                missing_from_ground_truth.append(shot_info)
        
        return {
            'matched_correct': matched_correct,
            'matched_incorrect': matched_incorrect,
            'missing_from_ground_truth': missing_from_ground_truth,
            'unmatched_ground_truth': unmatched_ground_truth,
            'matching_method': 'simple_timestamp_range'
        }
    
    def filter_by_time_range(self, shots: List[Dict], start_seconds: float = None, end_seconds: float = None, 
                            timestamp_field: str = 'timestamp', session_start_time: str = None) -> List[Dict]:
        """Filter shots by time range"""
        if start_seconds is None and end_seconds is None:
            return shots
        
        filtered_shots = []
        for shot in shots:
            if timestamp_field == 'timestamp':
                # For detection data - use timestamp_seconds if available, otherwise convert
                if 'timestamp_seconds' in shot:
                    shot_time = shot['timestamp_seconds']
                else:
                    shot_time = self.convert_timestamp_to_seconds(shot.get(timestamp_field, ''), session_start_time)
            else:
                # For ground truth data - use timestamp_seconds directly
                shot_time = shot.get(timestamp_field, 0)
                if shot_time is None:
                    continue
            
            # Check if shot is within time range
            if start_seconds is not None and shot_time < start_seconds:
                continue
            if end_seconds is not None and shot_time > end_seconds:
                continue
                
            filtered_shots.append(shot)
        
        return filtered_shots
    
    def calculate_accuracy(self, detection_data: Dict, ground_truth: List[Dict], 
                          start_seconds: float = None, end_seconds: float = None) -> Dict:
        """Calculate accuracy metrics between detection and ground truth using timestamp matching"""
        
        if not detection_data or not ground_truth:
            return {
                'error': 'Missing detection data or ground truth',
                'detection_shots': 0,
                'ground_truth_shots': 0,
                'accuracy': 0.0
            }
        
        detected_shots = detection_data.get('shots', [])
        
        # Extract session start time for proper timestamp conversion
        session_start_time = detection_data.get('session_info', {}).get('start_time')
        
        # Filter shots by time range if specified
        if start_seconds is not None or end_seconds is not None:
            detected_shots = self.filter_by_time_range(detected_shots, start_seconds, end_seconds, 'timestamp', session_start_time)
            ground_truth = self.filter_by_time_range(ground_truth, start_seconds, end_seconds, 'timestamp_seconds')
        
        detected_made = sum(1 for shot in detected_shots if shot.get('outcome') == 'made')
        detected_missed = sum(1 for shot in detected_shots if shot.get('outcome') == 'missed')
        detected_total = detected_made + detected_missed
        
        ground_truth_made = sum(1 for event in ground_truth if event.get('outcome') == 'made')
        ground_truth_missed = sum(1 for event in ground_truth if event.get('outcome') == 'missed')
        ground_truth_total = ground_truth_made + ground_truth_missed
        
        # Perform timestamp-based matching
        matching_results = self.match_shots_by_timestamp(detected_shots, ground_truth, session_start_time)
        
        # Calculate accuracy metrics using new structure
        matched_correct = matching_results['matched_correct']
        matched_incorrect = matching_results['matched_incorrect']
        missing_from_ground_truth = matching_results['missing_from_ground_truth']
        unmatched_ground_truth = matching_results['unmatched_ground_truth']
        
        total_matches = len(matched_correct) + len(matched_incorrect)
        correct_matches = len(matched_correct)
        
        # Calculate accuracy: Of the 135 detected shots, how many did we classify correctly?
        overall_accuracy = (correct_matches / detected_total * 100) if detected_total > 0 else 0
        
        # Calculate accuracy metrics
        results = {
            'detection_summary': {
                'total_shots': detected_total,
                'made_shots': detected_made,
                'missed_shots': detected_missed,
                'shooting_percentage': (detected_made / detected_total * 100) if detected_total > 0 else 0
            },
            'ground_truth_summary': {
                'total_shots': ground_truth_total,
                'made_shots': ground_truth_made,
                'missed_shots': ground_truth_missed,
                'shooting_percentage': (ground_truth_made / ground_truth_total * 100) if ground_truth_total > 0 else 0
            },
            'accuracy_analysis': {
                'total_detected_shots': detected_total,
                'matched_correct': correct_matches,
                'matched_incorrect': len(matched_incorrect),
                'missing_from_ground_truth': len(missing_from_ground_truth),
                'overall_accuracy_percentage': overall_accuracy,
                'matched_shots_accuracy': (correct_matches / total_matches * 100) if total_matches > 0 else 0,
                'ground_truth_coverage': (total_matches / ground_truth_total * 100) if ground_truth_total > 0 else 0
            },
            'timestamp_matching': {
                'total_matches': total_matches,
                'outcome_accuracy': (correct_matches / total_matches * 100) if total_matches > 0 else 0,
                'detection_coverage': (total_matches / detected_total * 100) if detected_total > 0 else 0,
                'ground_truth_coverage': (total_matches / ground_truth_total * 100) if ground_truth_total > 0 else 0
            },
            'comparison': {
                'shot_count_accuracy': (min(detected_total, ground_truth_total) / max(detected_total, ground_truth_total) * 100) if max(detected_total, ground_truth_total) > 0 else 0,
                'made_shot_difference': detected_made - ground_truth_made,
                'missed_shot_difference': detected_missed - ground_truth_missed,
                'total_shot_difference': detected_total - ground_truth_total
            },
            'detailed_analysis': {
                'matched_correct': matched_correct,
                'matched_incorrect': matched_incorrect, 
                'missing_from_ground_truth': missing_from_ground_truth,
                'unmatched_ground_truth': unmatched_ground_truth,
                'matching_method': matching_results['matching_method']
            },
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'detection_method': detection_data.get('session_info', {}).get('detection_method', 'unknown'),
                'model_path': detection_data.get('session_info', {}).get('model_path', 'unknown'),
                'matching_method': 'start_end_timestamp_range',
                'time_range_filter': {
                    'start_seconds': start_seconds,
                    'end_seconds': end_seconds,
                    'applied': start_seconds is not None or end_seconds is not None
                }
            }
        }
        
        return results
    
    def save_results(self, session_dir: str, detection_data: Dict, ground_truth: List[Dict], 
                     accuracy_results: Dict, video_path: str = None, processed_video_path: str = None):
        """Save all results to the session directory"""
        
        session_path = Path(session_dir)
        
        # Save detection results
        detection_file = session_path / "detection_results.json"
        with open(detection_file, 'w') as f:
            json.dump(detection_data, f, indent=2)
        
        # Save ground truth data
        ground_truth_file = session_path / "ground_truth.json"
        with open(ground_truth_file, 'w') as f:
            json.dump(ground_truth, f, indent=2)
        
        # Save accuracy analysis
        accuracy_file = session_path / "accuracy_analysis.json"
        with open(accuracy_file, 'w') as f:
            json.dump(accuracy_results, f, indent=2)
        
        # Copy processed video only (not original to save space)
        if processed_video_path and Path(processed_video_path).exists():
            import shutil
            processed_video = session_path / f"processed_video{Path(processed_video_path).suffix}"
            shutil.copy2(processed_video_path, processed_video)
        
        # Create summary file
        summary = {
            'session_info': {
                'uuid': session_path.name,
                'created_at': datetime.now().isoformat(),
                'game_id': accuracy_results.get('metadata', {}).get('game_id'),
                'video_path': str(video_path) if video_path else None,
                'processed_video_path': str(processed_video_path) if processed_video_path else None
            },
            'files': {
                'detection_results': 'detection_results.json',
                'ground_truth': 'ground_truth.json',
                'accuracy_analysis': 'accuracy_analysis.json',
                'processed_video': f"processed_video{Path(processed_video_path).suffix}" if processed_video_path else None
            },
            'quick_summary': {
                'detection_shots': accuracy_results['detection_summary']['total_shots'],
                'ground_truth_shots': accuracy_results['ground_truth_summary']['total_shots'],
                'shot_count_accuracy': accuracy_results['comparison']['shot_count_accuracy']
            }
        }
        
        summary_file = session_path / "session_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Results saved to: {session_dir}")
        return {
            'session_dir': session_dir,
            'detection_file': str(detection_file),
            'ground_truth_file': str(ground_truth_file),
            'accuracy_file': str(accuracy_file),
            'summary_file': str(summary_file)
        }
    
    def validate_detection(self, game_id: str, detection_json_path: str, 
                          video_path: str = None, processed_video_path: str = None,
                          start_seconds: float = None, end_seconds: float = None, angle: str = None) -> Dict:
        """Complete validation workflow"""
        
        self.logger.info(f"Starting validation for game_id: {game_id}")
        
        # Create results folder with name based on video path
        session_dir = self.create_results_folder(video_path=video_path)
        
        # Fetch ground truth
        ground_truth = self.fetch_ground_truth(game_id, angle)
        if not ground_truth:
            angle_filter = f" with angle {angle}" if angle else ""
            error_msg = f"No ground truth data found for game_id: {game_id}{angle_filter}"
            self.logger.error(error_msg)
            return {'error': error_msg}
        
        # Parse detection results
        detection_data = self.parse_detection_results(detection_json_path)
        if not detection_data:
            error_msg = f"Failed to parse detection results from: {detection_json_path}"
            self.logger.error(error_msg)
            return {'error': error_msg}
        
        # Calculate accuracy
        accuracy_results = self.calculate_accuracy(detection_data, ground_truth, start_seconds, end_seconds)
        accuracy_results['metadata']['game_id'] = game_id
        if angle:
            accuracy_results['metadata']['angle_filter'] = angle
        
        # Save all results
        file_paths = self.save_results(
            session_dir, detection_data, ground_truth, accuracy_results,
            video_path, processed_video_path
        )
        
        # Return summary
        result = {
            'success': True,
            'session_dir': session_dir,
            'game_id': game_id,
            'files': file_paths,
            'summary': accuracy_results,
            'quick_stats': {
                'detection_shots': accuracy_results['detection_summary']['total_shots'],
                'ground_truth_shots': accuracy_results['ground_truth_summary']['total_shots'],
                'timestamp_matches': accuracy_results['timestamp_matching']['total_matches'],
                'outcome_accuracy': f"{accuracy_results['timestamp_matching']['outcome_accuracy']:.1f}%",
                'detection_coverage': f"{accuracy_results['timestamp_matching']['detection_coverage']:.1f}%",
                'ground_truth_coverage': f"{accuracy_results['timestamp_matching']['ground_truth_coverage']:.1f}%",
                'detection_shooting_pct': f"{accuracy_results['detection_summary']['shooting_percentage']:.1f}%",
                'actual_shooting_pct': f"{accuracy_results['ground_truth_summary']['shooting_percentage']:.1f}%"
            }
        }
        
        self.logger.info(f"Validation completed successfully for game {game_id}")
        self.logger.info(f"Timestamp matches: {result['quick_stats']['timestamp_matches']}")
        self.logger.info(f"Outcome accuracy: {result['quick_stats']['outcome_accuracy']}")
        
        return result

def main():
    """Example usage of the AccuracyValidator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate basketball shot detection accuracy')
    parser.add_argument('--game_id', required=True, help='Game ID from Supabase')
    parser.add_argument('--detection_json', required=True, help='Path to detection results JSON')
    parser.add_argument('--video_path', help='Path to original video file')
    parser.add_argument('--processed_video', help='Path to processed video file')
    parser.add_argument('--start_time', help='Start time for validation (HH:MM:SS or MM:SS or SS)')
    parser.add_argument('--end_time', help='End time for validation (HH:MM:SS or MM:SS or SS)')
    
    args = parser.parse_args()
    
    # Convert time parameters to seconds
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
    
    start_seconds = time_to_seconds(args.start_time) if args.start_time else None
    end_seconds = time_to_seconds(args.end_time) if args.end_time else None
    
    validator = AccuracyValidator()
    result = validator.validate_detection(
        game_id=args.game_id,
        detection_json_path=args.detection_json,
        video_path=args.video_path,
        processed_video_path=args.processed_video,
        start_seconds=start_seconds,
        end_seconds=end_seconds
    )
    
    if result.get('success'):
        print("✅ Validation completed successfully!")
        print(f"📁 Results saved to: {result['session_dir']}")
        print(f"📊 Quick Stats:")
        for key, value in result['quick_stats'].items():
            print(f"   {key}: {value}")
    else:
        print(f"❌ Validation failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()