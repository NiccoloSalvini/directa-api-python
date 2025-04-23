# Directa Trading API

Un wrapper Python per interagire con l'API Trading di Directa SIM tramite la piattaforma Darwin.

## Caratteristiche

- Connessione all'API Trading di Directa SIM (porta 10002)
- Gestione automatica della connessione e monitoraggio dello stato
- Supporto per le operazioni di base (acquisto/vendita, cancellazione ordini)
- Supporto per query di portfolio, disponibilità e informazioni account
- Modalità simulazione per testare operazioni senza utilizzare denaro reale
- Parser dettagliati per le risposte dell'API

## Installazione

```bash
git clone https://github.com/TUOUSERNAME/directa-api-python.git
cd directa-api-python
pip install -e .
```

## Requisiti

- Python 3.7+
- Piattaforma di trading Darwin in esecuzione

## Utilizzo base

```python
from directa_api import DirectaTrading

# Connessione all'API
api = DirectaTrading()
if api.connect():
    # Verifica dello stato
    status = api.get_darwin_status()
    print(f"Stato connessione: {status['data']['connection_status']}")
    
    # Ottieni informazioni account
    account = api.get_account_info()
    print(f"Codice account: {account['data']['account_code']}")
    print(f"Liquidità: {account['data']['liquidity']}")
    
    # Ottieni portfolio
    portfolio = api.get_portfolio()
    if portfolio['success']:
        for position in portfolio['data']:
            print(f"{position['symbol']}: {position['quantity_portfolio']} azioni")
    
    # Chiusura connessione
    api.disconnect()
```

## Modalità Simulazione

È possibile utilizzare la modalità simulazione per testare operazioni senza utilizzare denaro reale:

```python
# Crea un'istanza in modalità simulazione
api = DirectaTrading(simulation_mode=True)
api.connect()

# Simula acquisto di azioni
order = api.place_order("INTC", "BUY", 100, 50.25)
order_id = order["data"]["order_id"]

# Simula esecuzione dell'ordine
api.simulate_order_execution(order_id, executed_price=50.00)

# Verifica portfolio simulato
portfolio = api.get_portfolio()
print(portfolio)

# Chiusura
api.disconnect()
```

Vedere `examples/simulation_example.py` per un esempio completo.

## Esempi

Nella directory `examples` sono presenti diversi script di esempio:

- `trading_example.py`: Esempio base di utilizzo dell'API
- `simulation_example.py`: Esempio di utilizzo della modalità simulazione
- `raw_socket_test.py`: Test di connessione socket semplice per diagnostica

## Note sull'API Directa

- L'API Trading di Directa è accessibile solo quando la piattaforma Darwin è in esecuzione
- L'API utilizza la porta 10002 per le operazioni di trading
- È necessario avere un account Directa attivo per utilizzare l'API in modalità reale

## Licenza

Questo progetto è distribuito con licenza MIT. Vedere il file `LICENSE` per i dettagli.

## Disclaimer

Questo software è fornito "così com'è", senza garanzie di alcun tipo. L'autore e i contributori non sono responsabili per eventuali perdite finanziarie derivanti dall'uso di questo software. Utilizzare a proprio rischio e pericolo. Non è affiliato ufficialmente a Directa SIM.