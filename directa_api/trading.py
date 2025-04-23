import socket
import logging
import time
import re
import datetime
import random
from typing import Optional, Dict, List, Union, Tuple, Any

from directa_api.parsers import (
    parse_portfolio_response,
    parse_order_response,
    parse_orders_response,
    parse_account_info_response,
    parse_darwin_status_response
)
from directa_api.errors import is_error_response, parse_error_response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class DirectaTrading:
    """
    A wrapper for the Directa Trading API (port 10002)
    
    This class handles socket connections to the Directa Trading API
    for executing trades and managing orders.
    
    Note: Requires the Darwin trading platform to be running.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 10002, buffer_size: int = 4096, 
                 simulation_mode: bool = False):
        """
        Initialize the DirectaTrading API wrapper
        
        Args:
            host: The hostname (default: 127.0.0.1)
            port: The port for trading API (default: 10002)
            buffer_size: Socket buffer size for receiving responses
            simulation_mode: If True, simulates trading operations without real money
        """
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.socket = None
        self.logger = logging.getLogger("DirectaTrading")
        self.connected = False
        self.last_darwin_status = None
        self.connection_status = "UNKNOWN"
        self.is_trading_connected = False
        self.simulation_mode = simulation_mode
        
        # Connection tracking
        self.connection_history = []
        self.connection_attempts = 0
        self.last_connection_time = None
        self.last_status_check = None
        self.connection_state_changes = []
        
        # Simulation data (used only in simulation mode)
        self.simulated_portfolio = []
        self.simulated_orders = {}  # Dictionary with order_id as key
        self.simulated_account = {
            "account_code": "SIM1234",
            "liquidity": 10000.0,
            "equity": 10000.0
        }
        
        if simulation_mode:
            self.logger.warning("SIMULATION MODE ACTIVE - No real trading will occur")
    
    def set_connection_status(self, status: str, is_connected: bool) -> None:
        """
        Update the connection status and record the change
        
        Args:
            status: The new connection status
            is_connected: Whether the connection is active
        """
        # Only record changes
        if status != self.connection_status:
            # Record the state change
            timestamp = datetime.datetime.now()
            change = {
                "timestamp": timestamp,
                "previous_status": self.connection_status,
                "new_status": status,
                "duration": None
            }
            
            # Calculate duration of previous state if we have previous records
            if self.connection_state_changes:
                prev_change = self.connection_state_changes[-1]
                if "timestamp" in prev_change:
                    prev_change["duration"] = (timestamp - prev_change["timestamp"]).total_seconds()
            
            self.connection_state_changes.append(change)
            
            # Update current status
            self.connection_status = status
            self.is_trading_connected = is_connected
            self.logger.info(f"Connection status changed: {self.connection_status}")
    
    def connect(self) -> bool:
        """
        Establish a connection to the Directa Trading API
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connection_attempts += 1
            self.last_connection_time = datetime.datetime.now()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.logger.info(f"Connected to Directa Trading API on {self.host}:{self.port}")
            
            # Record connection success
            self.connection_history.append({
                "timestamp": self.last_connection_time,
                "attempt": self.connection_attempts,
                "success": True,
                "details": f"Connected to {self.host}:{self.port}"
            })
            
            # Use a longer timeout for initial connection to match telnet behavior
            self.socket.settimeout(3.0)  
            
            # Read initial data similar to telnet
            try:
                # Wait a short time to ensure all initial data is received
                time.sleep(0.2)
                
                initial_data = b""
                try:
                    while True:
                        chunk = self.socket.recv(self.buffer_size)
                        if not chunk:
                            break
                        initial_data += chunk
                        
                        # If we received a complete message with a newline, it's likely complete
                        if b'\n' in chunk:
                            # Check if we've already received a status message
                            if b'DARWIN_STATUS' in initial_data:
                                break
                except (socket.timeout, BlockingIOError):
                    # No more initial data available, this is expected
                    pass
                
                if initial_data:
                    initial_text = initial_data.decode('utf-8')
                    self.logger.debug(f"Initial data received on connect: {initial_text.strip()}")
                    
                    # Check for darwin status in initial data
                    self._check_for_darwin_status(initial_text)
            except Exception as e:
                self.logger.warning(f"Error processing initial data: {str(e)}")
            finally:
                # Restore normal timeout
                self.socket.settimeout(2.0)
            
            # If we didn't get a status yet, explicitly request it
            if not self.last_darwin_status or self.connection_status == "UNKNOWN":
                try:
                    status_response = self._update_darwin_status()
                    if "CONN_OK" in status_response and not self.is_trading_connected:
                        # Force update connection status if response says CONN_OK
                        self.set_connection_status("CONN_OK", True)
                        self.logger.info("Connection status updated to CONN_OK from explicit check")
                except Exception as e:
                    self.logger.warning(f"Failed to get initial Darwin status: {str(e)}")
            
            return True
        except socket.error as e:
            self.logger.error(f"Error connecting to Trading API: {str(e)}")
            self.connected = False
            
            # Record connection failure
            self.connection_history.append({
                "timestamp": datetime.datetime.now(),
                "attempt": self.connection_attempts,
                "success": False,
                "error": str(e),
                "details": f"Failed to connect to {self.host}:{self.port}"
            })
            return False
    
    def _update_darwin_status(self):
        """
        Request and update the Darwin platform status
        
        Returns:
            The response text from the API
        """
        self.last_status_check = datetime.datetime.now()
        try:
            response = self.send_command("DARWINSTATUS")
            self._check_for_darwin_status(response)
            return response
        except Exception as e:
            self.logger.error(f"Error getting Darwin status: {str(e)}")
            # Create a failure response in the expected format
            error_response = f"DARWIN_STATUS;CONN_ERROR;ERROR;{str(e)}"
            # Update local status
            self.set_connection_status("CONN_ERROR", False)
            return error_response
    
    def _check_for_darwin_status(self, response_text: str):
        """
        Parse Darwin status from response text and update connection state
        
        Args:
            response_text: The response text from Darwin
        """
        # First look for all DARWIN_STATUS lines in the response
        status_lines = []
        for line in response_text.strip().split('\n'):
            if "DARWIN_STATUS" in line:
                status_lines.append(line)
                
        if not status_lines:
            # No status lines found, nothing to update
            return
            
        # Try to find a CONN_OK status among the lines
        best_status = None
        best_status_priority = -1
        
        # Status priority (higher is better)
        status_priority = {
            "CONN_OK": 3,
            "CONN_UNAVAILABLE": 1,
            "CONN_ERROR": 0,
            "UNKNOWN": -1
        }
        
        # Check each status line
        for status_line in status_lines:
            match = re.search(r'DARWIN_STATUS;([^;]+);([^;]+);', status_line)
            if match:
                new_status = match.group(1)
                app_status = match.group(2)
                
                # Update our best status if this is better
                current_priority = status_priority.get(new_status, -1)
                if current_priority > best_status_priority:
                    best_status = (new_status, app_status, status_line)
                    best_status_priority = current_priority
        
        # If we found a valid status, use it
        if best_status:
            new_status, app_status, status_line = best_status
            self.last_darwin_status = status_line
            
            # Update connection status
            is_connected = new_status == "CONN_OK"
            self.set_connection_status(new_status, is_connected)
            self.logger.debug(f"Darwin status: connection={new_status}, application={app_status}")
            
            # Validate using the parser as well
            try:
                status_info = parse_darwin_status_response(status_line)
                
                # If the parser and regex disagree, log it
                if status_info["data"]:
                    parser_status = status_info["data"].get("connection_status")
                    if parser_status and parser_status != new_status:
                        self.logger.warning(
                            f"Connection status mismatch: regex found '{new_status}' but parser found '{parser_status}'"
                        )
            except Exception as e:
                self.logger.warning(f"Error validating status with parser: {str(e)}")
        else:
            # If we can't parse with regex but the response contains DARWIN_STATUS
            try:
                # Use the parser directly
                status_info = parse_darwin_status_response(response_text)
                
                if "data" in status_info and status_info["data"]:
                    new_status = status_info["data"].get("connection_status", "UNKNOWN")
                    is_connected = new_status == "CONN_OK"
                    self.last_darwin_status = response_text
                    self.set_connection_status(new_status, is_connected)
                    
                    if "details" in status_info["data"]:
                        self.logger.debug(f"Darwin status details: {status_info['data']['details']}")
                else:
                    # Only set error state if we haven't found a better status
                    if self.connection_status == "UNKNOWN":
                        self.set_connection_status("CONN_ERROR", False)
                    if status_info.get("error"):
                        self.logger.warning(f"Darwin status error: {status_info['error']}")
            except Exception as e:
                self.logger.warning(f"Error parsing status with parser: {str(e)}")
                
        # Double-check socket connection state for consistency
        if self.connected and self.connection_status != "CONN_OK":
            # Try one more manual check to verify - sometimes the automatic status is wrong
            try:
                self.logger.debug("Socket connected but Darwin reports not connected. Performing manual check...")
                manual_check = self.send_command("DARWINSTATUS")
                if "CONN_OK" in manual_check:
                    self.logger.info("Manual status check found CONN_OK, updating status")
                    self.set_connection_status("CONN_OK", True)
            except Exception as e:
                self.logger.warning(f"Manual status check failed: {str(e)}")
    
    def disconnect(self) -> None:
        """Close the connection to the Directa Trading API"""
        if self.socket and self.connected:
            self.socket.close()
            self.logger.info("Disconnected from Directa Trading API")
            
            # Record disconnection
            timestamp = datetime.datetime.now()
            self.connection_history.append({
                "timestamp": timestamp,
                "details": "Disconnected from API",
                "was_connected": self.connected
            })
            
            # Update connection status
            self.set_connection_status("DISCONNECTED", False)
        
        self.connected = False
        self.socket = None
    
    def __enter__(self):
        """Support for context manager protocol"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for context manager protocol"""
        self.disconnect()
    
    def send_command(self, command: str) -> str:
        """
        Send a command to the Directa Trading API
        
        Args:
            command: The command string to send
        
        Returns:
            str: The response from the server
        
        Raises:
            ConnectionError: If not connected to the API
            socket.error: If an error occurs during sending/receiving
        """
        if not self.connected or not self.socket:
            raise ConnectionError("Not connected to Directa Trading API")
        
        # Ensure command ends with newline
        if not command.endswith('\n'):
            command += '\n'
        
        try:
            self.logger.debug(f"Sending command: {command.strip()}")
            self.socket.sendall(command.encode('utf-8'))
            
            # Use slightly different timeout for status checks vs other commands
            if command.strip() == "DARWINSTATUS":
                # Use longer timeout for status checks
                self.socket.settimeout(3.0)
            else:
                # Use standard timeout for other commands
                self.socket.settimeout(2.0)
                
            response = b""
            
            # Read response with a timeout loop
            start_time = time.time()
            max_time = 3.0  # Maximum 3 seconds 
            
            while time.time() - start_time < max_time:
                try:
                    chunk = self.socket.recv(self.buffer_size)
                    if not chunk:  # If no data, break
                        if response:  # But only if we already have some data
                            break
                        # Otherwise keep waiting a bit
                        time.sleep(0.1)
                        continue
                        
                    response += chunk
                    
                    # Special handling for DARWINSTATUS - wait longer to get proper status
                    if command.strip() == "DARWINSTATUS" and b"DARWIN_STATUS" in response:
                        # When we get a DARWIN_STATUS response, wait a bit more for complete data
                        time.sleep(0.1)
                        try:
                            # Try to get any additional data
                            self.socket.settimeout(0.2)
                            more_data = self.socket.recv(self.buffer_size)
                            if more_data:
                                response += more_data
                        except (socket.timeout, BlockingIOError):
                            pass  # No more data available, which is fine
                        # Found our status response, can break
                        break
                        
                    # For other commands, if we see a complete response, stop waiting
                    if b'\n' in chunk:
                        # If we have a command-specific response, we can break
                        if (command.strip() == "INFOACCOUNT" and b"INFOACCOUNT" in response) or \
                           (command.strip() == "INFOSTOCKS" and (b"STOCK" in response or b"ERR" in response)) or \
                           (command.strip() == "ORDERLIST" and (b"ORDER" in response or b"ERR" in response)) or \
                           (b"ERR" in response):  # Always break on error
                            break
                        
                        # For other responses, wait a short time for any additional data
                        time.sleep(0.1)
                        try:
                            self.socket.settimeout(0.1)
                            more_data = self.socket.recv(self.buffer_size)
                            if more_data:
                                response += more_data
                        except (socket.timeout, BlockingIOError):
                            pass  # No more data, which is fine
                        break
                except socket.timeout:
                    # No data received within timeout
                    if response:  # If we already have data, we can stop
                        break
            
            # Restore standard timeout
            self.socket.settimeout(2.0)
            
            # If we didn't get any response, raise an error
            if not response:
                raise ConnectionError("No response received from server")
                
            response_text = response.decode('utf-8')
            self.logger.debug(f"Received response: {response_text.strip()}")
            
            # Check for darwin status in the response
            self._check_for_darwin_status(response_text)
            
            # Special handling for multi-line responses
            lines = response_text.strip().split('\n')
            if len(lines) > 1:
                # Find the right response line based on the command
                cmd_name = command.strip()
                cmd_prefix = ""
                
                # Map commands to expected response prefixes
                if cmd_name == "DARWINSTATUS":
                    cmd_prefix = "DARWIN_STATUS"
                elif cmd_name == "INFOACCOUNT":
                    cmd_prefix = "INFOACCOUNT"
                elif cmd_name == "INFOAVAILABILITY":
                    cmd_prefix = "AVAILABILITY"
                elif cmd_name == "INFOSTOCKS":
                    cmd_prefix = "STOCK"
                elif cmd_name == "ORDERLIST":
                    cmd_prefix = "ORDER"
                
                # Search for matching response line
                for line in lines:
                    # Direct match with prefix
                    if line.startswith(cmd_prefix):
                        return line
                    # Check for contained prefix (e.g., DARWIN_STATUS in a larger line)
                    if cmd_prefix and cmd_prefix in line:
                        return line
                    # Always prioritize error responses
                    if line.startswith("ERR;"):
                        return line
                
                # Special case for DARWINSTATUS - always return line with DARWIN_STATUS if found
                if cmd_name == "DARWINSTATUS":
                    for line in lines:
                        if "DARWIN_STATUS" in line:
                            return line
                
                # Special case for INFOAVAILABILITY - also look for AVAILABILITY
                if cmd_name == "INFOAVAILABILITY":
                    for line in lines:
                        if line.startswith("AVAILABILITY"):
                            return line
                
                # If no specific match found, return the last non-empty line
                for line in reversed(lines):
                    if line.strip():
                        return line
            
            return response_text
        except socket.error as e:
            self.logger.error(f"Socket error: {str(e)}")
            raise
    
    # Trading API commands
    
    def get_portfolio(self, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get the current portfolio information (stocks in portfolio and in trading)
        
        Args:
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with portfolio data or raw response string
        """
        if self.simulation_mode:
            # In simulation mode, return simulated portfolio data
            if not self.simulated_portfolio:
                # Empty portfolio
                response = "ERR;N/A;1018"
            else:
                # Format portfolio entries
                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                portfolio_lines = []
                
                for position in self.simulated_portfolio:
                    line = f"STOCK;{position['symbol']};{current_time};{position['quantity']};0;0;{position.get('avg_price', 0)};{position.get('gain', 0)}"
                    portfolio_lines.append(line)
                
                response = "\n".join(portfolio_lines)
            
            if not parse:
                return response
            return parse_portfolio_response(response)
            
        # Real mode - use actual API
        response = self.send_command("INFOSTOCKS")
        if parse:
            return parse_portfolio_response(response)
        return response
    
    def get_account_info(self, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get account information
        
        Args:
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with account details or raw response string
        """
        if self.simulation_mode:
            # In simulation mode, return simulated account data
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            response = f"INFOACCOUNT;{current_time};{self.simulated_account['account_code']};{self.simulated_account['liquidity']};0;0.0;{self.simulated_account['equity']};SIM"
            
            if not parse:
                return response
            return parse_account_info_response(response)
        
        # Real mode - use actual API
        response = self.send_command("INFOACCOUNT")
        if parse:
            return parse_account_info_response(response)
        return response
    
    def get_availability(self, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get portfolio liquidity information
        
        Args:
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with portfolio liquidity details or raw response string
        """
        response = self.send_command("INFOAVAILABILITY")
        if parse:
            return parse_account_info_response(response)
        return response
    
    def get_darwin_status(self, parse: bool = True, retry: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get Darwin platform status information
        
        Args:
            parse: Whether to parse the response (default: True)
            retry: Whether to retry if first attempt fails (default: True)
            
        Returns:
            Dictionary with Darwin status information or raw response string
        """
        if self.simulation_mode:
            # In simulation mode, always return a successful connection
            response = "DARWIN_STATUS;CONN_OK;TRUE;Release 2.5.1 build SIMULATION more info at http://app1.directatrading.com/trading-api-directa/index.html"
            
            if not parse:
                return response
                
            # Parse the simulated response
            status_resp = parse_darwin_status_response(response, self)
            
            # Add connection metrics in simulation mode
            if "data" in status_resp and status_resp["data"] is not None:
                status_resp["data"]["connection_metrics"] = self.get_connection_metrics()
                status_resp["data"]["simulation_mode"] = True
            
            return status_resp
        
        # Real mode - standard processing
        try:
            response = self._update_darwin_status()
        except Exception as e:
            if retry:
                self.logger.warning(f"First Darwin status check failed: {str(e)}. Retrying...")
                # Short pause before retry
                time.sleep(0.5)
                try:
                    response = self._update_darwin_status()
                except Exception as e2:
                    self.logger.error(f"Darwin status check failed after retry: {str(e2)}")
                    # Create error response
                    response = f"DARWIN_STATUS;CONN_ERROR;ERROR;{str(e2)}"
            else:
                self.logger.error(f"Darwin status check failed: {str(e)}")
                response = f"DARWIN_STATUS;CONN_ERROR;ERROR;{str(e)}"
        
        if not parse:
            return response
            
        # Use the enhanced parser that accepts the trading instance
        status_resp = parse_darwin_status_response(response, self)
        
        # Add detailed connection metrics
        if "data" in status_resp and status_resp["data"] is not None:
            status_resp["data"]["connection_metrics"] = self.get_connection_metrics()
        
        return status_resp
    
    def get_position(self, symbol: str, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get information about a specific position
        
        Args:
            symbol: The symbol/ticker to get position for
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with position details or raw response string
        """
        response = self.send_command(f"GETPOSITION {symbol}")
        if parse:
            return parse_portfolio_response(response)
        return response
    
    def place_order(self, symbol: str, side: str, quantity: int, 
                   price: Optional[float] = None, order_type: str = "LIMIT", 
                   parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a new order
        
        Args:
            symbol: The stock symbol
            side: "BUY" or "SELL"
            quantity: Number of shares
            price: Price per share (required for LIMIT orders)
            order_type: Type of order ("LIMIT", "MARKET", etc.)
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        side = side.upper()
        order_type = order_type.upper()
        
        if order_type == "LIMIT" and price is None:
            raise ValueError("Price must be specified for LIMIT orders")
        
        # Map side to Directa API commands
        if side == "BUY":
            cmd_prefix = "ACQAZ" if order_type == "LIMIT" else "ACQMARKET"
        elif side == "SELL":
            cmd_prefix = "VENAZ" if order_type == "LIMIT" else "VENMARKET"
        else:
            raise ValueError("Side must be either 'BUY' or 'SELL'")
        
        # Generate a unique order ID with timestamp and a random component
        order_id = f"ORD{int(time.time())}_{random.randint(1000, 9999)}"
        
        if order_type == "LIMIT":
            command = f"{cmd_prefix} {order_id},{symbol},{quantity},{price}"
        else:
            command = f"{cmd_prefix} {order_id},{symbol},{quantity}"
        
        if self.simulation_mode:
            # In simulation mode, create simulated order response
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Create the simulated order
            new_order = {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "order_type": order_type,
                "status": "PENDING",
                "time": current_time
            }
            
            # Add to simulated orders dictionary with order_id as key
            self.simulated_orders[order_id] = new_order
            
            # Create simulated response
            response = f"TRADOK;{symbol};{order_id};SENT;{side};{quantity};{price};0;0;{quantity};SIMREF001;{command}"
            
            if not parse:
                return response
            
            return parse_order_response(response)
        
        # Real mode - use actual API
        response = self.send_command(command)
        
        # Check if we need to confirm the order
        if "TRADCONFIRM" in response:
            if not parse:
                return response
                
            # Check if we should automatically confirm
            confirm_response = parse_order_response(response)
            if confirm_response.get("confirmation_required", False):
                # Get the order ID from the response
                order_id = confirm_response.get("data", {}).get("order_id")
                if order_id:
                    # Send confirmation
                    confirm_cmd = f"CONFORD {order_id}"
                    response = self.send_command(confirm_cmd)
        
        if parse:
            return parse_order_response(response)
        return response
    
    def cancel_order(self, order_id: str, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Cancel an existing order
        
        Args:
            order_id: The ID of the order to cancel
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with cancellation details or raw response string
        """
        if self.simulation_mode:
            # In simulation mode, find and update the order in our simulated list
            order_found = False
            for order in self.simulated_orders.values():
                if order["order_id"] == order_id:
                    order["status"] = "CANCELLED"
                    order_found = True
                    break
            
            if order_found:
                symbol = next((o["symbol"] for o in self.simulated_orders.values() if o["order_id"] == order_id), "UNKNOWN")
                response = f"TRADOK;{symbol};{order_id};CANCELLED;CANCEL;0;0;0;0;0;SIMREF002;REVORD {order_id}"
            else:
                response = "ERR;N/A;1020"  # Order not found
                
            if not parse:
                return response
            return parse_order_response(response)
            
        # Real mode - use actual API
        response = self.send_command(f"REVORD {order_id}")
        if parse:
            return parse_order_response(response)
        return response
    
    def cancel_all_orders(self, symbol: str, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Cancel all orders for a specific symbol
        
        Args:
            symbol: The symbol/ticker to cancel all orders for
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with cancellation details or raw response string
        """
        response = self.send_command(f"REVALL {symbol}")
        if parse:
            return parse_order_response(response)
        return response
    
    def modify_order(self, order_id: str, price: float, 
                    signal_price: Optional[float] = None, 
                    parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Modify an existing order
        
        Args:
            order_id: The ID of the order to modify
            price: The new price
            signal_price: The new signal price (for stop orders)
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with modification details or raw response string
        """
        if signal_price is not None:
            command = f"MODORD {order_id},{price},{signal_price}"
        else:
            command = f"MODORD {order_id},{price}"
            
        response = self.send_command(command)
        if parse:
            return parse_order_response(response)
        return response
    
    def get_orders(self, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get all orders
        
        Args:
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with orders data or raw response string
        """
        if self.simulation_mode:
            # In simulation mode, return simulated orders data
            if not self.simulated_orders:
                # No orders
                response = "ERR;N/A;1019"
            else:
                # Format order entries
                order_lines = []
                
                for order in self.simulated_orders.values():
                    line = f"ORDER;{order['symbol']};{order['time']};{order['order_id']};{order['side']};{order['price']};0;{order['quantity']};{order['status']}"
                    order_lines.append(line)
                
                response = "\n".join(order_lines)
            
            if not parse:
                return response
            return parse_orders_response(response)
            
        # Real mode - use actual API
        response = self.send_command("ORDERLIST")
        if parse:
            return parse_orders_response(response)
        return response
    
    def get_pending_orders(self, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get pending orders only
        
        Args:
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with pending orders data or raw response string
        """
        response = self.send_command("ORDERLISTPENDING")
        if parse:
            return parse_orders_response(response)
        return response
    
    def get_orders_for_symbol(self, symbol: str, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get orders for a specific symbol
        
        Args:
            symbol: The symbol/ticker to get orders for
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with orders data for the symbol or raw response string
        """
        response = self.send_command(f"ORDERLIST {symbol}")
        if parse:
            return parse_orders_response(response)
        return response
    
    def get_connection_metrics(self) -> Dict[str, Any]:
        """
        Generate a summary of connection metrics and status history
        
        Returns:
            Dictionary with connection metrics and history
        """
        # Create a summary of connection history
        changes = self.connection_state_changes[-10:] if len(self.connection_state_changes) > 10 else self.connection_state_changes
        
        history_summary = []
        for change in changes:
            entry = {
                "timestamp": change["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                "from": change["previous_status"],
                "to": change["new_status"],
            }
            if change.get("duration") is not None:
                entry["duration_seconds"] = change["duration"]
            history_summary.append(entry)
        
        # Calculate connection statistics
        total_connections = len([h for h in self.connection_history if h.get("success") is True])
        failed_connections = len([h for h in self.connection_history if h.get("success") is False])
        
        # Calculate uptime percentage if we have state changes
        uptime_percentage = None
        if self.connection_state_changes:
            connected_duration = sum([
                change.get("duration", 0) 
                for change in self.connection_state_changes 
                if change.get("new_status") == "CONN_OK" and change.get("duration") is not None
            ])
            total_duration = sum([
                change.get("duration", 0) 
                for change in self.connection_state_changes 
                if change.get("duration") is not None
            ])
            if total_duration > 0:
                uptime_percentage = (connected_duration / total_duration) * 100
        
        return {
            "currently_connected": self.is_trading_connected,
            "connection_status": self.connection_status,
            "connection_attempts": self.connection_attempts,
            "successful_connections": total_connections,
            "failed_connections": failed_connections,
            "uptime_percentage": uptime_percentage,
            "last_connection_time": self.last_connection_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_connection_time else None,
            "last_status_check": self.last_status_check.strftime("%Y-%m-%d %H:%M:%S") if self.last_status_check else None,
            "connection_history": history_summary
        }
    
    # Simulation helper methods
    def add_simulated_position(self, symbol: str, quantity: int, price: float):
        """
        Add a position to the simulated portfolio.
        If the position already exists, update its quantity and average price.
        
        Args:
            symbol: The symbol of the position
            quantity: The quantity to add (can be negative for selling)
            price: The price of the new position
        """
        if not self.simulation_mode:
            self.logger.warning("add_simulated_position called but simulation mode is not active")
            return
        
        # Find if we already have this position
        for position in self.simulated_portfolio:
            if position["symbol"] == symbol:
                # Calculate new average price based on quantities
                new_qty = position["quantity"] + quantity
                if new_qty <= 0:
                    # Remove this position if quantity goes to 0 or negative
                    self.simulated_portfolio = [p for p in self.simulated_portfolio if p["symbol"] != symbol]
                    return
                
                position["avg_price"] = ((position["quantity"] * position["avg_price"]) + 
                                        (quantity * price)) / new_qty
                position["quantity"] = new_qty
                self.logger.debug(f"Updated simulated position: {position}")
                # Update total balance after position change
                self.update_simulated_total_balance()
                return
        
        # New position
        if quantity <= 0:
            self.logger.warning(f"Tried to add a new position with quantity <= 0: {symbol}, {quantity}")
            return
        
        new_position = {
            "symbol": symbol,
            "quantity": quantity,
            "avg_price": price
        }
        self.simulated_portfolio.append(new_position)
        self.logger.debug(f"Added new simulated position: {new_position}")
        # Update total balance after new position
        self.update_simulated_total_balance()
    
    def remove_simulated_position(self, symbol: str) -> bool:
        """
        Remove a position from the simulated portfolio (simulation mode only)
        
        Args:
            symbol: Symbol/ticker to remove
            
        Returns:
            True if position was found and removed, False otherwise
        """
        if not self.simulation_mode:
            self.logger.warning("remove_simulated_position called but simulation mode is not active")
            return False
            
        initial_length = len(self.simulated_portfolio)
        self.simulated_portfolio = [p for p in self.simulated_portfolio if p["symbol"] != symbol]
        
        if len(self.simulated_portfolio) < initial_length:
            self.logger.info(f"Removed simulated position: {symbol}")
            return True
            
        self.logger.warning(f"Attempted to remove non-existent position: {symbol}")
        return False
    
    def update_simulated_account(self, liquidity: float = None, equity: float = None) -> None:
        """
        Update the simulated account (simulation mode only)
        
        Args:
            liquidity: New liquidity value (if None, kept unchanged)
            equity: New equity value (if None, kept unchanged)
        """
        if not self.simulation_mode:
            self.logger.warning("update_simulated_account called but simulation mode is not active")
            return
            
        if liquidity is not None:
            self.simulated_account["liquidity"] = liquidity
            
        if equity is not None:
            self.simulated_account["equity"] = equity
            
        self.logger.info(f"Updated simulated account: liquidity={self.simulated_account['liquidity']}, equity={self.simulated_account['equity']}")
    
    def fix_test(self):
        """Reset simulated account and portfolio for testing."""
        if not self.simulation_mode:
            logging.warning("fix_test called but simulation mode is not active")
            return

        # Reset to initial state
        self.simulated_account = {
            "account_code": "SIM1234",  # Important for get_account_info
            "broker_id": "DEMO",
            "account_name": "Simulated Account",
            "currency": "EUR",
            "liquidity": 10000.0,
            "equity": 10000.0,
            "mtd": 0.0,
            "ytd": 0.0,
            "pl_daily": 0.0,
            "pl_ytd": 0.0,
            "total_balance": 10000.0,
        }
        self.simulated_portfolio = []
        self.simulated_orders = {}
        logging.info("Simulation state reset for testing")
        return {"success": True, "data": "Simulation reset"}

    def simulate_order_execution(self, order_req: Union[str, dict], fill_price: Optional[float] = None, executed_price: Optional[float] = None) -> dict:
        """
        Simulates the execution of an order by updating the account balances and portfolio.
        
        Args:
            order_req: Either the order ID (string) or the order details (dictionary)
            fill_price: Price at which the order is filled (if None, use the price from order_req)
            executed_price: Alternative name for fill_price (for backward compatibility)
        
        Returns:
            A dictionary containing the simulated response with execution details
        """
        if not self.simulation_mode:
            self.logger.warning("simulate_order_execution called but simulation mode is not active")
            return {"success": False, "error": "Simulation mode not active"}
        
        # Use executed_price if provided (for backward compatibility)
        if executed_price is not None:
            fill_price = executed_price
            
        # If order_req is a string (order ID), find the order in simulated_orders
        if isinstance(order_req, str):
            order_id = order_req
            found_order = None
            for order in self.simulated_orders.values():
                if order.get("order_id") == order_id:
                    found_order = order
                    order_req = order
                    break
            else:
                return {"success": False, "error": f"Order ID {order_id} not found"}
        
        # Extract order details
        symbol = order_req.get("symbol", "")
        side = order_req.get("side", "").upper()
        quantity = int(order_req.get("quantity", 0))
        price = fill_price if fill_price is not None else float(order_req.get("price", 0))
        
        # Check for required fields
        if not all([symbol, side, quantity, price]):
            return {"success": False, "error": "Missing required order fields"}
        
        # Calculate order value
        order_value = quantity * price
        
        # Update account based on order type
        if side == "BUY":
            # Check if we have enough liquidity
            if order_value > self.simulated_account.get("liquidity", 0):
                return {"success": False, "error": "Insufficient funds for buy order"}
            
            # Reduce liquidity
            self.simulated_account["liquidity"] -= order_value
            
            # Add position
            self.add_simulated_position(symbol, quantity, price)
            
        elif side == "SELL":
            # Find the position
            position_found = False
            for position in self.simulated_portfolio:
                if position["symbol"] == symbol:
                    if position["quantity"] < quantity:
                        return {"success": False, "error": "Insufficient shares for sell order"}
                    
                    # Increase liquidity (we sold shares)
                    self.simulated_account["liquidity"] += order_value
                    
                    # Reduce position quantity
                    new_qty = position["quantity"] - quantity
                    if new_qty == 0:
                        # Remove position completely
                        self.simulated_portfolio = [p for p in self.simulated_portfolio if p["symbol"] != symbol]
                    else:
                        # Update quantity
                        position["quantity"] = new_qty
                    
                    position_found = True
                    break
            
            if not position_found:
                return {"success": False, "error": f"Position {symbol} not found in portfolio"}
        else:
            return {"success": False, "error": f"Unsupported order side: {side}"}
        
        # Update total balance after the operation
        self.update_simulated_total_balance()
        
        # Create a simulated execution response
        execution_resp = {
            "success": True,
            "data": {
                "order_id": f"sim-{int(time.time() * 1000)}",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "value": order_value,
                "execution_time": datetime.datetime.now().isoformat(),
                "account_status": {
                    "liquidity": self.simulated_account.get("liquidity", 0),
                    "portfolio_count": len(self.simulated_portfolio),
                    "total_balance": self.simulated_account.get("total_balance", 0)
                }
            }
        }
        
        self.logger.info(f"Simulated order execution: {side} {quantity} {symbol} @ {price}")
        return execution_resp
    
    def update_simulated_total_balance(self):
        """
        Update the total balance of the simulated account based on cash liquidity and portfolio value.
        """
        if not self.simulation_mode:
            self.logger.warning("update_simulated_total_balance called but simulation mode is not active")
            return
            
        portfolio_value = 0.0
        for position in self.simulated_portfolio:
            portfolio_value += position["quantity"] * position.get("avg_price", 0)
            
        self.simulated_account["total_balance"] = self.simulated_account["liquidity"] + portfolio_value
        self.logger.info(f"Updated simulated total balance: {self.simulated_account['total_balance']}") 