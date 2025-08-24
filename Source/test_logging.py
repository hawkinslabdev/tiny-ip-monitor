#!/usr/bin/env python3

import os
import sys
import logging
from datetime import datetime

def test_logging():
    """Test logging functionality"""
    log_file = '/var/log/vpn-monitor.log'
    
    print("=" * 50)
    print("VPN Monitor Logging Test")
    print("=" * 50)
    
    # Test 1: Directory creation
    print("Test 1: Creating log directory...")
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        print("Success; Log directory created/exists")
    except Exception as e:
        print(f"❌ Failed to create log directory: {e}")
        return False
    
    # Test 2: File creation
    print("Test 2: Creating log file...")
    try:
        with open(log_file, 'a') as f:
            test_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Log test - file creation\n"
            f.write(test_message)
        print("Success; Log file created/writable")
    except Exception as e:
        print(f"❌ Failed to create/write log file: {e}")
        return False
    
    # Test 3: File permissions
    print("Test 3: Checking file permissions...")
    try:
        if os.path.exists(log_file):
            if os.access(log_file, os.R_OK):
                print("Success; Log file is readable")
            else:
                print("❌ Log file is not readable")
                
            if os.access(log_file, os.W_OK):
                print("Success; Log file is writable")
            else:
                print("❌ Log file is not writable")
        else:
            print("❌ Log file doesn't exist")
            return False
    except Exception as e:
        print(f"❌ Error checking permissions: {e}")
        return False
    
    # Test 4: Python logging
    print("Test 4: Testing Python logging...")
    try:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        logger = logging.getLogger(__name__)
        
        # Add file handler
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Test log messages
        logger.info("Python logging test - INFO level")
        logger.warning("Python logging test - WARNING level")
        logger.error("Python logging test - ERROR level")
        
        print("Success; Python logging successful")
    except Exception as e:
        print(f"❌ Python logging failed: {e}")
        return False
    
    # Test 5: Read back logs
    print("Test 5: Reading back log entries...")
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            print(f"Success; Log file contains {len(lines)} lines")
            
            if lines:
                print("Last few log entries:")
                for line in lines[-3:]:
                    print(f"  {line.strip()}")
            else:
                print("❌ Log file is empty")
                return False
                
    except Exception as e:
        print(f"❌ Failed to read log file: {e}")
        return False
    
    # Test 6: Monitor module logging
    print("Test 6: Testing monitor module...")
    try:
        sys.path.insert(0, '/app')
        from monitor import IPMonitor
        
        monitor = IPMonitor()
        print("Success; Monitor initialized with logging")
        
        # Test a quick IP check (this will log)
        current_ip = monitor.get_public_ip()
        if current_ip:
            print(f"Success; IP retrieval successful: {current_ip}")
        else:
            print("⚠️  IP retrieval failed (may be network issue)")
        
    except Exception as e:
        print(f"❌ Monitor module test failed: {e}")
        return False
    
    print("=" * 50)
    print("Success; All logging tests passed!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = test_logging()
    sys.exit(0 if success else 1)