# Directa API

Una libreria Python per interagire con le API di Directa Trading, che consente di effettuare operazioni di trading e recuperare dati storici.

## Caratteristiche

- **Trading API**: Connessione e interazione con l'API di trading Directa (porta 10002)
  - Piazzare ordini (limite, mercato, stop, trailing stop, iceberg)
  - Gestire ordini e posizioni
  - Recuperare informazioni di account e portafoglio
  - Modalità simulazione per testare strategie senza utilizzare denaro reale

- **Historical Data API**: Accesso ai dati storici di Directa (porta 10003)
  - Dati tick-by-tick
  - Dati a candele (intraday e giornalieri)
  - Intervalli di date personalizzati
  - Gestione volume after-hours


## Requisiti

- Python 3.9 o versioni successive
- Piattaforma Darwin di Directa in esecuzione sul sistema

## Installazione

```bash
# Clone del repository
git clone https://github.com/username/directa_api.git
cd directa_api

# Installazione
pip install -e .
```

## Guida rapida

### Trading API

```python
from directa_api import DirectaTrading

# Connessione all'API di trading
with DirectaTrading() as api:
    # Ottieni informazioni sull'account
    account_info = api.get_account_info()
    print(f"Liquidità: {account_info.get('data', {}).get('liquidity')}")
    
    # Piazza un ordine limite
    order = api.buy_limit("ENI.MI", 10, 13.50)
    
    # Ottieni informazioni sul portafoglio
    portfolio = api.get_portfolio()
    
    # Verifica lo stato degli ordini
    orders = api.get_orders()
```

### Historical Data API

```python
from directa_api import HistoricalData

# Connessione all'API per dati storici
with HistoricalData() as api:
    # Ottieni dati giornalieri
    daily_candles = api.get_daily_candles("ENI.MI", days=30)
    
    # Ottieni dati intraday (candele a 5 minuti)
    intraday_candles = api.get_intraday_candles("ENI.MI", days=1, period_minutes=5)
    
    # Ottieni dati tick by tick
    ticks = api.get_tick_data("ENI.MI", days=1)
    
    # Specifica un intervallo di date
    import datetime
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    
    # Candele orarie nell'intervallo
    candles = api.get_candle_data_range("ENI.MI", start_date, end_date, period_seconds=3600)
```

### Uso combinato

```python
from directa_api import DirectaTrading, HistoricalData
import pandas as pd

# Ottenimento dati storici
with HistoricalData() as historical:
    # Ottieni candele giornaliere
    candles = historical.get_daily_candles("ENI.MI", days=60)
    
    # Converti in DataFrame pandas per l'analisi
    df = pd.DataFrame(candles.get("data", []))
    
    # Calcola medie mobili
    df.set_index('timestamp', inplace=True)
    df['sma_10'] = df['close'].rolling(window=10).mean()
    df['sma_20'] = df['close'].rolling(window=20).mean()
    
    # Genera segnali
    df['signal'] = 0
    df.loc[df['sma_10'] > df['sma_20'], 'signal'] = 1  # Segnale di acquisto
    df.loc[df['sma_10'] < df['sma_20'], 'signal'] = -1  # Segnale di vendita

# Esegui ordini basati sui segnali
with DirectaTrading(simulation_mode=True) as trading:
    # Ottieni l'ultimo segnale
    last_signal = df['signal'].iloc[-1]
    
    if last_signal > 0:
        # Segnale di acquisto
        trading.buy_limit("ENI.MI", 10, df['close'].iloc[-1])
    elif last_signal < 0:
        # Segnale di vendita
        trading.sell_limit("ENI.MI", 10, df['close'].iloc[-1])
```

## Esempi

Nella cartella `examples/` sono presenti esempi più dettagliati:

- `trading_examples.py` - Esempi di trading (ordini, portfolio, account info)
- `historical_examples.py` - Esempi di recupero e analisi di dati storici
- `combined_example.py` - Esempio di strategia che combina dati storici e trading

Per eseguire gli esempi:

```bash
python examples/trading_examples.py
python examples/historical_examples.py
python examples/combined_example.py
```

## Note

- **Modalità simulazione**: Per evitare di utilizzare denaro reale durante i test, è possibile abilitare la modalità simulazione:

```python
api = DirectaTrading(simulation_mode=True)
```

- **Supporto per i contesti**: L'API supporta il protocollo context manager di Python per gestire automaticamente la connessione e disconnessione:

```python
with DirectaTrading() as api:
    # Operazioni di trading
    pass  # La disconnessione avviene automaticamente alla fine del blocco
```

## Dipendenze

- La piattaforma Darwin di Directa deve essere in esecuzione sul sistema locale
- Per l'analisi dei dati e gli esempi avanzati: pandas, matplotlib

## Licenza

Questo progetto è distribuito con licenza MIT. Vedere il file `LICENSE` per i dettagli.

## Disclaimer

Questo software è fornito "così com'è", senza garanzie di alcun tipo. L'autore e i contributori non sono responsabili per eventuali perdite finanziarie derivanti dall'uso di questo software. Utilizzare a proprio rischio e pericolo. Non è affiliato ufficialmente a Directa SIM.