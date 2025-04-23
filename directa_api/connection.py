import socket
import logging
import time
import re
import datetime
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class DirectaConnection:
    """
    Base connection handler for Directa API services
    
    This class manages the socket connection to the Directa API services,
    handling connection initialization, command sending and receiving responses.
    
    It's used as a base class for specialized services like trading and historical data.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 10002, 
                 buffer_size: int = 4096, service_name: str = "DirectaAPI"):
        """
        Initialize the DirectaConnection
        
        Args:
            host: The hostname (default: 127.0.0.1)
            port: The port to connect to
            buffer_size: Socket buffer size for receiving responses
            service_name: Name of the service for logging
        """
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.socket = None
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.connected = False
        self.last_status = None
        self.connection_status = "UNKNOWN"
        
        # Connection tracking
        self.connection_attempts = 0
        self.last_connection_time = None
        self.last_status_check = None
        self.connection_state_changes = []
    
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
            self.connected = is_connected
            self.logger.info(f"Connection status changed: {self.connection_status}")
    
    def connect(self, initial_timeout: float = 5.0, normal_timeout: float = 2.0) -> bool:
        """
        Establish a connection to the Directa API
        
        Args:
            initial_timeout: Timeout for initial connection
            normal_timeout: Standard timeout after connection
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connection_attempts += 1
            self.last_connection_time = datetime.datetime.now()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.logger.info(f"Connected to {self.service_name} on {self.host}:{self.port}")
            
            # Use a longer timeout for initial connection
            self.socket.settimeout(initial_timeout)
            
            # Read initial data
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
                    self._check_status_response(initial_text)
            except Exception as e:
                self.logger.warning(f"Error processing initial data: {str(e)}")
            finally:
                # Restore normal timeout
                self.socket.settimeout(normal_timeout)
            
            return True
        except socket.error as e:
            self.logger.error(f"Error connecting to {self.service_name}: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Close the connection to the Directa API"""
        if self.socket and self.connected:
            self.socket.close()
            self.logger.info(f"Disconnected from {self.service_name}")
        
        self.connected = False
        self.socket = None
    
    def __enter__(self):
        """Support for context manager protocol"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for context manager protocol"""
        self.disconnect()
    
    def _check_status_response(self, response_text: str) -> None:
        """
        Check for Darwin status in response and update connection state
        
        Args:
            response_text: The response text from Darwin
        """
        if "DARWIN_STATUS" in response_text:
            match = re.search(r'DARWIN_STATUS;([^;]+);([^;]+);', response_text)
            if match:
                status = match.group(1)
                app_status = match.group(2)
                self.last_status = response_text
                
                # Update connection status
                is_connected = status == "CONN_OK"
                self.set_connection_status(status, is_connected)
                self.logger.debug(f"Darwin status: connection={status}, application={app_status}")
    
    def send_command(self, command: str, timeout: float = None) -> str:
        """
        Send a command to the Directa API
        
        Args:
            command: The command string to send
            timeout: Optional override for socket timeout
        
        Returns:
            str: The response from the server
        
        Raises:
            ConnectionError: If not connected to the API
            socket.error: If an error occurs during sending/receiving
        """
        if not self.connected or not self.socket:
            raise ConnectionError(f"Not connected to {self.service_name}")
        
        # Ensure command ends with newline
        if not command.endswith('\n'):
            command += '\n'
        
        try:
            self.logger.debug(f"Sending command: {command.strip()}")
            self.socket.sendall(command.encode('utf-8'))
            
            # Set custom timeout if provided
            if timeout is not None:
                self.socket.settimeout(timeout)
                
            response = b""
            
            # Read response with a timeout loop
            start_time = time.time()
            max_time = 10.0  # Maximum 10 seconds for standard commands
            
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
                    
                    # If we see a complete response, stop waiting
                    if b'\n' in chunk:
                        break
                        
                except socket.timeout:
                    # No data received within timeout
                    if response:  # If we already have data, we can stop
                        break
            
            # If we didn't get any response, raise an error
            if not response:
                raise ConnectionError("No response received from server")
                
            response_text = response.decode('utf-8')
            self.logger.debug(f"Received response: {response_text.strip()}")
            
            # Check for darwin status in the response
            self._check_status_response(response_text)
            
            return response_text
        except socket.error as e:
            self.logger.error(f"Socket error: {str(e)}")
            raise
    
    def get_connection_metrics(self) -> Dict[str, Any]:
        """
        Generate a summary of connection metrics and status history
        
        Returns:
            Dictionary with connection metrics and history
        """
        # Create a summary of recent connection history
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
            "currently_connected": self.connected,
            "connection_status": self.connection_status,
            "connection_attempts": self.connection_attempts,
            "last_connection_time": self.last_connection_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_connection_time else None,
            "last_status_check": self.last_status_check.strftime("%Y-%m-%d %H:%M:%S") if self.last_status_check else None,
            "uptime_percentage": uptime_percentage,
            "connection_history": history_summary
        }


class TradingConnection(DirectaConnection):
    """Connection handler for Directa Trading API (port 10002)"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 10002, buffer_size: int = 4096):
        super().__init__(host, port, buffer_size, "DirectaTrading")
        
        # Trading-specific attributes
        self.is_trading_connected = False
    
    def set_connection_status(self, status: str, is_connected: bool) -> None:
        """Override to also update trading connection status"""
        super().set_connection_status(status, is_connected)
        self.is_trading_connected = is_connected
    
    def send_command(self, command: str, timeout: float = None) -> str:
        """
        Send a command to the Trading API with specialized handling
        
        Args:
            command: The command string to send
            timeout: Optional override for socket timeout
        
        Returns:
            str: The response from the server
        """
        if not self.connected or not self.socket:
            raise ConnectionError("Not connected to Directa Trading API")
        
        # Ensure command ends with newline
        if not command.endswith('\n'):
            command += '\n'
        
        try:
            self.logger.debug(f"Sending command: {command.strip()}")
            self.socket.sendall(command.encode('utf-8'))
            
            # Use different timeouts for different commands
            if command.strip() == "DARWINSTATUS":
                # Use longer timeout for status checks
                self.socket.settimeout(3.0)
            else:
                # Use standard timeout for other commands
                self.socket.settimeout(2.0 if timeout is None else timeout)
                
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
                    
                    # Special handling for DARWINSTATUS
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
            self._check_status_response(response_text)
            
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
                
                # Special cases for specific commands
                if cmd_name == "DARWINSTATUS":
                    for line in lines:
                        if "DARWIN_STATUS" in line:
                            return line
                
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


class HistoricalConnection(DirectaConnection):
    """Connection handler for Directa Historical Data API (port 10003)"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 10003, buffer_size: int = 8192):
        super().__init__(host, port, buffer_size, "DirectaHistoricalData")
    
    def connect(self) -> bool:
        """
        Connect to the Historical Data API with appropriate timeouts
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        return super().connect(initial_timeout=5.0, normal_timeout=30.0)
    
    def send_command(self, command: str, timeout: float = 60.0) -> str:
        """
        Send a command to the Historical Data API with longer timeouts
        
        Args:
            command: The command string to send
            timeout: Timeout for response (default: 60s for historical data)
        
        Returns:
            str: The complete response from the server
        """
        if not self.connected or not self.socket:
            raise ConnectionError("Not connected to Directa Historical Data API")
        
        # Ensure command ends with newline
        if not command.endswith('\n'):
            command += '\n'
        
        try:
            self.logger.debug(f"Sending command: {command.strip()}")
            self.socket.sendall(command.encode('utf-8'))
            
            # Historical data can take longer to fetch
            self.socket.settimeout(timeout)
                
            response = b""
            complete = False
            
            # Read until we get a complete response
            # For historical data, we need to detect special end markers
            while not complete:
                chunk = self.socket.recv(self.buffer_size)
                if not chunk:
                    break
                
                response += chunk
                
                # Check for completion markers in the response
                response_text = response.decode('utf-8', errors='ignore')
                if "END TBT" in response_text or "END CANDLES" in response_text:
                    complete = True
                    break
                
                # Also check for error responses
                if "Wrong number_of_days value" in response_text or \
                   "Wrong candle value" in response_text or \
                   "Not enough parameters" in response_text or \
                   "ERR;" in response_text:
                    complete = True
                    break
            
            response_text = response.decode('utf-8')
            self.logger.debug(f"Received response of {len(response_text)} chars")
            
            # Check for status info in the response
            self._check_status_response(response_text)
            
            return response_text
        except socket.error as e:
            self.logger.error(f"Socket error: {str(e)}")
            raise 