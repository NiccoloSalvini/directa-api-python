import datetime
import re
from typing import Dict, List, Union, Any, Iterator

from directa_api.connection import HistoricalConnection


class HistoricalData:
    """
    A wrapper for the Directa Historical Data API (port 10003)
    
    This class handles socket connections to the Directa Historical Data API
    for retrieving historical pricing data, tick data, and candle data.
    
    Note: Requires the Darwin trading platform to be running.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 10003, buffer_size: int = 8192):
        """
        Initialize the HistoricalData API wrapper
        
        Args:
            host: The hostname (default: 127.0.0.1)
            port: The port for historical data API (default: 10003)
            buffer_size: Socket buffer size for receiving responses
        """
        self.connection = HistoricalConnection(host, port, buffer_size)
        
        # Volume after-hours setting (default is CNT+AH)
        self.volume_afterhours_setting = "CNT+AH"
    
    def connect(self) -> bool:
        """
        Establish a connection to the Directa Historical Data API
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        return self.connection.connect()
    
    def disconnect(self) -> None:
        """Close the connection to the Directa Historical Data API"""
        self.connection.disconnect()
    
    def __enter__(self):
        """Support for context manager protocol"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for context manager protocol"""
        self.disconnect()
    
    def send_command(self, command: str) -> str:
        """
        Send a command to the Directa Historical Data API
        
        Args:
            command: The command string to send
        
        Returns:
            str: The complete response from the server
        
        Raises:
            ConnectionError: If not connected to the API
            socket.error: If an error occurs during sending/receiving
        """
        return self.connection.send_command(command)
    
    def set_volume_afterhours(self, setting: str = None) -> str:
        """
        Set or get the volume after-hours setting
        
        Args:
            setting: One of "CNT" (continuous), "AH" (after-hours), or "CNT+AH" (both)
                    If None, just return the current setting
        
        Returns:
            str: The response showing the current or new setting
        """
        if setting is not None:
            # Validate the setting
            if setting not in ["CNT", "AH", "CNT+AH"]:
                raise ValueError("Volume after-hours setting must be one of: CNT, AH, CNT+AH")
            
            response = self.send_command(f"VOLUMEAFTERHOURS {setting}")
        else:
            # Just get the current setting
            response = self.send_command("VOLUMEAFTERHOURS")
        
        # Update our stored setting based on the response
        match = re.search(r'VOLUME_AFTERHOURS\s+(CNT\+AH|CNT|AH)', response)
        if match:
            self.volume_afterhours_setting = match.group(1)
            
        return response
    
    def enable_ticker_marker(self, enable: bool = True) -> str:
        """
        Enable or disable including ticker in response
        
        Args:
            enable: Whether to enable or disable ticker markers
        
        Returns:
            str: The response from the server
        """
        value = "TRUE" if enable else "FALSE"
        return self.send_command(f"TICKERMARKER {value}")
    
    def get_tick_data(self, symbol: str, days: int) -> Dict[str, Any]:
        """
        Get historical tick-by-tick data for a given number of days
        
        Args:
            symbol: The ticker symbol
            days: Number of days to fetch (max 100 for intraday)
        
        Returns:
            Dict with parsed tick data
        """
        response = self.send_command(f"TBT {symbol} {days}")
        return self._parse_tbt_response(response)
    
    def get_tick_data_range(self, symbol: str, start_date: Union[str, datetime.datetime], 
                           end_date: Union[str, datetime.datetime]) -> Dict[str, Any]:
        """
        Get historical tick-by-tick data for a specific date range
        
        Args:
            symbol: The ticker symbol
            start_date: Start date (either a datetime object or a string in format 'yyyyMMddHHmmss')
            end_date: End date (either a datetime object or a string in format 'yyyyMMddHHmmss')
        
        Returns:
            Dict with parsed tick data
        """
        # Convert datetime objects to string format if needed
        if isinstance(start_date, datetime.datetime):
            start_date = start_date.strftime("%Y%m%d%H%M%S")
        
        if isinstance(end_date, datetime.datetime):
            end_date = end_date.strftime("%Y%m%d%H%M%S")
        
        response = self.send_command(f"TBTRANGE {symbol} {start_date} {end_date}")
        return self._parse_tbt_response(response)
    
    def get_candle_data(self, symbol: str, days: int, period_seconds: int) -> Dict[str, Any]:
        """
        Get historical candle data for a given number of days
        
        Args:
            symbol: The ticker symbol
            days: Number of days to fetch (max 100 for intraday, 15 years for daily)
            period_seconds: Candle period in seconds (60=1min, 300=5min, 3600=1hr, 86400=1day)
        
        Returns:
            Dict with parsed candle data
        """
        response = self.send_command(f"CANDLE {symbol} {days} {period_seconds}")
        return self._parse_candle_response(response)
    
    def get_candle_data_range(self, symbol: str, start_date: Union[str, datetime.datetime], 
                             end_date: Union[str, datetime.datetime], 
                             period_seconds: int) -> Dict[str, Any]:
        """
        Get historical candle data for a specific date range
        
        Args:
            symbol: The ticker symbol
            start_date: Start date (either a datetime object or a string in format 'yyyyMMddHHmmss')
            end_date: End date (either a datetime object or a string in format 'yyyyMMddHHmmss')
            period_seconds: Candle period in seconds (60=1min, 300=5min, 3600=1hr, 86400=1day)
        
        Returns:
            Dict with parsed candle data
        """
        # Convert datetime objects to string format if needed
        if isinstance(start_date, datetime.datetime):
            start_date = start_date.strftime("%Y%m%d%H%M%S")
        
        if isinstance(end_date, datetime.datetime):
            end_date = end_date.strftime("%Y%m%d%H%M%S")
        
        response = self.send_command(f"CANDLERANGE {symbol} {start_date} {end_date} {period_seconds}")
        return self._parse_candle_response(response)
    
    def _parse_tbt_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the response from a TBT or TBTRANGE command
        
        Args:
            response: The raw response string
        
        Returns:
            Dict with parsed data or error information
        """
        # Check for error responses
        if "Wrong number_of_days value" in response:
            return {"success": False, "error": "Wrong number of days value"}
        elif "Not enough parameters" in response:
            return {"success": False, "error": "Not enough parameters provided"}
        elif "ERR;" in response:
            return {"success": False, "error": response.strip()}
        
        # Extract ticker from the first data line
        ticker = None
        tick_data = []
        
        for line in response.strip().split('\n'):
            line = line.strip()
            
            # Skip non-data lines
            if not line or line.startswith("no delta") or line == "END TBT":
                continue
            
            # Parse TBT data lines
            if line.startswith("TBT;"):
                parts = line.split(';')
                if len(parts) >= 6:
                    ticker = parts[1] if ticker is None else ticker
                    
                    # Extract date, time, price, and quantity
                    date_str = parts[2]
                    time_str = parts[3]
                    price = float(parts[4])
                    quantity = int(parts[5])
                    
                    # Convert date and time strings to datetime
                    date_time = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H:%M:%S")
                    
                    tick_data.append({
                        "timestamp": date_time,
                        "price": price,
                        "quantity": quantity
                    })
        
        # Prepare the result dictionary
        result = {
            "success": True,
            "symbol": ticker,
            "data_type": "tick",
            "count": len(tick_data),
            "data": tick_data
        }
        
        # Add time range info if we have data
        if tick_data:
            result["from_date"] = tick_data[0]["timestamp"]
            result["to_date"] = tick_data[-1]["timestamp"]
        
        return result
    
    def _parse_candle_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the response from a CANDLE or CANDLERANGE command
        
        Args:
            response: The raw response string
        
        Returns:
            Dict with parsed data or error information
        """
        # Check for error responses
        if "Wrong number_of_days value" in response:
            return {"success": False, "error": "Wrong number of days value"}
        elif "Wrong candle value" in response:
            return {"success": False, "error": "Wrong candle period value"}
        elif "Not enough parameters" in response:
            return {"success": False, "error": "Not enough parameters provided"}
        elif "ERR;" in response:
            return {"success": False, "error": response.strip()}
        
        # Extract ticker from the response
        ticker_match = re.search(r'BEGIN CANDLES\s+(\w+)', response)
        ticker = ticker_match.group(1) if ticker_match else None
        
        candle_data = []
        
        for line in response.strip().split('\n'):
            line = line.strip()
            
            # Skip non-data lines
            if not line or line.startswith("BEGIN CANDLES") or line.startswith("END CANDLES"):
                continue
            
            # Parse CANDLE data lines
            if line.startswith("CANDLE;"):
                parts = line.split(';')
                if len(parts) >= 9:
                    # If ticker wasn't found from BEGIN line, extract it from the first candle
                    ticker = parts[1] if ticker is None else ticker
                    
                    # Extract date, time, close, low, high, open, and volume
                    date_str = parts[2]
                    time_str = parts[3]
                    close = float(parts[4])
                    low = float(parts[5])
                    high = float(parts[6])
                    open_price = float(parts[7])
                    volume = int(parts[8])
                    
                    # Convert date and time strings to datetime
                    date_time = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H:%M:%S")
                    
                    candle_data.append({
                        "timestamp": date_time,
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume
                    })
        
        # Prepare the result dictionary
        result = {
            "success": True,
            "symbol": ticker,
            "data_type": "candle",
            "count": len(candle_data),
            "volume_setting": self.volume_afterhours_setting,
            "data": candle_data
        }
        
        # Add time range info if we have data
        if candle_data:
            result["from_date"] = candle_data[0]["timestamp"]
            result["to_date"] = candle_data[-1]["timestamp"]
        
        return result
    
    def get_daily_candles(self, symbol: str, days: int = 252) -> Dict[str, Any]:
        """
        Get daily candle data (convenience method for EOD data)
        
        Args:
            symbol: The ticker symbol
            days: Number of trading days (default: 252, approximately 1 year)
        
        Returns:
            Dict with parsed daily candle data
        """
        return self.get_candle_data(symbol, days, 86400)
    
    def get_intraday_candles(self, symbol: str, days: int = 1, 
                            period_minutes: int = 1) -> Dict[str, Any]:
        """
        Get intraday candle data (convenience method)
        
        Args:
            symbol: The ticker symbol
            days: Number of days back (default: 1)
            period_minutes: Candle period in minutes (default: 1)
        
        Returns:
            Dict with parsed intraday candle data
        """
        # Convert minutes to seconds
        period_seconds = period_minutes * 60
        return self.get_candle_data(symbol, days, period_seconds)
    
    def get_intraday_ticks(self, symbol: str, days: int = 1) -> Dict[str, Any]:
        """
        Get intraday tick data (convenience method)
        
        Args:
            symbol: The ticker symbol
            days: Number of days back (default: 1)
        
        Returns:
            Dict with parsed tick data
        """
        return self.get_tick_data(symbol, days)
    
    def get_candles_iterator(self, symbol: str, period_seconds: int, 
                            max_days: int = 100) -> Iterator[Dict[str, Any]]:
        """
        Get a candle data iterator that fetches data in chunks to avoid timeouts
        
        Args:
            symbol: The ticker symbol
            period_seconds: Candle period in seconds
            max_days: Maximum number of days to fetch in each chunk
        
        Returns:
            Iterator yielding candle data dictionaries
        """
        # Determine if EOD or intraday based on period
        is_eod = period_seconds >= 86400
        
        # Set up the chunking parameters
        if is_eod:
            # For EOD data, fetch in chunks of max 5 years (about 1250 trading days)
            chunk_size = min(1250, max_days)
            total_days = 3650  # About 15 years (the max supported)
        else:
            # For intraday, fetch in chunks of the provided max_days
            chunk_size = min(max_days, 100)  # Max 100 days for intraday
            total_days = 100   # Intraday max is 100 days
        
        # Fetch data in chunks
        days_fetched = 0
        while days_fetched < total_days:
            days_to_fetch = min(chunk_size, total_days - days_fetched)
            
            # Calculate date range for this chunk
            end_date = datetime.datetime.now() - datetime.timedelta(days=days_fetched)
            start_date = end_date - datetime.timedelta(days=days_to_fetch)
            
            # Format dates for the API
            start_date_str = start_date.strftime("%Y%m%d%H%M%S")
            end_date_str = end_date.strftime("%Y%m%d%H%M%S")
            
            # Fetch the data
            result = self.get_candle_data_range(symbol, start_date_str, end_date_str, period_seconds)
            
            # If we got an error or empty data, stop iteration
            if not result.get("success", False) or len(result.get("data", [])) == 0:
                break
                
            # Yield the result
            yield result
            
            # Update days fetched
            days_fetched += days_to_fetch
            
            # If we got fewer candles than expected, we're at the end of data
            if len(result.get("data", [])) < days_to_fetch and is_eod:
                break 