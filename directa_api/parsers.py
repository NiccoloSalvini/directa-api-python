"""
Parsers for Directa Trading API responses.

This module provides functions to parse responses from the Directa Trading API.
Each parser function handles a specific type of response and converts it into
a structured dictionary format for easier processing.

The parsers follow a consistent pattern:
- Each response is converted into a dictionary with status, error, and data keys
- Error responses are handled consistently across all functions
- Type conversion is performed where appropriate (e.g., strings to numbers)
- Complex responses are broken down into structured objects

The parsers can be configured to handle various response formats:
- Enhanced parsers like parse_darwin_status_response can accept additional context
  parameters like trading_instance to provide more detailed analysis
- All parsers follow a standard return format for consistency

Example:
    response = api.get_portfolio(parse=True)
    # Returns: {"status": "success", "error": None, "data": {...}}
"""
from typing import Dict, List, Optional, Union, Any
from directa_api.errors import is_error_response, parse_error_response
import re


def parse_portfolio_response(response: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse the portfolio response from the API (INFOSTOCKS command)
    
    Args:
        response: Raw API response string
        
    Returns:
        List of portfolio positions or error dict
    """
    # Check if it's an error response
    if is_error_response(response):
        return parse_error_response(response)
        
    lines = response.strip().split('\n')
    positions = []
    
    # Check for FLOWPOINT markers (if enabled on the API)
    start_idx = 0
    end_idx = len(lines)
    
    for i, line in enumerate(lines):
        if line.startswith("BEGIN STOCKLIST"):
            start_idx = i + 1
        elif line.startswith("END STOCKLIST"):
            end_idx = i
    
    # Process each STOCK line
    for line in lines[start_idx:end_idx]:
        if not line.strip() or not line.startswith("STOCK;"):
            continue
            
        parts = line.split(';')
        if len(parts) < 6:  # Basic validation
            continue
            
        # Format is: STOCK;<TICKER>;<ORA>;<QUANTITA IN PORTAFOGLIO>;<QUANTITA DIRECTA>;<QUANTITA IN NEGOZIAZIONE>;<PREZZO MEDIO>;<GAIN TEORICO>
        try:
            position = {
                "stock_type": parts[0],
                "symbol": parts[1],
                "time": parts[2],
                "quantity_portfolio": parts[3],
                "quantity_directa": parts[4],
                "quantity_trading": parts[5]
            }
            
            # Some positions might have more fields
            if len(parts) > 6:
                position["avg_price"] = parts[6]
            if len(parts) > 7:
                position["theoretical_gain"] = parts[7]
                
            positions.append(position)
        except Exception:
            # Skip malformed lines
            continue
    
    return {"success": True, "data": positions}


def parse_order_response(response: str) -> Dict[str, Any]:
    """
    Parse the order placement response from the API
    
    Args:
        response: Raw API response string
        
    Returns:
        Dictionary with order details
    """
    # Check if it's an error response
    if is_error_response(response):
        return parse_error_response(response)
    
    lines = response.strip().split('\n')
    result = {"success": True, "data": {}}
    
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split(';')
        
        # Handle TRADOK responses
        if line.startswith("TRADOK;"):
            if len(parts) >= 8:
                order_data = {
                    "response_type": parts[0],
                    "symbol": parts[1],
                    "order_id": parts[2],
                    "status_code": parts[3],
                    "operation": parts[4],
                    "quantity": parts[5],
                    "price": parts[6]
                }
                
                # Check for extended fields with PRICEEXE enabled
                if len(parts) > 8:
                    order_data["exec_price"] = parts[7]
                    order_data["exec_quantity"] = parts[8]
                    order_data["remaining_quantity"] = parts[9]
                    order_data["directa_ref_id"] = parts[10]
                
                # Check for command log with LOGCMD enabled
                if len(parts) > 11:
                    order_data["command"] = parts[11]
                
                result["data"] = order_data
                break
        
        # Handle TRADERR responses
        elif line.startswith("TRADERR;"):
            if len(parts) >= 7:
                result["success"] = False
                result["data"] = {
                    "response_type": parts[0],
                    "symbol": parts[1],
                    "order_id": parts[2],
                    "error_code": parts[3],
                    "operation": parts[4],
                    "quantity": parts[5],
                    "error_message": parts[6]
                }
                
                # Check for command log with LOGCMD enabled
                if len(parts) > 7:
                    result["data"]["command"] = parts[7]
                
                break
        
        # Handle TRADCONFIRM responses
        elif line.startswith("TRADCONFIRM;"):
            if len(parts) >= 8:
                result["success"] = True
                result["confirmation_required"] = True
                result["data"] = {
                    "response_type": parts[0],
                    "symbol": parts[1],
                    "order_id": parts[2],
                    "status_code": parts[3],
                    "operation": parts[4],
                    "quantity": parts[5],
                    "price": parts[6],
                    "message": parts[7]
                }
                break
    
    return result


def parse_orders_response(response: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse the active orders response from the API (ORDERLIST command)
    
    Args:
        response: Raw API response string
        
    Returns:
        List of orders or error dict
    """
    # Check if it's an error response
    if is_error_response(response):
        # Special case for empty order list
        if "1019" in response:
            return {"success": True, "data": []}
        return parse_error_response(response)
    
    lines = response.strip().split('\n')
    orders = []
    
    # Check for FLOWPOINT markers (if enabled on the API)
    start_idx = 0
    end_idx = len(lines)
    
    for i, line in enumerate(lines):
        if line.startswith("BEGIN ORDERLIST"):
            start_idx = i + 1
        elif line.startswith("END ORDERLIST"):
            end_idx = i
    
    # Process each ORDER line
    for line in lines[start_idx:end_idx]:
        if not line.strip() or not line.startswith("ORDER;"):
            continue
            
        parts = line.split(';')
        if len(parts) < 8:  # Basic validation
            continue
        
        # Format is: ORDER;<TICKER>;<ORA>;<ID ORDINE>;<TIPO OPERAZIONE>;<PREZZO LIMITE>;<PREZZO SEGNALE>;<QUANTITA'>;<STATO ORDINE>
        try:
            order = {
                "order_type": parts[0],
                "symbol": parts[1],
                "time": parts[2],
                "order_id": parts[3],
                "operation": parts[4],
                "limit_price": parts[5],
                "signal_price": parts[6],
                "quantity": parts[7],
                "status_code": parts[8]
            }
            
            # If PRICEEXE is enabled, there will be more fields
            if len(parts) > 9:
                order["avg_price"] = parts[9]
                order["exec_price"] = parts[10]
                order["market_quantity"] = parts[11]
                
                if len(parts) > 12:
                    order["directa_ref_id"] = parts[12]
            
            orders.append(order)
        except Exception:
            # Skip malformed lines
            continue
    
    return {"success": True, "data": orders}


def parse_account_info_response(response: str) -> Dict[str, Any]:
    """
    Parse the account information response from the API (INFOACCOUNT command)
    
    Args:
        response: Raw API response string
        
    Returns:
        Dictionary with account details
    """
    # Check if it's an error response
    if is_error_response(response):
        return parse_error_response(response)
    
    # The response is: INFOACCOUNT;<ORA>;<CODICE CONTO>;<LIQUIDITA'>;<GAIN EURO>;<OPEN PROFIT/LOSS>;<EQUITY>
    parts = response.strip().split(';')
    if len(parts) >= 7 and parts[0] == "INFOACCOUNT":
        return {
            "success": True,
            "data": {
                "response_type": parts[0],
                "time": parts[1],
                "account_code": parts[2],
                "liquidity": try_convert_to_number(parts[3]),
                "gain_euro": try_convert_to_number(parts[4]),
                "open_profit_loss": try_convert_to_number(parts[5]),
                "equity": try_convert_to_number(parts[6]),
                # There might be additional fields
                "additional_info": parts[7] if len(parts) > 7 else None
            }
        }
    
    # Handle AVAILABILITY responses
    if len(parts) >= 6 and parts[0] == "AVAILABILITY":
        return {
            "success": True,
            "data": {
                "response_type": parts[0],
                "time": parts[1],
                "stock_availability": try_convert_to_number(parts[2]),
                "stock_availability_margin": try_convert_to_number(parts[3]),
                "derivatives_availability": try_convert_to_number(parts[4]),
                "derivatives_availability_margin": try_convert_to_number(parts[5]),
                "total_liquidity": try_convert_to_number(parts[6]) if len(parts) > 6 else None
            }
        }
    
    # If we can't parse the response, return a generic structure
    return {
        "success": False,
        "error_message": "Formato di risposta sconosciuto",
        "raw_response": response
    }


def parse_darwin_status_response(response: str, trading_instance=None) -> Dict[str, Any]:
    """
    Parse the response from a Darwin status request.
    
    Args:
        response: The response string from the server
        trading_instance: Optional DirectaTrading instance to provide connection context
        
    Returns:
        A dictionary with the parsed response
    """
    parts = response.split(';')
    
    # Initialize with backward compatible format
    result = {
        "success": True,
        "error": None,
        "status": "success",
        "data": {
            "response_type": "DARWIN_STATUS"
        }
    }
    
    # Check if the response is in the expected format
    if parts[0] != "DARWIN_STATUS":
        result["success"] = False
        result["status"] = "error"
        result["error"] = "Invalid response format"
        result["data"] = None
        return result
    
    # Check connection status codes    
    connection_status = parts[1] if len(parts) > 1 else "UNKNOWN"
    application_status = parts[2] if len(parts) > 2 else "UNKNOWN"
    
    # Enhanced status mapping with descriptive messages
    status_mapping = {
        "CONN_OK": "Connected and operational",
        "CONN_UNAVAILABLE": "Connection unavailable",
        "CONN_ERROR": "Connection error",
        "UNKNOWN": "Unknown connection status"
    }
    
    # Enhanced application status description
    app_status_desc = "Running" if application_status.upper() == "TRUE" else "Not running"
    
    # Format connection description for backward compatibility
    connection_description = ""
    if connection_status == "CONN_OK":
        connection_description = "Connessione ai server di trading attiva"
    elif connection_status == "CONN_UNAVAILABLE":
        connection_description = "Connessione ai server di trading non stabilita o interrotta"
    elif connection_status == "CONN_ERROR":
        connection_description = "Errore nella connessione ai server di trading"
    
    # Status verification
    is_connected = connection_status == "CONN_OK"
    is_valid_connection = is_connected
    
    # For backward compatibility, always keep success=True unless format error
    result["success"] = True
    
    # But set the new status field appropriately
    if is_connected:
        result["status"] = "success"
    else:
        result["status"] = "error"
        result["error"] = status_mapping.get(connection_status, f"Connection error: {connection_status}")
    
    # Additional context if trading instance is provided
    if trading_instance is not None and hasattr(trading_instance, 'is_trading_connected'):
        # Cross-check API response with socket connection state
        api_says_connected = connection_status == "CONN_OK"
        socket_is_connected = trading_instance.is_trading_connected
        
        # Handle inconsistency
        if api_says_connected != socket_is_connected:
            # Log the discrepancy but trust the API response
            if hasattr(trading_instance, 'logger'):
                trading_instance.logger.warning(
                    f"Connection state mismatch: API reports '{connection_status}' but socket reports "
                    f"{'connected' if socket_is_connected else 'disconnected'}"
                )
    
    # Always provide meaningful data even for error states
    # Format the response data
    result["data"] = {
        "response_type": "DARWIN_STATUS",
        "connection_status": connection_status,
        "application_status": application_status,
        "status_message": status_mapping.get(connection_status, connection_status),
        "connection_description": connection_description,
        "is_connected": is_connected,
        "is_running": application_status.upper() == "TRUE",
        "datafeed_enabled": is_connected and application_status.upper() == "TRUE",
        "raw_details": parts[3:] if len(parts) > 3 else []
    }
    
    # Try to parse additional information if available
    if len(parts) > 3:
        try:
            # Check if the 4th part looks like a release string
            release_info = parts[3]
            if "Release" in release_info or "build" in release_info:
                result["data"]["release"] = release_info
            
            # Check if there are additional key=value pairs
            additional_info = {}
            for i in range(3, len(parts)):
                if "=" in parts[i]:
                    key, value = parts[i].split("=", 1)
                    additional_info[key.strip()] = value.strip()
            
            if additional_info:
                result["data"]["details"] = additional_info
        except Exception:
            # If parsing fails, keep the raw data only
            pass
    
    return result


def try_convert_to_number(value: str) -> Union[int, float, str]:
    """
    Try to convert a string to an appropriate numeric type
    
    Args:
        value: The string to convert
        
    Returns:
        The converted value or the original string if conversion fails
    """
    if not value or not isinstance(value, str):
        return value
        
    # Try to convert to numeric if appropriate
    value_str = value.strip()
    if value_str.replace('.', '', 1).replace('-', '', 1).isdigit():
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass
    
    return value 