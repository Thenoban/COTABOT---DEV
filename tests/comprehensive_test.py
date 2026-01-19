
import asyncio
import sys
import os
import subprocess
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_FILES = [
    "tests/verify_squad_db.py",
    "tests/verify_event_db.py",
    "tests/verify_voice_db.py",
    "tests/verify_training_db.py"
]

def run_test(test_file):
    print(f"\n{'='*60}")
    print(f"RUNNING TEST: {test_file}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    try:
        # Verify file exists
        if not os.path.exists(test_file):
             print(f"FAIL: Test file not found: {test_file}")
             return False

        # Run script as subprocess
        result = subprocess.run(
            [sys.executable, test_file], 
            capture_output=True, 
            text=True, 
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            encoding='utf-8', errors='ignore' # Handle subprocess encoding too
        )
        
        # Print output
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return False
        
        duration = time.time() - start_time
        print(f"PASS: {test_file} COMPLETED in {duration:.2f}s")
        return True
        
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False

def main():
    print(f"STARTING COMPREHENSIVE SYSTEM VERIFICATION")
    print(f"Timestamp: {datetime.now()}")
    print(f"Environment: DEV")
    
    results = {}
    
    for test in TEST_FILES:
        success = run_test(test)
        results[test] = "PASS" if success else "FAIL"
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    all_passed = True
    for test, status in results.items():
        icon = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{icon} {test}: {status}")
        if status == "FAIL":
            all_passed = False
            
    print("-" * 60)
    if all_passed:
        print("ALL SYSTEMS OPERATIONAL")
    else:
        print("WARNING: SOME TESTS FAILED")

if __name__ == "__main__":
    main()
