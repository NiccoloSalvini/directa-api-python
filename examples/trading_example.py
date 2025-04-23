#!/usr/bin/env python3
"""
Example script showing how to use the Directa Trading API wrapper.
Make sure the Darwin trading platform is running before executing this script.
"""

import os
import sys
import time
import logging
import json

# Add parent directory to sys.path to import directa_api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from directa_api import DirectaTrading, get_error_message

# Set logging level to DEBUG to see detailed API communication
logging.getLogger("DirectaTrading").setLevel(logging.DEBUG)

def json_pretty_print(data):
    """Print data as formatted JSON"""
    print(json.dumps(data, indent=2, sort_keys=True))

def main():
    print("Directa Trading API Example")
    print("Make sure Darwin trading platform is running!")
    print("-------------------------------------------")
    
    # Connect to the Trading API using a context manager
    with DirectaTrading() as api:
        if not api.connected:
            print("Failed to connect to Directa Trading API. Is Darwin running?")
            return
        
        print(f"\nInitial connection status: {api.connection_status}")
        print(f"Is trading connected: {api.is_trading_connected}")
        
        print("\n1. Getting Darwin status...")
        try:
            # Richiedi lo stato del server prima di tutto
            raw_status = api.get_darwin_status(parse=False)
            print(f"Raw Darwin Status Response: {raw_status}")
            
            status_resp = api.get_darwin_status()
            print("Darwin Status (parsed):")
            json_pretty_print(status_resp)
            
            # Handle both old and new response formats
            if "status" in status_resp and status_resp["status"] == "success":
                # New format
                status_data = status_resp.get("data", {})
                if status_data:
                    connection_status = status_data.get("connection_status", "Unknown")
                    status_message = status_data.get("status_message", "")
                    
                    print(f"\nConnection Status: {connection_status}")
                    print(f"Status Message: {status_message}")
                    
                    # Show connection metrics
                    if "connection_metrics" in status_data:
                        metrics = status_data["connection_metrics"]
                        print("\nConnection Metrics:")
                        print(f"Currently Connected: {metrics.get('currently_connected', False)}")
                        print(f"Connection Attempts: {metrics.get('connection_attempts', 0)}")
                        print(f"Successful Connections: {metrics.get('successful_connections', 0)}")
                        print(f"Failed Connections: {metrics.get('failed_connections', 0)}")
                        
                        # Show uptime if available
                        if metrics.get("uptime_percentage") is not None:
                            print(f"Uptime Percentage: {metrics.get('uptime_percentage', 0):.2f}%")
                        
                        # Show recent connection history
                        if "connection_history" in metrics and metrics["connection_history"]:
                            print("\nRecent Connection Status Changes:")
                            for change in metrics["connection_history"][-3:]:  # Show last 3 changes
                                print(f"- {change['timestamp']}: {change['from']} → {change['to']}")
            elif "success" in status_resp and status_resp["success"]:
                # Old format (backward compatibility)
                status_data = status_resp.get("data", {})
                connection_status = status_data.get("connection_status", "Unknown")
                connection_description = status_data.get("connection_description", "")
                is_connected = status_data.get("is_connected", False)
                datafeed_enabled = status_data.get("datafeed_enabled", False)
                
                print(f"\nConnection Status: {connection_status}")
                print(f"Descrizione: {connection_description}")
                print(f"Datafeed Enabled: {datafeed_enabled}")
            else:
                # Error state
                print(f"\nError: {status_resp.get('error', 'Unknown error')}")
                
            # Show current connection status from instance
            print(f"\nConnection Status Tracker: {api.connection_status}")
            print(f"Is Trading Connected: {api.is_trading_connected}")
            
            # Warning if not connected
            if not api.is_trading_connected:
                print("\nATTENZIONE: Connessione Trading non disponibile.")
                print("Le operazioni informative funzioneranno, ma le operazioni di trading potrebbero fallire.")
                print("Verifica che la piattaforma Darwin sia correttamente collegata ai server di Directa.")
            
        except Exception as e:
            print(f"Error getting Darwin status: {str(e)}")
        
        print("\n2. Getting account information...")
        try:
            account_info = api.get_account_info()
            print("Account Info:")
            json_pretty_print(account_info)
            
            # Dopo aver richiesto le info account, mostra lo stato interno
            print(f"\nAfter account info - Connection Status: {api.connection_status}")
            print(f"Is Trading Connected: {api.is_trading_connected}")
            
            if account_info.get("success", False):
                account_data = account_info.get("data", {})
                account_code = account_data.get("account_code", "Unknown")
                liquidity = account_data.get("liquidity", 0)
                
                print(f"\nAccount Code: {account_code}")
                print(f"Liquidity: {liquidity}")
            
        except Exception as e:
            print(f"Error getting account info: {str(e)}")
        
        print("\n3. Getting portfolio information...")
        try:
            portfolio = api.get_portfolio()
            print("Portfolio:")
            json_pretty_print(portfolio)
            
            # Dopo aver richiesto il portfolio, mostra lo stato interno
            print(f"\nAfter portfolio - Connection Status: {api.connection_status}")
            print(f"Is Trading Connected: {api.is_trading_connected}")
            
            if portfolio.get("success", False):
                positions = portfolio.get("data", [])
                if positions:
                    print(f"\nFound {len(positions)} positions in portfolio")
                    for pos in positions:
                        symbol = pos.get("symbol", "Unknown")
                        qty = pos.get("quantity_portfolio", "0")
                        print(f"- {symbol}: {qty} shares")
                else:
                    print("\nNo positions in portfolio")
            elif "error_code" in portfolio:
                error_code = portfolio.get("error_code")
                print(f"\nError: {get_error_message(error_code)}")
            
        except Exception as e:
            print(f"Error getting portfolio: {str(e)}")
        
        print("\n4. Getting portfolio availability...")
        try:
            availability = api.get_availability()
            print("Availability:")
            json_pretty_print(availability)
            
            # Dopo aver richiesto la disponibilità, mostra lo stato interno
            print(f"\nAfter availability - Connection Status: {api.connection_status}")
            print(f"Is Trading Connected: {api.is_trading_connected}")
            
            if availability.get("success", False):
                avail_data = availability.get("data", {})
                total_liquidity = avail_data.get("total_liquidity", 0)
                
                print(f"\nTotal Liquidity: {total_liquidity}")
            
        except Exception as e:
            print(f"Error getting availability: {str(e)}")
        
        print("\n5. Getting order list...")
        try:
            orders = api.get_orders()
            print("Orders:")
            json_pretty_print(orders)
            
            # Dopo aver richiesto gli ordini, mostra lo stato interno
            print(f"\nAfter orders - Connection Status: {api.connection_status}")
            print(f"Is Trading Connected: {api.is_trading_connected}")
            
            if orders.get("success", False):
                order_list = orders.get("data", [])
                if order_list:
                    print(f"\nFound {len(order_list)} orders")
                    for order in order_list:
                        order_id = order.get("order_id", "Unknown")
                        symbol = order.get("symbol", "Unknown")
                        status = order.get("status_code", "Unknown")
                        print(f"- Order {order_id} for {symbol}: Status {status}")
                else:
                    print("\nNo active orders")
            elif "error_code" in orders:
                error_code = orders.get("error_code")
                if error_code == "1019":
                    print("\nNo active orders")
                else:
                    print(f"\nError: {get_error_message(error_code)}")
            
        except Exception as e:
            print(f"Error getting orders: {str(e)}")
            
        # Alla fine, ricontrolla lo stato di Darwin
        print("\nFinal connection check...")
        final_status = api.get_darwin_status()
        print(f"Final connection status: {api.connection_status}")
        print(f"Is trading connected: {api.is_trading_connected}")
        
        # Display connection metrics
        print("\nConnection Metrics Summary:")
        metrics = api.get_connection_metrics()
        if metrics.get("uptime_percentage") is not None:
            print(f"Uptime: {metrics.get('uptime_percentage', 0):.2f}%")
        print(f"Connection Attempts: {metrics.get('connection_attempts', 0)}")
        print(f"Successful Connections: {metrics.get('successful_connections', 0)}")
        print(f"Failed Connections: {metrics.get('failed_connections', 0)}")

        # Uncomment the following to place a real order (USE WITH CAUTION!)
        """
        print("\n6. Placing a test order...")
        try:
            symbol = "UCG"  # Unicredit stock symbol
            side = "BUY"
            quantity = 1
            price = 20.0  # Set an appropriate price
            
            # Place order and get parsed response
            order_response = api.place_order(symbol, side, quantity, price)
            print("Order Response:")
            json_pretty_print(order_response)
            
            # Wait a moment
            time.sleep(1)
            
            # If order was successful and we have an order_id
            if order_response.get("success", False) and "order_id" in order_response.get("data", {}):
                order_id = order_response["data"]["order_id"]
                print(f"\nCanceling order {order_id}...")
                cancel_response = api.cancel_order(order_id)
                print("Cancel Response:")
                json_pretty_print(cancel_response)
        except Exception as e:
            print(f"Error placing/canceling order: {str(e)}")
        """

if __name__ == "__main__":
    main() 