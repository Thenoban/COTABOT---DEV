"""
Logging Configuration Test Script
Tests RotatingFileHandler and log level configuration
"""
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.logging_config import setup_logging


def test_log_rotation():
    """Test that log rotation works when file exceeds max size"""
    print("=== Test 1: Log Rotation ===")
    
    # Setup with small max bytes for testing (1KB)
    setup_logging(log_level="DEBUG", log_file="test_rotation.log", max_bytes=1024, backup_count=2)
    logger = logging.getLogger("RotationTest")
    
    # Generate lots of logs to trigger rotation
    for i in range(100):
        logger.info(f"Test log entry {i} " * 20)  # ~400 bytes per entry
    
    # Check if rotation happened
    files_created = []
    for f in ["test_rotation.log", "test_rotation.log.1", "test_rotation.log.2"]:
        if os.path.exists(f):
            files_created.append(f)
            size = os.path.getsize(f)
            print(f"  ✅ {f} exists ({size} bytes)")
    
    # Cleanup
    for f in files_created:
        os.remove(f)
    
    if len(files_created) >= 2:
        print("  ✅ Log rotation test PASSED!")
        return True
    else:
        print("  ❌ Log rotation test FAILED - no rotation occurred")
        return False


def test_log_levels():
    """Test that log levels work correctly"""
    print("\n=== Test 2: Log Levels ===")
    
    # Test WARNING level (should NOT show DEBUG/INFO)
    setup_logging(log_level="WARNING", log_file="test_levels.log")
    logger = logging.getLogger("LevelTest")
    
    logger.debug("DEBUG: This should NOT appear")
    logger.info("INFO: This should NOT appear")
    logger.warning("WARNING: This SHOULD appear")
    logger.error("ERROR: This SHOULD appear")
    
    # Read log file
    with open("test_levels.log", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Cleanup
    os.remove("test_levels.log")
    
    # Verify
    has_warning = "WARNING: This SHOULD appear" in content
    has_error = "ERROR: This SHOULD appear" in content
    no_debug = "DEBUG: This should NOT appear" not in content
    no_info = "INFO: This should NOT appear" not in content
    
    if has_warning and has_error and no_debug and no_info:
        print("  ✅ Log level filtering PASSED!")
        print(f"     - WARNING messages: shown ✓")
        print(f"     - ERROR messages: shown ✓")
        print(f"     - DEBUG messages: hidden ✓")
        print(f"     - INFO messages: hidden ✓")
        return True
    else:
        print("  ❌ Log level filtering FAILED")
        return False


def test_env_variables():
    """Test environment variable configuration"""
    print("\n=== Test 3: Environment Variables ===")
    
    # Set environment variables
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["LOG_MAX_BYTES"] = "2048"
    os.environ["LOG_BACKUP_COUNT"] = "3"
    
    # Setup should read from env
    setup_logging(log_file="test_env.log")
    logger = logging.getLogger("EnvTest")
    
    logger.info("This should NOT appear (level=ERROR)")
    logger.error("This SHOULD appear (level=ERROR)")
    
    # Read log file
    with open("test_env.log", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Cleanup
    os.remove("test_env.log")
    del os.environ["LOG_LEVEL"]
    del os.environ["LOG_MAX_BYTES"]
    del os.environ["LOG_BACKUP_COUNT"]
    
    # Verify
    has_error = "This SHOULD appear" in content
    no_info = "This should NOT appear" not in content
    
    if has_error and no_info:
        print("  ✅ Environment variable configuration PASSED!")
        print("     - LOG_LEVEL env var respected ✓")
        return True
    else:
        print("  ❌ Environment variable configuration FAILED")
        return False


if __name__ == "__main__":
    print("Testing Logging Configuration\n")
    
    test1 = test_log_rotation()
    test2 = test_log_levels()
    test3 = test_env_variables()
    
    print("\n" + "="*50)
    if test1 and test2 and test3:
        print("✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
