#!/usr/bin/env python3
"""
Unit tests for the simulation mode
"""
import unittest
import pytest
from directa_api.trading import DirectaTrading

class TestSimulation(unittest.TestCase):
    def test_simulation_init(self):
        """Test simulation mode initialization"""
        api = DirectaTrading(simulation_mode=True)
        self.assertTrue(api.simulation_mode)
        self.assertIsNotNone(api.simulation)
        self.assertEqual(api.simulation.portfolio, [])
        self.assertIsInstance(api.simulation.orders, dict)

    def test_simulation_account_info(self):
        """Test simulation account info"""
        api = DirectaTrading(simulation_mode=True)
        account_info = api.get_account_info()
        
        self.assertTrue(account_info["success"])
        self.assertEqual(account_info["data"]["account_code"], "SIM1234")
        self.assertEqual(account_info["data"]["liquidity"], 10000.0)
        self.assertEqual(account_info["data"]["equity"], 10000.0)

    def test_simulation_empty_portfolio(self):
        """Test simulation empty portfolio"""
        api = DirectaTrading(simulation_mode=True)
        # Reset the simulation to ensure it's empty
        api.simulation.reset_state()
        # Empty the portfolio explicitly
        api.simulation.portfolio = []
        portfolio = api.get_portfolio()
        
        # Debug output
        print("\nDebug portfolio data:")
        print(f"Portfolio data keys: {portfolio['data'].keys()}")
        print(f"Stocks: {portfolio['data']['stocks']}")
        
        # Check if portfolio is empty
        self.assertTrue(portfolio["success"])
        self.assertEqual(len(portfolio["data"]["stocks"]), 0, "Portfolio should be empty")

    def test_simulation_order_placement(self):
        """Test simulation order placement"""
        api = DirectaTrading(simulation_mode=True)
        api.simulation.reset_state()
        
        # Place a test order
        order = api.place_order("TEST", "BUY", 100, 50.0)
        
        self.assertTrue(order["success"])
        
        # Extract order_id from the response
        order_id = order["data"]["order_id"]
        
        # Check if order is in the simulation orders
        self.assertEqual(len(api.simulation.orders), 1)
        self.assertEqual(api.simulation.orders[order_id]["symbol"], "TEST")
        self.assertEqual(api.simulation.orders[order_id]["quantity"], 100)
        self.assertEqual(api.simulation.orders[order_id]["price"], 50.0)
        self.assertEqual(api.simulation.orders[order_id]["side"], "BUY")

    def test_simulation_order_execution(self):
        """Test simulation order execution"""
        api = DirectaTrading(simulation_mode=True)
        # Reset to clean state
        api.simulation.reset_state()
        
        # Place and execute an order
        order = api.place_order("TEST", "BUY", 100, 50.0)
        order_id = order["data"]["order_id"]
        
        # Get initial liquidity
        initial_liquidity = api.simulation.account["liquidity"]
        
        # Execute the order - using the simulation instance directly
        execution_result = api.simulation.execute_order(order_id, fill_price=49.5)
        self.assertTrue(execution_result["success"])
        
        # Check portfolio
        portfolio = api.get_portfolio()
        self.assertTrue(portfolio["success"])
        
        # Find TEST positions in the stocks array
        test_positions = [pos for pos in portfolio["data"]["stocks"] if pos["symbol"] == "TEST"]
        self.assertEqual(len(test_positions), 1, "Should have exactly one TEST position")
        
        # Check the position details
        test_position = test_positions[0]
        self.assertEqual(test_position["symbol"], "TEST")
        self.assertEqual(test_position["quantity"], 100)
        
        # Check account (should have initial - (49.5 * 100))
        account_info = api.get_account_info()
        expected_liquidity = initial_liquidity - (49.5 * 100)
        self.assertEqual(account_info["data"]["liquidity"], expected_liquidity)

    def test_simulation_order_cancellation(self):
        """Test simulation order cancellation"""
        api = DirectaTrading(simulation_mode=True)
        api.simulation.reset_state()
        
        # Place an order
        order = api.place_order("TEST", "BUY", 100, 50.0)
        order_id = order["data"]["order_id"]
        
        # Cancel the order - use simulation instance directly
        cancel_result = api.simulation.cancel_order(order_id)
        self.assertTrue(cancel_result["success"])
        
        # Check order status
        self.assertEqual(api.simulation.orders[order_id]["status"], "CANCELLED")

    def test_simulation_buy_sell_sequence(self):
        """Test buy and sell sequence in simulation"""
        api = DirectaTrading(simulation_mode=True)
        # Reset simulation state for a clean test
        api.simulation.reset_state()
        
        initial_liquidity = api.simulation.account["liquidity"]
        self.assertEqual(initial_liquidity, 10000.0)  # Verify initial state
        
        # Buy stocks
        buy_order = api.place_order("TEST", "BUY", 100, 50.0)
        buy_order_id = buy_order["data"]["order_id"]
        buy_execution = api.simulation.execute_order(buy_order_id)
        self.assertTrue(buy_execution["success"])
        
        # Account should have less liquidity after buying
        account_after_buy = api.get_account_info()
        buy_liquidity = account_after_buy["data"]["liquidity"]
        self.assertLess(buy_liquidity, initial_liquidity)
        self.assertEqual(buy_liquidity, 5000.0)  # 10000 - (100 * 50.0)
        
        # Get portfolio to verify shares are there
        portfolio_after_buy = api.get_portfolio()
        self.assertTrue(portfolio_after_buy["success"])
        
        # Check for TEST positions
        test_positions_buy = [pos for pos in portfolio_after_buy["data"]["stocks"] if pos["symbol"] == "TEST"]
        self.assertEqual(len(test_positions_buy), 1, "Should have exactly one TEST position after buying")
        
        # Check position details
        self.assertEqual(test_positions_buy[0]["symbol"], "TEST")
        self.assertEqual(test_positions_buy[0]["quantity"], 100)
        
        # Sell stocks at higher price
        sell_order = api.place_order("TEST", "SELL", 100, 55.0)
        sell_order_id = sell_order["data"]["order_id"]
        sell_execution = api.simulation.execute_order(sell_order_id, fill_price=55.0)  # Explicitly set execution price
        self.assertTrue(sell_execution["success"])
        
        # Account should have more liquidity after selling
        account_after_sell = api.get_account_info()
        sell_liquidity = account_after_sell["data"]["liquidity"]
        
        # Expected: 5000 + (100 * 55) = 10500
        expected_after_sell = buy_liquidity + (100 * 55.0)
        self.assertEqual(sell_liquidity, expected_after_sell, 
                         f"Expected liquidity after sell to be {expected_after_sell}, but got {sell_liquidity}")
        self.assertGreater(sell_liquidity, buy_liquidity)
        
        # Check portfolio status after selling
        portfolio_after_sell = api.get_portfolio()
        # Portfolio should have no TEST positions
        test_positions_sell = [pos for pos in portfolio_after_sell["data"]["stocks"] if pos["symbol"] == "TEST"]
        self.assertEqual(len(test_positions_sell), 0, "TEST position should be removed after selling all shares")

    def test_darwin_status_simulation(self):
        """Test darwin status in simulation mode"""
        api = DirectaTrading(simulation_mode=True)
        status = api.get_darwin_status()
        
        self.assertTrue(status["success"])
        self.assertEqual(status["data"]["connection_status"], "CONN_OK")
        self.assertTrue(status["data"]["simulation_mode"])
        self.assertIn("connection_metrics", status["data"])

if __name__ == "__main__":
    unittest.main() 