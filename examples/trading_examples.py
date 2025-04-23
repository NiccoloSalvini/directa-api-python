#!/usr/bin/env python3
"""
Directa API Trading Examples

Questo file contiene esempi di utilizzo dell'API di trading di Directa.
"""

import time
import datetime
from directa_api import DirectaTrading

# Esempio 1: Connessione base
def example_connection():
    """Esempio di connessione base all'API di trading"""
    print("\n=== Esempio di connessione ===")
    
    # Inizializzazione con parametri di default (localhost:10002)
    api = DirectaTrading()
    
    # Connessione
    if api.connect():
        print("Connessione riuscita!")
        
        # Verifica dello stato della connessione
        status = api.get_darwin_status()
        print(f"Stato connessione: {status.get('data', {}).get('connection_status')}")
        
        # Metriche di connessione
        metrics = api.get_connection_metrics()
        print(f"Tentativi di connessione: {metrics.get('connection_attempts')}")
        print(f"Connesso: {metrics.get('currently_connected')}")
        
        # Chiusura della connessione
        api.disconnect()
        print("Connessione chiusa")
    else:
        print("Connessione fallita")

# Esempio 2: Uso del contesto manager (with)
def example_context_manager():
    """Esempio di utilizzo come context manager con 'with'"""
    print("\n=== Esempio di context manager ===")
    
    # Uso dell'API come context manager (gestisce automaticamente connect/disconnect)
    with DirectaTrading() as api:
        print("Connessione stabilita automaticamente")
        
        # Verifica dello stato
        status = api.get_darwin_status()
        print(f"Stato connessione: {status.get('data', {}).get('connection_status')}")
        
        # Fine del blocco with -> disconnessione automatica
    print("Disconnessione automatica completata")

# Esempio 3: Informazioni di account
def example_account_info():
    """Esempio per ottenere informazioni sull'account"""
    print("\n=== Esempio informazioni account ===")
    
    # Usando il context manager
    with DirectaTrading() as api:
        # Ottieni informazioni sull'account
        account_info = api.get_account_info()
        
        if account_info.get("success", False):
            data = account_info.get("data", {})
            print(f"Codice account: {data.get('account_code')}")
            print(f"Liquidità: {data.get('liquidity')}")
            print(f"Equity: {data.get('equity')}")
        else:
            print(f"Errore: {account_info.get('error')}")
        
        # Ottieni informazioni sul portafoglio
        portfolio = api.get_portfolio()
        
        if portfolio.get("success", False):
            stocks = portfolio.get("data", {}).get("stocks", [])
            print(f"Numero di posizioni in portafoglio: {len(stocks)}")
            
            for stock in stocks:
                print(f"Titolo: {stock.get('symbol')}, Quantità: {stock.get('quantity')}, Prezzo medio: {stock.get('avg_price')}")
        else:
            print(f"Errore portafoglio: {portfolio.get('error')}")

# Esempio 4: Ordini di trading base
def example_basic_orders():
    """Esempio di ordini di trading base"""
    print("\n=== Esempio ordini base ===")
    
    # Usa la modalità simulazione per evitare ordini reali
    with DirectaTrading(simulation_mode=True) as api:
        print("API in modalità simulazione")
        
        # Simbolo di esempio
        symbol = "ENI.MI"
        
        # 1. Ordine limite di acquisto
        buy_order = api.buy_limit(symbol, 10, 12.50)
        
        if buy_order.get("success", False):
            order_id = buy_order.get("data", {}).get("order_id")
            print(f"Ordine limite di acquisto creato con ID: {order_id}")
        else:
            print(f"Errore ordine acquisto: {buy_order.get('error')}")
        
        # 2. Ordine di mercato di vendita
        sell_order = api.sell_market(symbol, 5)
        
        if sell_order.get("success", False):
            order_id = sell_order.get("data", {}).get("order_id")
            print(f"Ordine di mercato di vendita creato con ID: {order_id}")
        else:
            print(f"Errore ordine vendita: {sell_order.get('error')}")
        
        # 3. Ottieni lista ordini
        orders = api.get_orders()
        
        if orders.get("success", False):
            orders_list = orders.get("data", {}).get("orders", [])
            print(f"Numero di ordini attivi: {len(orders_list)}")
            
            for order in orders_list:
                print(f"ID: {order.get('order_id')}, Simbolo: {order.get('symbol')}, Tipo: {order.get('side')}, Stato: {order.get('status')}")
        
        # 4. Cancella un ordine
        if buy_order.get("success", False):
            order_id = buy_order.get("data", {}).get("order_id")
            cancel_result = api.cancel_order(order_id)
            
            if cancel_result.get("success", False):
                print(f"Ordine {order_id} cancellato con successo")
            else:
                print(f"Errore cancellazione: {cancel_result.get('error')}")

# Esempio 5: Ordini avanzati
def example_advanced_orders():
    """Esempio di ordini avanzati"""
    print("\n=== Esempio ordini avanzati ===")
    
    # Usa la modalità simulazione per evitare ordini reali
    with DirectaTrading(simulation_mode=True) as api:
        print("API in modalità simulazione")
        
        # Simbolo di esempio
        symbol = "INTC"
        
        # 1. Stop order
        stop_order = api.buy_stop(symbol, 10, 50.0, 52.0)
        
        if stop_order.get("success", False):
            order_id = stop_order.get("data", {}).get("order_id")
            print(f"Stop order creato con ID: {order_id}")
        else:
            print(f"Errore stop order: {stop_order.get('error')}")
        
        # 2. Trailing stop
        trailing_stop = api.sell_trailing_stop(symbol, 5, 48.0, 2.0)
        
        if trailing_stop.get("success", False):
            order_id = trailing_stop.get("data", {}).get("order_id")
            print(f"Trailing stop creato con ID: {order_id}")
        else:
            print(f"Errore trailing stop: {trailing_stop.get('error')}")
        
        # 3. Ordine iceberg
        iceberg = api.buy_iceberg(symbol, 100, 20, 49.5)
        
        if iceberg.get("success", False):
            order_id = iceberg.get("data", {}).get("order_id")
            print(f"Ordine iceberg creato con ID: {order_id}")
        else:
            print(f"Errore ordine iceberg: {iceberg.get('error')}")

# Esempio 6: Simulazione completa
def example_simulation():
    """Esempio di simulazione completa di trading"""
    print("\n=== Esempio simulazione completa ===")
    
    # Crea API in modalità simulazione
    api = DirectaTrading(simulation_mode=True)
    api.connect()
    
    try:
        print("Stato iniziale dell'account:")
        account = api.get_account_info()
        initial_liquidity = account.get("data", {}).get("liquidity", 0)
        print(f"Liquidità iniziale: {initial_liquidity}")
        
        # Aggiungi una posizione simulata
        symbol = "AAPL"
        api.add_simulated_position(symbol, 10, 150.0)
        print(f"Aggiunta posizione simulata: 10 AAPL @ 150.0")
        
        # Verifica portafoglio dopo l'aggiunta
        portfolio = api.get_portfolio()
        print("Portafoglio dopo l'aggiunta:")
        for stock in portfolio.get("data", {}).get("stocks", []):
            print(f"Titolo: {stock.get('symbol')}, Quantità: {stock.get('quantity')}, Prezzo medio: {stock.get('avg_price')}")
        
        # Simula un ordine
        print("\nCreazione ordine limite di acquisto...")
        order = api.buy_limit(symbol, 5, 155.0)
        order_id = order.get("data", {}).get("order_id")
        print(f"Ordine creato con ID: {order_id}")
        
        # Simula l'esecuzione dell'ordine
        print("\nSimulazione dell'esecuzione dell'ordine...")
        execution = api.simulate_order_execution(order_id, fill_price=155.0)
        
        if execution.get("success", False):
            print("Ordine eseguito con successo")
            print(f"Valore transazione: {execution.get('data', {}).get('value')}")
            
            # Verifica lo stato dell'account dopo l'esecuzione
            account_after = api.get_account_info()
            final_liquidity = account_after.get("data", {}).get("liquidity", 0)
            print(f"Liquidità dopo l'esecuzione: {final_liquidity}")
            print(f"Variazione liquidità: {final_liquidity - initial_liquidity}")
            
            # Verifica portafoglio finale
            final_portfolio = api.get_portfolio()
            print("\nPortafoglio finale:")
            for stock in final_portfolio.get("data", {}).get("stocks", []):
                print(f"Titolo: {stock.get('symbol')}, Quantità: {stock.get('quantity')}, Prezzo medio: {stock.get('avg_price')}")
        else:
            print(f"Errore esecuzione: {execution.get('error')}")
    
    finally:
        # Disconnetti
        api.disconnect()

if __name__ == "__main__":
    try:
        print("Directa API - Esempi di Trading")
        print("================================")
        
        # Esegui tutti gli esempi
        example_connection()
        example_context_manager()
        example_account_info()
        example_basic_orders()
        example_advanced_orders()
        example_simulation()
        
    except Exception as e:
        print(f"Errore durante l'esecuzione degli esempi: {str(e)}") 