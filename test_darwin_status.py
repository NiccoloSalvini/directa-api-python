#!/usr/bin/env python3
"""
Test script for Darwin status with enhanced connection tracking
"""

import sys
import time
import logging
from pprint import pprint
from directa_api.trading import DirectaTrading

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_darwin_status')

def test_darwin_status(host="127.0.0.1", port=10002):
    """
    Test the Darwin status functionality with multiple connection attempts
    """
    print(f"Testing Darwin status on {host}:{port}...")
    
    # Create trading instance
    trading = DirectaTrading(host=host, port=port)
    
    # First attempt to connect
    print("\n=== First connection attempt ===")
    connected = trading.connect()
    print(f"Connected: {connected}")
    
    if connected:
        # Check Darwin status
        print("\n=== Initial status check ===")
        status = trading.get_darwin_status()
        print("Darwin Status:")
        pprint(status)
        
        # Disconnect and reconnect to generate connection history
        print("\n=== Disconnecting... ===")
        trading.disconnect()
        
        # Wait a moment
        time.sleep(1)
        
        # Second connection attempt
        print("\n=== Second connection attempt ===")
        connected = trading.connect()
        print(f"Connected: {connected}")
        
        # Check Darwin status again
        if connected:
            print("\n=== Status after reconnection ===")
            status = trading.get_darwin_status()
            print("Darwin Status:")
            pprint(status)
            
            # Show connection metrics
            print("\n=== Connection Metrics ===")
            metrics = trading.get_connection_metrics()
            pprint(metrics)
            
            # Clean up
            trading.disconnect()
    
    print("\nTest completed.")

if __name__ == "__main__":
    # Use command line arguments for host/port if provided
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 10002
    
    test_darwin_status(host, port) 