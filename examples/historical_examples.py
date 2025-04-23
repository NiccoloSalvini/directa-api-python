#!/usr/bin/env python3
"""
Directa API Historical Data Examples

Questo file contiene esempi di utilizzo dell'API per dati storici di Directa.
"""

import time
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from directa_api import HistoricalData

# Esempio 1: Connessione base
def example_connection():
    """Esempio di connessione base all'API storica"""
    print("\n=== Esempio di connessione ===")
    
    # Inizializzazione con parametri di default (localhost:10003)
    api = HistoricalData()
    
    # Connessione
    if api.connect():
        print("Connessione riuscita!")
        
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
    with HistoricalData() as api:
        print("Connessione stabilita automaticamente")
        
        # Fine del blocco with -> disconnessione automatica
    print("Disconnessione automatica completata")

# Esempio 3: Ottenere dati di candele giornaliere
def example_daily_candles():
    """Esempio per ottenere dati di candele giornaliere"""
    print("\n=== Esempio candele giornaliere ===")
    
    # Usando il context manager
    with HistoricalData() as api:
        # Ottieni candele giornaliere per un simbolo
        symbol = "ENI.MI"  # Titolo di esempio
        days = 30  # Ultimi 30 giorni
        
        print(f"Richiesta candele giornaliere per {symbol}, ultimi {days} giorni")
        candles = api.get_daily_candles(symbol, days)
        
        if candles.get("success", False):
            data = candles.get("data", [])
            print(f"Ricevute {len(data)} candele")
            
            if data:
                # Stampa le prime 5 candele
                print("\nPrime 5 candele:")
                for i, candle in enumerate(data[:5]):
                    print(f"Data: {candle.get('timestamp').strftime('%Y-%m-%d')}, "
                          f"Apertura: {candle.get('open')}, "
                          f"Massimo: {candle.get('high')}, "
                          f"Minimo: {candle.get('low')}, "
                          f"Chiusura: {candle.get('close')}, "
                          f"Volume: {candle.get('volume')}")
                
                # Riepilogo dell'intervallo di date
                first_date = data[0].get('timestamp').strftime('%Y-%m-%d')
                last_date = data[-1].get('timestamp').strftime('%Y-%m-%d')
                print(f"\nIntervallo date: da {first_date} a {last_date}")
        else:
            print(f"Errore: {candles.get('error')}")

# Esempio 4: Ottenere dati intraday
def example_intraday_candles():
    """Esempio per ottenere dati intraday"""
    print("\n=== Esempio candele intraday ===")
    
    # Usando il context manager
    with HistoricalData() as api:
        # Ottieni candele intraday per un simbolo
        symbol = "ENI.MI"  # Titolo di esempio
        days = 1  # Solo oggi
        period_minutes = 5  # Candele a 5 minuti
        
        print(f"Richiesta candele intraday {period_minutes} min per {symbol}, ultimo giorno")
        candles = api.get_intraday_candles(symbol, days, period_minutes)
        
        if candles.get("success", False):
            data = candles.get("data", [])
            print(f"Ricevute {len(data)} candele")
            
            if data:
                # Stampa le prime 5 candele
                print("\nPrime 5 candele:")
                for i, candle in enumerate(data[:5]):
                    print(f"Data/Ora: {candle.get('timestamp').strftime('%Y-%m-%d %H:%M')}, "
                          f"Apertura: {candle.get('open')}, "
                          f"Massimo: {candle.get('high')}, "
                          f"Minimo: {candle.get('low')}, "
                          f"Chiusura: {candle.get('close')}, "
                          f"Volume: {candle.get('volume')}")
                
                # Riepilogo dell'intervallo di date
                first_date = data[0].get('timestamp').strftime('%Y-%m-%d %H:%M')
                last_date = data[-1].get('timestamp').strftime('%Y-%m-%d %H:%M')
                print(f"\nIntervallo date: da {first_date} a {last_date}")
        else:
            print(f"Errore: {candles.get('error')}")

# Esempio 5: Ottenere dati tick by tick
def example_tick_data():
    """Esempio per ottenere dati tick by tick"""
    print("\n=== Esempio dati tick by tick ===")
    
    # Usando il context manager
    with HistoricalData() as api:
        # Ottieni dati tick by tick per un simbolo
        symbol = "ENI.MI"  # Titolo di esempio
        days = 1  # Solo oggi
        
        print(f"Richiesta dati tick by tick per {symbol}, ultimo giorno")
        ticks = api.get_intraday_ticks(symbol, days)
        
        if ticks.get("success", False):
            data = ticks.get("data", [])
            print(f"Ricevuti {len(data)} tick")
            
            if data:
                # Stampa i primi 5 tick
                print("\nPrimi 5 tick:")
                for i, tick in enumerate(data[:5]):
                    print(f"Data/Ora: {tick.get('timestamp').strftime('%Y-%m-%d %H:%M:%S')}, "
                          f"Prezzo: {tick.get('price')}, "
                          f"Quantità: {tick.get('quantity')}")
                
                # Riepilogo dell'intervallo di date
                first_date = data[0].get('timestamp').strftime('%Y-%m-%d %H:%M:%S')
                last_date = data[-1].get('timestamp').strftime('%Y-%m-%d %H:%M:%S')
                print(f"\nIntervallo date: da {first_date} a {last_date}")
        else:
            print(f"Errore: {ticks.get('error')}")

# Esempio 6: Specificare un intervallo di date
def example_date_range():
    """Esempio per ottenere dati in un intervallo di date specifico"""
    print("\n=== Esempio intervallo di date ===")
    
    # Usando il context manager
    with HistoricalData() as api:
        # Ottieni candele in un intervallo di date specifico
        symbol = "ENI.MI"  # Titolo di esempio
        
        # Definisci l'intervallo di date
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=7)  # Una settimana fa
        
        # Candele a 1 ora
        period_seconds = 3600  # 1 ora
        
        print(f"Richiesta candele per {symbol} dal {start_date.strftime('%Y-%m-%d')} al {end_date.strftime('%Y-%m-%d')}")
        candles = api.get_candle_data_range(symbol, start_date, end_date, period_seconds)
        
        if candles.get("success", False):
            data = candles.get("data", [])
            print(f"Ricevute {len(data)} candele")
            
            if data:
                # Stampa le prime 5 candele
                print("\nPrime 5 candele:")
                for i, candle in enumerate(data[:5]):
                    print(f"Data/Ora: {candle.get('timestamp').strftime('%Y-%m-%d %H:%M')}, "
                          f"Apertura: {candle.get('open')}, "
                          f"Chiusura: {candle.get('close')}")
                
                # Riepilogo dell'intervallo di date
                first_date = data[0].get('timestamp').strftime('%Y-%m-%d %H:%M')
                last_date = data[-1].get('timestamp').strftime('%Y-%m-%d %H:%M')
                print(f"\nIntervallo date: da {first_date} a {last_date}")
        else:
            print(f"Errore: {candles.get('error')}")

# Esempio 7: Impostazioni volume after-hours
def example_afterhours_volume():
    """Esempio per impostare le opzioni di volume after-hours"""
    print("\n=== Esempio impostazioni volume after-hours ===")
    
    # Usando il context manager
    with HistoricalData() as api:
        # Ottieni l'impostazione corrente
        print("Ottengo l'impostazione corrente volume after-hours...")
        response = api.set_volume_afterhours()
        print(f"Impostazione attuale: {api.volume_afterhours_setting}")
        
        # Cambia l'impostazione a solo volumi continuous
        print("\nCambio l'impostazione a solo volumi continuous (CNT)...")
        response = api.set_volume_afterhours("CNT")
        print(f"Nuova impostazione: {api.volume_afterhours_setting}")
        
        # Ottieni dati con questa impostazione
        symbol = "ENI.MI"
        print(f"\nOttengo candele giornaliere per {symbol} con impostazione CNT...")
        candles_cnt = api.get_daily_candles(symbol, 1)
        
        if candles_cnt.get("success", False) and candles_cnt.get("data"):
            candle = candles_cnt.get("data")[0]
            print(f"Volume con impostazione CNT: {candle.get('volume')}")
        
        # Cambia l'impostazione a volumi after-hours
        print("\nCambio l'impostazione a volumi after-hours (AH)...")
        response = api.set_volume_afterhours("AH")
        print(f"Nuova impostazione: {api.volume_afterhours_setting}")
        
        # Ottieni dati con questa impostazione
        print(f"\nOttengo candele giornaliere per {symbol} con impostazione AH...")
        candles_ah = api.get_daily_candles(symbol, 1)
        
        if candles_ah.get("success", False) and candles_ah.get("data"):
            candle = candles_ah.get("data")[0]
            print(f"Volume con impostazione AH: {candle.get('volume')}")
        
        # Ripristina l'impostazione predefinita
        print("\nRipristino l'impostazione predefinita (CNT+AH)...")
        response = api.set_volume_afterhours("CNT+AH")
        print(f"Impostazione ripristinata: {api.volume_afterhours_setting}")

# Esempio 8: Utilizzare l'iteratore per dati storici estesi
def example_candles_iterator():
    """Esempio di utilizzo dell'iteratore per ottenere dati storici estesi"""
    print("\n=== Esempio iteratore per dati storici estesi ===")
    
    # Usando il context manager
    with HistoricalData() as api:
        # Ottieni candele giornaliere per un lungo periodo
        symbol = "ENI.MI"  # Titolo di esempio
        period_seconds = 86400  # Giornaliero
        chunk_days = 100  # Dimensione del chunk
        
        print(f"Richiesta di candele giornaliere per {symbol} usando l'iteratore (a blocchi di {chunk_days} giorni)")
        
        # Lista per raccogliere tutti i dati
        all_candles = []
        
        # Utilizza l'iteratore per ottenere i dati in blocchi
        for i, chunk in enumerate(api.get_candles_iterator(symbol, period_seconds, chunk_days)):
            if chunk.get("success", False):
                data = chunk.get("data", [])
                all_candles.extend(data)
                
                # Stampa informazioni sul chunk
                if data:
                    first_date = data[0].get('timestamp').strftime('%Y-%m-%d')
                    last_date = data[-1].get('timestamp').strftime('%Y-%m-%d')
                    print(f"Chunk {i+1}: {len(data)} candele, da {first_date} a {last_date}")
                
                # Limitiamo a 3 iterazioni per questo esempio
                if i >= 2:
                    print("Limitato a 3 blocchi per questo esempio")
                    break
            else:
                print(f"Errore durante il recupero del chunk {i+1}: {chunk.get('error')}")
                break
        
        print(f"\nTotale candele recuperate: {len(all_candles)}")
        
        if all_candles:
            # Stampa il range di date complessivo
            first_date = all_candles[0].get('timestamp').strftime('%Y-%m-%d')
            last_date = all_candles[-1].get('timestamp').strftime('%Y-%m-%d')
            print(f"Range di date completo: da {first_date} a {last_date}")

# Esempio 9: Convertire i dati in un DataFrame pandas e visualizzarli
def example_pandas_visualization():
    """Esempio di conversione dei dati in Pandas DataFrame e visualizzazione"""
    print("\n=== Esempio conversione in Pandas e visualizzazione ===")
    
    try:
        # Importiamo pandas per la gestione dei dati
        import pandas as pd
        import matplotlib.pyplot as plt
        
        # Usando il context manager
        with HistoricalData() as api:
            # Ottieni candele giornaliere
            symbol = "ENI.MI"  # Titolo di esempio
            days = 60  # Ultimi 60 giorni
            
            print(f"Richiesta candele giornaliere per {symbol}, ultimi {days} giorni")
            candles = api.get_daily_candles(symbol, days)
            
            if candles.get("success", False):
                data = candles.get("data", [])
                
                if data:
                    # Converti i dati in un DataFrame pandas
                    print("Conversione dati in pandas DataFrame...")
                    df = pd.DataFrame(data)
                    
                    # Imposta la colonna timestamp come indice
                    df.set_index('timestamp', inplace=True)
                    
                    # Mostra le prime righe del DataFrame
                    print("\nPrime righe del DataFrame:")
                    print(df.head())
                    
                    # Esempio di analisi statistica dei dati
                    print("\nStatistiche di riepilogo:")
                    print(df[['open', 'high', 'low', 'close', 'volume']].describe())
                    
                    # Calcolo dei rendimenti giornalieri
                    df['returns'] = df['close'].pct_change() * 100
                    
                    print("\nRendimenti giornalieri (%):")
                    print(df['returns'].describe())
                    
                    print(f"\nRendimento totale nel periodo: {df['returns'].sum():.2f}%")
                    
                    # Esempio di output grafico (commentato in quanto non può essere visualizzato in questo contesto)
                    print("\nIn un'applicazione reale, qui si potrebbe visualizzare un grafico delle candele.")
                    """
                    # Visualizza il grafico delle candele
                    plt.figure(figsize=(12, 6))
                    plt.plot(df.index, df['close'], label='Prezzo di chiusura')
                    plt.title(f'Andamento {symbol} ultimi {days} giorni')
                    plt.xlabel('Data')
                    plt.ylabel('Prezzo')
                    plt.legend()
                    plt.grid(True)
                    plt.tight_layout()
                    plt.show()
                    """
            else:
                print(f"Errore: {candles.get('error')}")
    
    except ImportError:
        print("Questo esempio richiede i moduli pandas e matplotlib.")
        print("Installali con: pip install pandas matplotlib")

if __name__ == "__main__":
    try:
        print("Directa API - Esempi di Dati Storici")
        print("====================================")
        
        # Esegui tutti gli esempi
        example_connection()
        example_context_manager()
        example_daily_candles()
        example_intraday_candles()
        example_tick_data()
        example_date_range()
        example_afterhours_volume()
        example_candles_iterator()
        example_pandas_visualization()
        
    except Exception as e:
        print(f"Errore durante l'esecuzione degli esempi: {str(e)}") 