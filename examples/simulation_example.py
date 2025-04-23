#!/usr/bin/env python3
"""
Esempio di utilizzo della modalità simulazione per Directa Trading API.
Questo script mostra come effettuare test senza utilizzare denaro reale.
"""

import os
import sys
import time
import logging
import json
import datetime

# Aggiungi la directory principale al path per importare directa_api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from directa_api import DirectaTrading

# Imposta il livello di logging per vedere le comunicazioni dettagliate
logging.basicConfig(level=logging.INFO)

def json_pretty_print(data):
    """Stampa i dati come JSON formattato"""
    # Custom JSON encoder to handle datetime objects
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return json.JSONEncoder.default(self, obj)
    
    print(json.dumps(data, indent=2, sort_keys=True, cls=DateTimeEncoder))

def main():
    print("Esempio modalità simulazione Directa Trading API")
    print("================================================")
    
    # Crea un'istanza API in modalità simulazione
    api = DirectaTrading(simulation_mode=True)
    
    # Non è necessario connettersi a Darwin in modalità simulazione
    # ma per coerenza con il codice reale, possiamo farlo comunque
    connected = api.connect()
    print(f"Connesso: {connected}")
    
    print("\n1. Verifica informazioni account iniziali (simulazione)")
    account_info = api.get_account_info()
    print("Informazioni account:")
    json_pretty_print(account_info)
    
    print("\n2. Verifica portfolio iniziale (vuoto)")
    portfolio = api.get_portfolio()
    print("Portfolio:")
    json_pretty_print(portfolio)
    
    print("\n3. Simula acquisto di azioni")
    order1 = api.place_order("INTC", "BUY", 100, 50.25)
    print("Risposta ordine #1:")
    json_pretty_print(order1)
    
    print("\n4. Simula un secondo acquisto")
    order2 = api.place_order("MSFT", "BUY", 50, 325.75)
    print("Risposta ordine #2:")
    json_pretty_print(order2)
    
    print("\n5. Verifica lista ordini")
    orders = api.get_orders()
    print("Lista ordini:")
    json_pretty_print(orders)
    
    print("\n6. Simula esecuzione del primo ordine")
    # Estrai l'ID del primo ordine
    order1_id = order1["data"]["order_id"]
    execution_success = api.simulate_order_execution(order1_id, executed_price=50.00)
    print(f"Esecuzione ordine: {'successo' if execution_success else 'fallimento'}")
    
    print("\n7. Verifica portfolio dopo l'esecuzione")
    portfolio = api.get_portfolio()
    print("Portfolio aggiornato:")
    json_pretty_print(portfolio)
    
    print("\n8. Verifica saldo account dopo acquisto")
    account_info = api.get_account_info()
    print("Informazioni account aggiornate:")
    json_pretty_print(account_info)
    
    print("\n9. Annulla il secondo ordine")
    order2_id = order2["data"]["order_id"]
    cancel_result = api.cancel_order(order2_id)
    print("Risultato cancellazione:")
    json_pretty_print(cancel_result)
    
    print("\n10. Verifica lista ordini dopo cancellazione")
    orders = api.get_orders()
    print("Lista ordini aggiornata:")
    json_pretty_print(orders)
    
    print("\n11. Simula vendita delle azioni possedute")
    order3 = api.place_order("INTC", "SELL", 100, 52.50)
    print("Risposta ordine vendita:")
    json_pretty_print(order3)
    
    print("\n12. Simula esecuzione dell'ordine di vendita")
    order3_id = order3["data"]["order_id"]
    execution_success = api.simulate_order_execution(order3_id, executed_price=52.25)
    print(f"Esecuzione ordine vendita: {'successo' if execution_success else 'fallimento'}")
    
    print("\n13. Verifica portfolio finale (dovrebbe essere vuoto)")
    portfolio = api.get_portfolio()
    print("Portfolio finale:")
    json_pretty_print(portfolio)
    
    print("\n14. Verifica saldo account finale")
    account_info = api.get_account_info()
    print("Informazioni account finali:")
    json_pretty_print(account_info)
    
    # Chiudi la connessione
    api.disconnect()
    print("\nTest completati!")

if __name__ == "__main__":
    main() 