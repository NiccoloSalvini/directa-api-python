#!/usr/bin/env python3
"""
Unit tests for the simulation mode
"""
import pytest
from directa_api.trading import DirectaTrading

def test_simulation_init():
    """Test simulation mode initialization"""
    api = DirectaTrading(simulation_mode=True)
    assert api.simulation_mode is True
    assert api.simulated_account is not None
    assert api.simulated_portfolio == []
    assert isinstance(api.simulated_orders, dict)

def test_simulation_account_info():
    """Test simulation account info"""
    api = DirectaTrading(simulation_mode=True)
    account_info = api.get_account_info()
    
    assert account_info["success"] is True
    assert account_info["data"]["account_code"] == "SIM1234"
    assert account_info["data"]["liquidity"] == 10000.0
    assert account_info["data"]["equity"] == 10000.0

def test_simulation_empty_portfolio():
    """Test simulation empty portfolio"""
    api = DirectaTrading(simulation_mode=True)
    portfolio = api.get_portfolio()
    
    assert portfolio["success"] is False
    assert portfolio["error_code"] == "1018"

def test_simulation_order_placement():
    """Test simulation order placement"""
    api = DirectaTrading(simulation_mode=True)
    
    # Place a test order
    order = api.place_order("TEST", "BUY", 100, 50.0)
    
    assert order["success"] is True
    assert order["data"]["symbol"] == "TEST"
    assert order["data"]["quantity"] == "100"
    assert order["data"]["price"] == "50.0"
    assert order["data"]["status_code"] == "SENT"
    
    # Check orders list
    order_id = order["data"]["order_id"]
    assert len(api.simulated_orders) == 1
    assert api.simulated_orders[order_id]["symbol"] == "TEST"
    assert api.simulated_orders[order_id]["quantity"] == 100
    assert api.simulated_orders[order_id]["price"] == 50.0
    assert api.simulated_orders[order_id]["side"] == "BUY"

def test_simulation_order_execution():
    """Test simulation order execution"""
    api = DirectaTrading(simulation_mode=True)
    api.fix_test()  # Reset to clean state
    
    # Place and execute an order
    order = api.place_order("TEST", "BUY", 100, 50.0)
    order_id = order["data"]["order_id"]
    
    execution_result = api.simulate_order_execution(order_id, executed_price=49.5)
    assert execution_result["success"] is True
    
    # Check portfolio
    portfolio = api.get_portfolio()
    assert portfolio["success"] is True
    assert len(portfolio["data"]) == 1
    assert portfolio["data"][0]["symbol"] == "TEST"
    assert portfolio["data"][0]["quantity_portfolio"] == "100"
    
    # Check account (should have 10000 - (49.5 * 100) = 5050)
    account_info = api.get_account_info()
    assert account_info["data"]["liquidity"] == 5050.0

def test_simulation_order_cancellation():
    """Test simulation order cancellation"""
    api = DirectaTrading(simulation_mode=True)
    
    # Place an order
    order = api.place_order("TEST", "BUY", 100, 50.0)
    order_id = order["data"]["order_id"]
    
    # Cancel the order
    cancel_result = api.cancel_order(order_id)
    assert cancel_result["success"] is True
    
    # Check order status
    for order_value in api.simulated_orders.values():
        if order_value["order_id"] == order_id:
            assert order_value["status"] == "CANCELLED"

def test_simulation_buy_sell_sequence():
    """Test buy and sell sequence in simulation"""
    api = DirectaTrading(simulation_mode=True)
    # Reset simulation state for a clean test
    api.fix_test()
    
    initial_liquidity = api.simulated_account["liquidity"]
    assert initial_liquidity == 10000.0  # Verify initial state
    
    # Buy stocks
    buy_order = api.place_order("TEST", "BUY", 100, 50.0)
    buy_order_id = buy_order["data"]["order_id"]
    api.simulate_order_execution(buy_order_id)
    
    # Account should have less liquidity after buying
    account_after_buy = api.get_account_info()
    buy_liquidity = account_after_buy["data"]["liquidity"]
    assert buy_liquidity < initial_liquidity
    assert buy_liquidity == 5000.0  # 10000 - (100 * 50.0)
    
    # Get portfolio to verify shares are there
    portfolio_after_buy = api.get_portfolio()
    assert portfolio_after_buy["success"] is True
    assert len(portfolio_after_buy["data"]) == 1
    assert portfolio_after_buy["data"][0]["symbol"] == "TEST"
    assert portfolio_after_buy["data"][0]["quantity_portfolio"] == "100"
    
    # Sell stocks at higher price
    sell_order = api.place_order("TEST", "SELL", 100, 55.0)
    sell_order_id = sell_order["data"]["order_id"]
    api.simulate_order_execution(sell_order_id, executed_price=55.0)  # Explicitly set execution price
    
    # Account should have more liquidity after selling
    account_after_sell = api.get_account_info()
    sell_liquidity = account_after_sell["data"]["liquidity"]
    
    # Expected: 5000 + (100 * 55) = 10500
    expected_after_sell = buy_liquidity + (100 * 55.0)
    assert sell_liquidity == expected_after_sell, f"Expected liquidity after sell to be {expected_after_sell}, but got {sell_liquidity}"
    assert sell_liquidity > buy_liquidity
    
    # Check portfolio status after selling
    portfolio_after_sell = api.get_portfolio()
    # Portfolio should be empty or TEST position should be removed
    if portfolio_after_sell["success"]:
        test_positions = [pos for pos in portfolio_after_sell["data"] if pos["symbol"] == "TEST"]
        assert len(test_positions) == 0, "TEST position should be removed after selling all shares"

def test_darwin_status_simulation():
    """Test darwin status in simulation mode"""
    api = DirectaTrading(simulation_mode=True)
    status = api.get_darwin_status()
    
    assert status["success"] is True
    assert status["status"] == "success"
    assert status["data"]["connection_status"] == "CONN_OK"
    assert status["data"]["simulation_mode"] is True 