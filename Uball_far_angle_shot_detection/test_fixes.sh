#!/bin/bash
# Test script for all 3 phases of fixes
# Expected accuracy: 90%+ (fix 20/26 errors)

echo "=========================================="
echo "PHASE 1 TESTS: General Made Shot (4 cases)"
echo "Expected: All should now detect as MISSED"
echo "=========================================="

echo -e "\n1. Testing 509s (was: made_shot, should be: MISSED)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 506 --end_time 512 2>&1 | grep 'Shot detected'

echo -e "\n2. Testing 938s (was: made_shot, should be: MISSED)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 935 --end_time 941 2>&1 | grep 'Shot detected'

echo -e "\n3. Testing 1237s (was: made_shot, should be: MISSED)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 1234 --end_time 1240 2>&1 | grep 'Shot detected'

echo -e "\n4. Testing 2279s (was: made_shot, should be: MISSED)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 2276 --end_time 2282 2>&1 | grep 'Shot detected'

echo -e "\n=========================================="
echo "PHASE 2 TESTS: No Vertical Crossing (2 cases)"
echo "Expected: All should now detect as MADE"
echo "=========================================="

echo -e "\n5. Testing 201s (was: no_vertical_crossing, should be: MADE 3-pointer)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 198 --end_time 204 2>&1 | grep 'Shot detected'

echo -e "\n6. Testing 242s (was: no_vertical_crossing, should be: MADE 3-pointer)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 239 --end_time 245 2>&1 | grep 'Shot detected'

echo -e "\n=========================================="
echo "PHASE 3 TESTS: Rim Roll Detection (5 cases)"
echo "Expected: All should now detect as MADE (rim_roll)"
echo "=========================================="

echo -e "\n7. Testing 954s (was: rim_bounce, should be: MADE rim_roll)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 951 --end_time 957 2>&1 | grep 'Shot detected'

echo -e "\n8. Testing 1212s (was: rim_bounce, should be: MADE rim_roll)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 1208 --end_time 1214 2>&1 | grep 'Shot detected'

echo -e "\n9. Testing 1642s (was: rim_bounce, should be: MADE rim_roll)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 1639 --end_time 1645 2>&1 | grep 'Shot detected'

echo -e "\n10. Testing 1766s (was: rim_bounce, should be: MADE rim_roll)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 1763 --end_time 1769 2>&1 | grep 'Shot detected'

echo -e "\n11. Testing 2685s (was: rim_bounce, should be: MADE rim_roll)"
python main.py --action video --video_path ../input/game1_farright.mp4 --model runs/detect/basketball_yolo11n2/weights/best.pt --start_time 2682 --end_time 2688 2>&1 | grep 'Shot detected'

echo -e "\n=========================================="
echo "SUMMARY"
echo "=========================================="
echo "Phase 1 (4 cases): Should all be MISSED"
echo "Phase 2 (2 cases): Should all be MADE"
echo "Phase 3 (5 cases): Should all be MADE (rim_roll)"
echo "Total: 11 cases tested"
echo "Expected outcome: 11/11 fixes = 90%+ accuracy on full video"
echo "=========================================="
