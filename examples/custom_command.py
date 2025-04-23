#!/usr/bin/env python3
"""
Interactive script for testing custom commands with the Directa Trading API.
This is useful for exploring the API and testing commands not implemented in the wrapper.

Make sure the Darwin trading platform is running before executing this script.
"""

import os
import sys
import logging
import cmd
import json
import socket
import re

# Add parent directory to sys.path to import directa_api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from directa_api import DirectaTrading, get_error_message, get_order_status, ERROR_CODES

# Set logging level
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DirectaTrading")
logger.setLevel(logging.DEBUG)

def json_pretty_print(data):
    """Print data as formatted JSON"""
    print(json.dumps(data, indent=2, sort_keys=True))

class DirectaShell(cmd.Cmd):
    """Interactive shell for testing Directa Trading API commands"""
    
    intro = "Welcome to the Directa Trading API shell. Type help or ? to list commands.\n"
    prompt = "(directa) "
    
    def __init__(self):
        super().__init__()
        self.api = DirectaTrading()
        self.connected = False
    
    def json_pretty_print(self, data):
        """Format and print JSON data in a readable way"""
        if isinstance(data, str):
            try:
                # Try to parse it as JSON if it's a string
                data = json.loads(data)
            except json.JSONDecodeError:
                # If it's not valid JSON, just return it as is
                pass
        
        return json.dumps(data, indent=2, ensure_ascii=False)

    def preloop(self):
        print("Attempting to connect to Darwin...")
        try:
            self.connected = self.api.connect()
            if self.connected:
                print("Successfully connected to Darwin!")
            else:
                print("Failed to connect to Darwin. Is it running?")
        except socket.error as e:
            print(f"Socket error: {e}")
            print("Failed to connect. Make sure Darwin is running.")

    def postloop(self):
        if self.connected:
            self.api.disconnect()
            print("Disconnected from Darwin.")

    def do_connect(self, arg):
        """Connect to Darwin API"""
        if self.connected:
            print("Already connected to Darwin.")
            return
        
        try:
            self.connected = self.api.connect()
            if self.connected:
                print("Successfully connected to Darwin!")
            else:
                print("Failed to connect to Darwin. Is it running?")
        except socket.error as e:
            print(f"Socket error: {e}")
    
    def do_disconnect(self, arg):
        """Disconnect from Darwin API"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        self.api.disconnect()
        self.connected = False
        print("Disconnected from Darwin.")
    
    def do_status(self, arg):
        """Get Darwin status"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        response = self.api.get_darwin_status()
        print(self.json_pretty_print(response))
        
        if response.get("success", False):
            data = response.get("data", {})
            conn_status = data.get("connection_status", "Unknown")
            conn_description = data.get("connection_description", "")
            is_connected = data.get("is_connected", False)
            print(f"\nConnection Status: {conn_status}")
            print(f"Description: {conn_description}")
            print(f"Datafeed Enabled: {data.get('datafeed_enabled', False)}")
            print(f"Release: {data.get('release', 'Unknown')}")
            
            if not is_connected:
                print("\nWARNING: Trading connection not available.")
                print("Informational operations will work, but trading operations may fail.")
                print("Make sure Darwin platform is properly connected to Directa servers.")
        
    def do_portfolio(self, arg):
        """Get portfolio information"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        response = self.api.get_portfolio()
        if not response.get("success") and "error_code" in response:
            error_code = response["error_code"]
            print(f"Error {error_code}: {get_error_message(error_code)}")
        
        print(self.json_pretty_print(response))
        
    def do_account(self, arg):
        """Get account information"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        response = self.api.get_account_info()
        print(self.json_pretty_print(response))
        
    def do_availability(self, arg):
        """Get availability information"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        response = self.api.get_availability()
        print(self.json_pretty_print(response))
    
    def do_orders(self, arg):
        """Get active orders"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        response = self.api.get_orders()
        if not response.get("success") and "error_code" in response:
            error_code = response["error_code"]
            print(f"Error {error_code}: {get_error_message(error_code)}")
        
        print(self.json_pretty_print(response))
    
    def do_pending(self, arg):
        """Get pending orders"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        response = self.api.get_pending_orders()
        if not response.get("success") and "error_code" in response:
            error_code = response["error_code"]
            print(f"Error {error_code}: {get_error_message(error_code)}")
        
        print(self.json_pretty_print(response))
    
    def do_position(self, arg):
        """Get position for a symbol. Usage: position SYMBOL"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        if not arg:
            print("Please specify a symbol. Usage: position SYMBOL")
            return
            
        response = self.api.get_position(arg)
        print(self.json_pretty_print(response))
    
    def do_error(self, arg):
        """Look up an error code. Usage: error CODE"""
        if not arg:
            print("Please specify an error code. Usage: error CODE")
            return
        
        arg = arg.strip()
        if arg in ERROR_CODES:
            print(f"Error {arg}: {ERROR_CODES[arg]}")
        else:
            print(f"Unknown error code: {arg}")
            print("Available error codes:")
            for code, desc in ERROR_CODES.items():
                print(f"{code}: {desc}")
        
    def do_raw(self, arg):
        """Send a raw command to Darwin. Usage: raw COMMAND"""
        if not self.connected:
            print("Not connected to Darwin.")
            return
            
        if not arg:
            print("Please specify a command. Usage: raw COMMAND")
            return
            
        try:
            response = self.api.send_command(arg)
            print(f"Raw response: {response}")
            
            # Try to parse the response and display in a better format
            if re.match(r"^\d{4}:", response):
                error_code = response.split(":")[0]
                print(f"Error {error_code}: {get_error_message(error_code)}")
            
        except Exception as e:
            print(f"Error sending command: {e}")
    
    def do_exit(self, arg):
        """Exit the shell"""
        print("Exiting Directa Trading API shell...")
        return True
    
    def do_quit(self, arg):
        """Exit the shell"""
        return self.do_exit(arg)
    
    def do_EOF(self, arg):
        """Exit on Ctrl-D"""
        print()  # Add a newline
        return self.do_exit(arg)

if __name__ == "__main__":
    print("Make sure Darwin trading platform is running!")
    DirectaShell().cmdloop() 