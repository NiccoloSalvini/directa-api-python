#!/usr/bin/env python3
"""
Directa API - Trading Module

Questo modulo fornisce l'interfaccia per le operazioni di trading
attraverso l'API di Directa Trading.
"""

import logging
import time
import re
import datetime
import random
from typing import Optional, Dict, List, Union, Tuple, Any

from directa_api.connection import TradingConnection
from directa_api.simulation import TradingSimulation
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
    Interfaccia per l'API di trading Directa (porta 10002)
    
    Questa classe gestisce le operazioni di trading attraverso l'API di Directa,
    inclusa la gestione degli ordini, del portafoglio e delle informazioni dell'account.
    
    Nota: Richiede la piattaforma Darwin in esecuzione.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 10002, buffer_size: int = 4096, 
                 simulation_mode: bool = False, max_retries: int = 0, retry_delay: int = 1):
        """
        Inizializza l'interfaccia DirectaTrading
        
        Args:
            host: Hostname (default: 127.0.0.1)
            port: Porta per l'API di trading (default: 10002)
            buffer_size: Dimensione del buffer socket
            simulation_mode: Se True, simula le operazioni senza denaro reale
            max_retries: Numero massimo di tentativi di connessione
            retry_delay: Ritardo tra i tentativi di connessione in secondi
        """
        self.logger = logging.getLogger("DirectaTrading")
        self.simulation_mode = simulation_mode
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Crea la connessione all'API
        self.connection = TradingConnection(host, port, buffer_size)
        
        # Inizializza il simulatore se richiesto
        self.simulation = TradingSimulation() if simulation_mode else None
        
        if simulation_mode:
            self.logger.warning("MODALITÀ SIMULAZIONE ATTIVA - Nessuna operazione reale sarà eseguita")
            
        # Inizializzazione attributi per il monitoraggio delle connessioni
        self.connection_status = "DISCONNECTED"
        self.is_trading_connected = False
        self.connection_state_changes = []
        self.connection_history = []
        self.connection_attempts = 0
        self.last_connection_time = None
        self.last_status_check = None
        self.last_darwin_status = None
    
    def connect(self, max_retries: Optional[int] = None, retry_delay: Optional[int] = None) -> bool:
        """
        Stabilisce una connessione all'API di Directa Trading
        
        Args:
            max_retries: Numero massimo di tentativi di connessione (sovrascrive il valore di inizializzazione)
            retry_delay: Ritardo tra i tentativi in secondi (sovrascrive il valore di inizializzazione)
            
        Returns:
            bool: True se la connessione è riuscita, False altrimenti
        """
        # In simulazione, non serve connettersi
        if self.simulation_mode:
            self.logger.info("Simulazione: connessione sempre attiva")
            return True
        
        # Imposta i valori di retry se specificati
        max_retries = max_retries if max_retries is not None else self.max_retries
        retry_delay = retry_delay if retry_delay is not None else self.retry_delay
        
        # Tentativi di connessione
        for attempt in range(max_retries + 1):
            if attempt > 0:
                self.logger.info(f"Tentativo di connessione {attempt}/{max_retries}...")
                time.sleep(retry_delay)
            
            if self.connection.connect():
                self.logger.info("Connessione all'API di trading stabilita")
                return True
        
        self.logger.error(f"Connessione fallita dopo {max_retries + 1} tentativi")
        return False
    
    def disconnect(self) -> None:
        """Chiude la connessione all'API di trading"""
        if not self.simulation_mode and self.connection:
            self.connection.disconnect()
            self.logger.info("Disconnessione dall'API di trading completata")
    
    def __enter__(self):
        """Supporto per il protocollo context manager"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Supporto per il protocollo context manager"""
        self.disconnect()
    
    def send_command(self, command: str) -> str:
        """
        Invia un comando all'API di trading
        
        Args:
            command: Comando da inviare
            
        Returns:
            str: Risposta dall'API
            
        Raises:
            ConnectionError: Se non connesso all'API
        """
        if self.simulation_mode:
            self.logger.debug(f"Simulazione comando: {command}")
            # In simulazione, restituisci una risposta fittizia
            return f"SIMULATED;{command};OK"
        
        return self.connection.send_command(command)
    
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
    
    def get_portfolio(self, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Get the current portfolio information (stocks in portfolio and in trading)
        
        Args:
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with portfolio data or raw response string
        """
        if self.simulation_mode:
            return self.simulation.get_portfolio()
        
        command = "GETPORTFOLIO"
        response = self.send_command(command)
        
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
            return self.simulation.get_account_info()
        
        command = "GETACCTINFO"
        response = self.send_command(command)
        
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
            return self.simulation.get_darwin_status()
        
        try:
            command = "DARWINSTATUS"
            response = self.send_command(command)
            
            if parse:
                status_resp = parse_darwin_status_response(response)
                
                # Aggiungi metriche di connessione
                metrics = self.get_connection_metrics()
                status_resp["data"]["connection_metrics"] = metrics
                
                return status_resp
            
            return response
        except Exception as e:
            if retry:
                self.logger.warning(f"Errore durante il controllo dello stato ({str(e)}). Tentativo di recupero...")
                time.sleep(1)
                try:
                    # Tenta di riconnettersi
                    self.connect(max_retries=1)
                    return self.get_darwin_status(parse, False)  # Chiama di nuovo senza retry
                except Exception as retry_error:
                    self.logger.error(f"Fallito il recupero dello stato: {str(retry_error)}")
            
            # Restituisci un oggetto di errore formattato
            error_msg = str(e)
            if parse:
                return {
                    "success": False,
                    "error": f"Errore durante il controllo dello stato: {error_msg}",
                    "data": {
                        "connection_status": "CONN_ERROR",
                        "connection_metrics": self.get_connection_metrics()
                    }
                }
            
            return f"DARWIN_STATUS;CONN_ERROR;ERROR;{error_msg}"
    
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
        if self.simulation_mode:
            return self.simulation.create_order(symbol, side, quantity, price, order_type)
        
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
        
        response = self.send_command(command)
        
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
            # Use the simulation instance to cancel the order
            return self.simulation.cancel_order(order_id)
            
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
            # Delegate to simulation instance
            return self.simulation.get_orders()
            
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
        Delegates to the simulation instance.
        
        Args:
            symbol: The symbol of the position
            quantity: The quantity to add (can be negative for selling)
            price: The price of the new position
        """
        if not self.simulation_mode:
            self.logger.warning("add_simulated_position called but simulation mode is not active")
            return
        
        # Delegate to simulation instance
        self.simulation.add_position(symbol, quantity, price)
    
    def remove_simulated_position(self, symbol: str) -> bool:
        """
        Remove a position from the simulated portfolio (simulation mode only)
        Delegates to the simulation instance.
        
        Args:
            symbol: Symbol/ticker to remove
            
        Returns:
            True if position was found and removed, False otherwise
        """
        if not self.simulation_mode:
            self.logger.warning("remove_simulated_position called but simulation mode is not active")
            return False
            
        # Delegate to simulation instance
        return self.simulation.remove_position(symbol)
    
    def update_simulated_account(self, liquidity: float = None, equity: float = None) -> None:
        """
        Update the simulated account (simulation mode only)
        Delegates to the simulation instance.
        
        Args:
            liquidity: New liquidity value (if None, kept unchanged)
            equity: New equity value (if None, kept unchanged)
        """
        if not self.simulation_mode:
            self.logger.warning("update_simulated_account called but simulation mode is not active")
            return
            
        # Delegate to simulation instance
        self.simulation.update_account(liquidity, equity)
    
    def fix_test(self):
        """
        Reset simulated account and portfolio for testing.
        Delegates to the simulation instance.
        """
        if not self.simulation_mode:
            logging.warning("fix_test called but simulation mode is not active")
            return

        # Delegate to simulation instance
        return self.simulation.reset_state()

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
            
        # Just delegate to the simulation instance's execute_order method
        if isinstance(order_req, str):
            # Simple case: just an order ID
            return self.simulation.execute_order(order_req, fill_price)
        else:
            # Complex case: order details dictionary
            # Extract key details and call execute_order
            order_id = order_req.get("order_id")
            if not order_id:
                return {"success": False, "error": "Order ID missing from order details"}
                
            return self.simulation.execute_order(order_id, fill_price)
    
    def update_simulated_total_balance(self):
        """
        Update the total balance of the simulated account based on cash liquidity and portfolio value.
        Delegates to the simulation instance.
        """
        if not self.simulation_mode:
            self.logger.warning("update_simulated_total_balance called but simulation mode is not active")
            return
            
        # Delegate to simulation instance
        self.simulation.update_total_balance()

    # Additional trading functions for Directa API
    
    def buy_limit(self, symbol: str, quantity: int, price: float, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a limit buy order
        
        Args:
            symbol: The stock symbol/ticker
            quantity: Number of shares
            price: Limit price
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_order(symbol, "BUY", quantity, price, "LIMIT", parse)
        
    def sell_limit(self, symbol: str, quantity: int, price: float, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a limit sell order
        
        Args:
            symbol: The stock symbol/ticker
            quantity: Number of shares
            price: Limit price
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_order(symbol, "SELL", quantity, price, "LIMIT", parse)
    
    def buy_market(self, symbol: str, quantity: int, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a market buy order
        
        Args:
            symbol: The stock symbol/ticker
            quantity: Number of shares
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_order(symbol, "BUY", quantity, None, "MARKET", parse)
    
    def sell_market(self, symbol: str, quantity: int, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a market sell order
        
        Args:
            symbol: The stock symbol/ticker
            quantity: Number of shares
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_order(symbol, "SELL", quantity, None, "MARKET", parse)
    
    def place_stop_order(self, symbol: str, side: str, quantity: int, 
                         limit_price: float, stop_price: float, 
                         parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a stop order
        
        Args:
            symbol: The stock symbol/ticker
            side: "BUY" or "SELL"
            quantity: Number of shares
            limit_price: Limit price
            stop_price: Stop/trigger price
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        side = side.upper()
        
        # Map side to Directa API commands
        if side == "BUY":
            cmd_prefix = "ACQSTOP"
        elif side == "SELL":
            cmd_prefix = "VENSTOP"
        else:
            raise ValueError("Side must be either 'BUY' or 'SELL'")
        
        # Generate a unique order ID
        order_id = f"ORD{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Format: ACQSTOP/VENSTOP ID_ORDINE,TICKER,QUANTITA',PREZZO_LIMITE,PREZZO_STOP
        command = f"{cmd_prefix} {order_id},{symbol},{quantity},{limit_price},{stop_price}"
        
        if self.simulation_mode:
            # In simulation mode, create simulated order response
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Create the simulated order
            new_order = {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": limit_price,
                "stop_price": stop_price,
                "order_type": "STOP",
                "status": "PENDING",
                "time": current_time
            }
            
            # Add to simulated orders dictionary
            self.simulated_orders[order_id] = new_order
            
            # Create simulated response
            response = f"TRADOK;{symbol};{order_id};SENT;{side}STOP;{quantity};{limit_price};0;0;{quantity};SIMREF001;{command}"
            
            if not parse:
                return response
            
            return parse_order_response(response)
        
        # Real mode - use actual API
        response = self.send_command(command)
        
        # Check if we need to confirm the order
        if "TRADCONFIRM" in response:
            if not parse:
                return response
                
            confirm_response = parse_order_response(response)
            if confirm_response.get("confirmation_required", False):
                order_id = confirm_response.get("data", {}).get("order_id")
                if order_id:
                    confirm_cmd = f"CONFORD {order_id}"
                    response = self.send_command(confirm_cmd)
        
        if parse:
            return parse_order_response(response)
        return response
    
    def buy_stop(self, symbol: str, quantity: int, limit_price: float, 
                stop_price: float, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a buy stop order
        
        Args:
            symbol: The stock symbol/ticker
            quantity: Number of shares
            limit_price: Limit price
            stop_price: Stop/trigger price
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_stop_order(symbol, "BUY", quantity, limit_price, stop_price, parse)
        
    def sell_stop(self, symbol: str, quantity: int, limit_price: float, 
                 stop_price: float, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a sell stop order
        
        Args:
            symbol: The stock symbol/ticker
            quantity: Number of shares
            limit_price: Limit price
            stop_price: Stop/trigger price
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_stop_order(symbol, "SELL", quantity, limit_price, stop_price, parse)
    
    def confirm_order(self, order_id: str, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Confirm an order that requires confirmation
        
        Args:
            order_id: The ID of the order to confirm
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with confirmation details or raw response string
        """
        if self.simulation_mode:
            # In simulation mode, find and update the order status
            order_found = False
            for order in self.simulated_orders.values():
                if order["order_id"] == order_id:
                    order["status"] = "CONFIRMED"
                    order_found = True
                    break
            
            if order_found:
                symbol = next((o["symbol"] for o in self.simulated_orders.values() if o["order_id"] == order_id), "UNKNOWN")
                response = f"TRADOK;{symbol};{order_id};CONFIRMED;{order.get('side', 'UNKNOWN')};{order.get('quantity', 0)};{order.get('price', 0)};0;0;{order.get('quantity', 0)};SIMREF003;CONFORD {order_id}"
            else:
                response = "ERR;N/A;1020"  # Order not found
                
            if not parse:
                return response
            return parse_order_response(response)
        
        # Real mode - use actual API
        response = self.send_command(f"CONFORD {order_id}")
        if parse:
            return parse_order_response(response)
        return response
    
    def place_trailing_stop_order(self, symbol: str, side: str, quantity: int, 
                                 limit_price: float, stop_offset: float, 
                                 parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a trailing stop order with offset from current price
        
        Args:
            symbol: The stock symbol/ticker
            side: "BUY" or "SELL"
            quantity: Number of shares
            limit_price: Limit price
            stop_offset: Trailing stop offset/distance
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        side = side.upper()
        
        # Map side to Directa API commands
        if side == "BUY":
            cmd_prefix = "ACQTST"
        elif side == "SELL":
            cmd_prefix = "VENTST"
        else:
            raise ValueError("Side must be either 'BUY' or 'SELL'")
        
        # Generate a unique order ID
        order_id = f"ORD{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Format: ACQTST/VENTST ID_ORDINE,TICKER,QUANTITA',PREZZO_LIMITE,OFFSET
        command = f"{cmd_prefix} {order_id},{symbol},{quantity},{limit_price},{stop_offset}"
        
        if self.simulation_mode:
            # In simulation mode, create simulated order response
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Create the simulated order
            new_order = {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": limit_price,
                "stop_offset": stop_offset,
                "order_type": "TRAILING_STOP",
                "status": "PENDING",
                "time": current_time
            }
            
            # Add to simulated orders dictionary
            self.simulated_orders[order_id] = new_order
            
            # Create simulated response
            response = f"TRADOK;{symbol};{order_id};SENT;{side}TST;{quantity};{limit_price};0;0;{quantity};SIMREF001;{command}"
            
            if not parse:
                return response
            
            return parse_order_response(response)
        
        # Real mode - use actual API
        response = self.send_command(command)
        
        # Check if we need to confirm the order
        if "TRADCONFIRM" in response:
            if not parse:
                return response
                
            confirm_response = parse_order_response(response)
            if confirm_response.get("confirmation_required", False):
                order_id = confirm_response.get("data", {}).get("order_id")
                if order_id:
                    confirm_cmd = f"CONFORD {order_id}"
                    response = self.send_command(confirm_cmd)
        
        if parse:
            return parse_order_response(response)
        return response
    
    def buy_trailing_stop(self, symbol: str, quantity: int, limit_price: float, 
                         stop_offset: float, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a buy trailing stop order
        
        Args:
            symbol: The stock symbol/ticker
            quantity: Number of shares
            limit_price: Limit price
            stop_offset: Trailing stop offset/distance
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_trailing_stop_order(symbol, "BUY", quantity, limit_price, stop_offset, parse)
        
    def sell_trailing_stop(self, symbol: str, quantity: int, limit_price: float, 
                          stop_offset: float, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a sell trailing stop order
        
        Args:
            symbol: The stock symbol/ticker
            quantity: Number of shares
            limit_price: Limit price
            stop_offset: Trailing stop offset/distance
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_trailing_stop_order(symbol, "SELL", quantity, limit_price, stop_offset, parse)
    
    def place_iceberg_order(self, symbol: str, side: str, total_quantity: int, 
                           visible_quantity: int, price: float, 
                           parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place an iceberg order (only showing part of the total quantity)
        
        Args:
            symbol: The stock symbol/ticker
            side: "BUY" or "SELL"
            total_quantity: Total number of shares
            visible_quantity: Visible quantity in the order book
            price: Limit price
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        side = side.upper()
        
        # Map side to Directa API commands
        if side == "BUY":
            cmd_prefix = "ACQICE"
        elif side == "SELL":
            cmd_prefix = "VENICE"
        else:
            raise ValueError("Side must be either 'BUY' or 'SELL'")
        
        # Generate a unique order ID
        order_id = f"ORD{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Format: ACQICE/VENICE ID_ORDINE,TICKER,QUANTITA_TOTALE,QUANTITA_VISIBILE,PREZZO
        command = f"{cmd_prefix} {order_id},{symbol},{total_quantity},{visible_quantity},{price}"
        
        if self.simulation_mode:
            # In simulation mode, create simulated order response
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Create the simulated order
            new_order = {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": total_quantity,
                "visible_quantity": visible_quantity,
                "price": price,
                "order_type": "ICEBERG",
                "status": "PENDING",
                "time": current_time
            }
            
            # Add to simulated orders dictionary
            self.simulated_orders[order_id] = new_order
            
            # Create simulated response
            response = f"TRADOK;{symbol};{order_id};SENT;{side}ICE;{total_quantity};{price};0;0;{total_quantity};SIMREF001;{command}"
            
            if not parse:
                return response
            
            return parse_order_response(response)
        
        # Real mode - use actual API
        response = self.send_command(command)
        
        # Check if we need to confirm the order
        if "TRADCONFIRM" in response:
            if not parse:
                return response
                
            confirm_response = parse_order_response(response)
            if confirm_response.get("confirmation_required", False):
                order_id = confirm_response.get("data", {}).get("order_id")
                if order_id:
                    confirm_cmd = f"CONFORD {order_id}"
                    response = self.send_command(confirm_cmd)
        
        if parse:
            return parse_order_response(response)
        return response
    
    def buy_iceberg(self, symbol: str, total_quantity: int, visible_quantity: int, 
                   price: float, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a buy iceberg order
        
        Args:
            symbol: The stock symbol/ticker
            total_quantity: Total number of shares
            visible_quantity: Visible quantity in the order book
            price: Limit price
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_iceberg_order(symbol, "BUY", total_quantity, visible_quantity, price, parse)
        
    def sell_iceberg(self, symbol: str, total_quantity: int, visible_quantity: int, 
                    price: float, parse: bool = True) -> Union[Dict[str, Any], str]:
        """
        Place a sell iceberg order
        
        Args:
            symbol: The stock symbol/ticker
            total_quantity: Total number of shares
            visible_quantity: Visible quantity in the order book
            price: Limit price
            parse: Whether to parse the response (default: True)
            
        Returns:
            Dictionary with order details or raw response string
        """
        return self.place_iceberg_order(symbol, "SELL", total_quantity, visible_quantity, price, parse) 