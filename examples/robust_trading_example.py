#!/usr/bin/env python3
"""
Directa API - Esempio di trading robusto

Questo esempio mostra come utilizzare le funzionalità robuste dell'API 
di trading, inclusa la gestione degli errori di connessione, retry automatici
e il monitoraggio dello stato della connessione.
"""

import time
import datetime
from directa_api import DirectaTrading

def example_robust_connection():
    """Esempio di connessione robusta con gestione degli errori"""
    print("\n=== Esempio di connessione robusta ===")
    
    # Inizializzazione con parametri di default
    api = DirectaTrading()
    
    # Tentativo di connessione con retry automatico
    if api.connect(max_retries=3, retry_delay=2):
        print("Connessione riuscita dopo eventuali retry!")
        
        # Verifica dettagliata dello stato della connessione
        status = api.get_darwin_status(retry=True)
        
        # Estrai le metriche di connessione
        conn_status = status.get('data', {}).get('connection_status')
        metrics = status.get('data', {}).get('connection_metrics', {})
        
        print(f"Stato connessione: {conn_status}")
        print(f"Tentativi di connessione: {metrics.get('connection_attempts')}")
        print(f"Ultima connessione: {metrics.get('last_connection_time')}")
        print(f"Tempo connessione totale: {metrics.get('total_connected_time')} secondi")
        print(f"Storia connessioni: {metrics.get('connection_history_summary')}")
        
        # Chiusura della connessione
        api.disconnect()
        print("Connessione chiusa")
    else:
        print("Connessione fallita dopo tutti i tentativi")

def example_trading_with_error_handling():
    """Esempio di trading con gestione avanzata degli errori"""
    print("\n=== Esempio di trading con gestione degli errori ===")
    
    # Usa la modalità simulazione per evitare ordini reali
    with DirectaTrading(simulation_mode=True) as api:
        print("API in modalità simulazione con gestione errori")
        
        # Simbolo di esempio
        symbol = "ENI.MI"
        
        # Tenta di piazzare un ordine con gestione degli errori
        try:
            # Ordine limite di acquisto
            buy_order = api.buy_limit(symbol, 10, 12.50)
            
            if buy_order.get("success", False):
                order_id = buy_order.get("data", {}).get("order_id")
                print(f"Ordine limite di acquisto creato con ID: {order_id}")
                
                # Verifica lo stato dell'ordine
                time.sleep(1)  # Breve attesa per simulare il processing
                
                order_status = api.get_order_status(order_id)
                if order_status.get("success", False):
                    status = order_status.get("data", {}).get("status")
                    print(f"Stato dell'ordine: {status}")
                else:
                    print(f"Errore nel recupero dello stato: {order_status.get('error')}")
            else:
                error = buy_order.get("error", "Errore sconosciuto")
                print(f"Errore nell'inserimento dell'ordine: {error}")
                
                # Se è un errore di connessione, tenta un recupero
                if "connection" in error.lower():
                    print("Rilevato errore di connessione, tentativo di recupero...")
                    
                    # Verifica lo stato della connessione con retry
                    status = api.get_darwin_status(retry=True)
                    if status.get("success", False) and status.get("data", {}).get("connection_status") == "connected":
                        print("Connessione ripristinata, ritentativo ordine...")
                        buy_order = api.buy_limit(symbol, 10, 12.50)
                        if buy_order.get("success", False):
                            print("Ordine inserito con successo dopo il recupero!")
                        else:
                            print("Fallito anche dopo il recupero della connessione")
        
        except Exception as e:
            print(f"Eccezione durante il trading: {str(e)}")
            # Un'applicazione reale potrebbe implementare strategie di recupero più sofisticate

def example_connection_monitoring():
    """Esempio di monitoraggio continuo della connessione"""
    print("\n=== Esempio di monitoraggio della connessione ===")
    
    api = DirectaTrading()
    
    try:
        # Connessione iniziale
        if not api.connect():
            print("Connessione iniziale fallita")
            return
        
        print("Connessione stabilita, inizio monitoraggio...")
        
        # Simula un monitoraggio di 30 secondi
        start_time = time.time()
        monitoring_time = 30  # secondi
        check_interval = 5    # controlla ogni 5 secondi
        
        while time.time() - start_time < monitoring_time:
            # Verifica lo stato con retry automatico
            status = api.get_darwin_status(retry=True)
            
            if status.get("success", False):
                conn_status = status.get("data", {}).get("connection_status")
                metrics = status.get("data", {}).get("connection_metrics", {})
                
                print(f"\nStato connessione: {conn_status}")
                print(f"Tempo connessione: {metrics.get('current_session_time')} secondi")
                print(f"Connessioni stabilite: {metrics.get('connection_attempts')}")
                
                # Esempio di logica per decidere se riconnettere
                if conn_status != "connected":
                    print("Connessione persa! Tentativo di riconnessione...")
                    if api.connect(max_retries=2):
                        print("Riconnessione riuscita!")
                    else:
                        print("Riconnessione fallita, termine monitoraggio")
                        break
            else:
                print(f"Errore nel controllo dello stato: {status.get('error')}")
            
            # Attendi prima del prossimo controllo
            time.sleep(check_interval)
        
        print("\nMonitoraggio completato")
    
    finally:
        # Assicura la disconnessione
        api.disconnect()
        print("Connessione chiusa")

def example_order_lifecycle():
    """Esempio completo del ciclo di vita di un ordine con gestione degli errori"""
    print("\n=== Esempio ciclo di vita ordine con gestione errori ===")
    
    # Usa la modalità simulazione
    with DirectaTrading(simulation_mode=True) as api:
        print("API in modalità simulazione")
        
        # Simbolo di esempio
        symbol = "ENI.MI"
        
        try:
            # 1. Inserimento dell'ordine
            print("Inserimento ordine limite di acquisto...")
            buy_order = api.buy_limit(symbol, 10, 12.50)
            
            if not buy_order.get("success", False):
                raise Exception(f"Errore inserimento ordine: {buy_order.get('error')}")
            
            order_id = buy_order.get("data", {}).get("order_id")
            print(f"Ordine creato con ID: {order_id}")
            
            # 2. Verifica dello stato dell'ordine
            print("Verifica stato ordine...")
            time.sleep(1)  # Breve attesa per simulare il processing
            
            order_status = api.get_order_status(order_id)
            if not order_status.get("success", False):
                raise Exception(f"Errore recupero stato ordine: {order_status.get('error')}")
            
            status = order_status.get("data", {}).get("status")
            print(f"Stato ordine: {status}")
            
            # 3. Modifica dell'ordine
            print("Modifica del prezzo dell'ordine...")
            modify_result = api.modify_order(order_id, new_price=12.75)
            
            if not modify_result.get("success", False):
                print(f"Errore modifica ordine: {modify_result.get('error')}")
                print("Continuiamo comunque con l'ordine originale...")
            else:
                print("Ordine modificato con successo")
                
                # Verifica del nuovo stato
                time.sleep(1)
                order_status = api.get_order_status(order_id)
                if order_status.get("success", False):
                    new_price = order_status.get("data", {}).get("price")
                    print(f"Nuovo prezzo dell'ordine: {new_price}")
            
            # 4. Simulazione dell'esecuzione parziale dell'ordine
            print("Simulazione di un'esecuzione parziale dell'ordine...")
            execution = api.simulate_order_execution(order_id, quantity=5, fill_price=12.75)
            
            if execution.get("success", False):
                filled_qty = execution.get("data", {}).get("filled_quantity")
                print(f"Ordine parzialmente eseguito: {filled_qty} su 10 azioni")
                
                # Verifica del nuovo stato dell'ordine
                order_status = api.get_order_status(order_id)
                if order_status.get("success", False):
                    remaining_qty = order_status.get("data", {}).get("remaining_quantity")
                    print(f"Quantità rimanente: {remaining_qty}")
            
            # 5. Cancellazione dell'ordine rimanente
            print("Cancellazione dell'ordine rimanente...")
            cancel_result = api.cancel_order(order_id)
            
            if cancel_result.get("success", False):
                print("Ordine cancellato con successo")
            else:
                print(f"Errore cancellazione: {cancel_result.get('error')}")
            
            # 6. Verifica del portafoglio aggiornato
            print("Verifica del portafoglio aggiornato...")
            portfolio = api.get_portfolio()
            
            if portfolio.get("success", False):
                positions = portfolio.get("data", {}).get("stocks", [])
                print(f"Portafoglio contiene {len(positions)} posizioni:")
                
                # Cerca la posizione appena creata
                for position in positions:
                    if position.get("symbol") == symbol:
                        print(f"Posizione {symbol}: {position.get('quantity')} azioni a prezzo medio {position.get('avg_price')}")
        
        except Exception as e:
            print(f"Errore durante il ciclo di vita dell'ordine: {str(e)}")

if __name__ == "__main__":
    try:
        print("Directa API - Esempi di Trading Robusto")
        print("========================================")
        
        # Esegui esempi
        example_robust_connection()
        example_trading_with_error_handling()
        example_connection_monitoring()
        example_order_lifecycle()
        
    except Exception as e:
        print(f"Errore durante l'esecuzione degli esempi: {str(e)}") 