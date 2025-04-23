#!/usr/bin/env python3
"""
Directa API - Esempio Combinato

Questo esempio mostra come utilizzare insieme l'API di trading e l'API per dati storici.
"""

import time
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from directa_api import DirectaTrading, HistoricalData

def trading_strategy_example():
    """
    Esempio di strategia di trading basata su dati storici.
    
    Questo esempio mostra come:
    1. Ottenere dati storici per un simbolo
    2. Analizzare i dati per identificare segnali di trading
    3. Eseguire operazioni di trading basate sui segnali
    """
    print("\nDirecta API - Esempio di Strategia Combinata")
    print("===========================================")
    
    # Simbolo su cui operare
    symbol = "ENI.MI"
    
    print(f"Analisi e trading su {symbol}")
    
    # Fase 1: Ottieni dati storici
    print("\n--- Fase 1: Recupero dati storici ---")
    with HistoricalData() as historical:
        print(f"Connessione all'API storica...")
        
        # Ottieni dati giornalieri degli ultimi 60 giorni
        days = 60
        print(f"Richiesta dati giornalieri per {symbol}, ultimi {days} giorni...")
        
        candles = historical.get_daily_candles(symbol, days)
        
        if not candles.get("success", False):
            print(f"Errore nel recupero dei dati: {candles.get('error')}")
            return
        
        data = candles.get("data", [])
        print(f"Ricevute {len(data)} candele giornaliere")
    
    # Fase 2: Analisi dei dati e generazione segnali
    print("\n--- Fase 2: Analisi e generazione segnali ---")
    
    if not data:
        print("Nessun dato disponibile per l'analisi")
        return
    
    # Convertiamo i dati in un DataFrame pandas per l'analisi
    df = pd.DataFrame(data)
    
    # Imposta la colonna timestamp come indice
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)  # Assicuriamoci che sia ordinato per data
    
    # Calcola alcune medie mobili semplici
    df['sma_10'] = df['close'].rolling(window=10).mean()  # Media mobile a 10 giorni
    df['sma_20'] = df['close'].rolling(window=20).mean()  # Media mobile a 20 giorni
    
    # Rimuovi le righe con valori NaN (dovuti al calcolo delle medie mobili)
    df = df.dropna()
    
    print("Dati elaborati:")
    print(df[['open', 'close', 'sma_10', 'sma_20']].tail())
    
    # Genera segnali: compra quando SMA10 > SMA20, vendi quando SMA10 < SMA20
    df['signal'] = 0
    df.loc[df['sma_10'] > df['sma_20'], 'signal'] = 1  # Segnale di acquisto
    df.loc[df['sma_10'] < df['sma_20'], 'signal'] = -1  # Segnale di vendita
    
    # Ottieni solo i cambi di segnale
    df['position'] = df['signal'].diff()
    
    # Visualizziamo gli ultimi segnali
    signals = df[df['position'] != 0].copy()
    print("\nUltimi segnali generati:")
    latest_signals = signals.tail(5)
    
    for idx, row in latest_signals.iterrows():
        signal_type = "ACQUISTO" if row['position'] > 0 else "VENDITA"
        print(f"Data: {idx.strftime('%Y-%m-%d')}, Segnale: {signal_type}, Prezzo: {row['close']}")
    
    # Fase 3: Esecuzione dei segnali tramite API di trading
    print("\n--- Fase 3: Esecuzione ordini ---")
    
    # Ottieni l'ultimo segnale
    if not latest_signals.empty:
        last_signal = latest_signals.iloc[-1]
        last_date = last_signal.name
        today = datetime.datetime.now().date()
        
        # Verifica se l'ultimo segnale è di oggi
        if last_date.date() == today:
            print(f"Segnale attivo per oggi: {'ACQUISTO' if last_signal['position'] > 0 else 'VENDITA'}")
            
            # Esegui l'ordine in simulazione
            with DirectaTrading(simulation_mode=True) as trading:
                print("Connessione all'API di trading (modalità simulazione)...")
                
                # Ottieni informazioni sull'account prima dell'operazione
                account_info = trading.get_account_info()
                if account_info.get("success", False):
                    liquidity = account_info.get("data", {}).get("liquidity", 0)
                    print(f"Liquidità disponibile: {liquidity}")
                
                # Ottieni il portafoglio
                portfolio = trading.get_portfolio()
                position_size = 0
                
                if portfolio.get("success", False):
                    # Cerca se abbiamo già una posizione sul titolo
                    for stock in portfolio.get("data", {}).get("stocks", []):
                        if stock.get("symbol") == symbol:
                            position_size = stock.get("quantity", 0)
                            print(f"Posizione attuale su {symbol}: {position_size} azioni")
                
                # Calcola la dimensione dell'ordine
                quantity = 10  # Semplice esempio con quantità fissa
                price = last_signal['close']
                
                print(f"Prezzo attuale: {price}")
                
                # Esegui l'ordine basato sul segnale
                if last_signal['position'] > 0:  # Segnale di acquisto
                    print(f"Esecuzione ordine di ACQUISTO: {quantity} {symbol} @ {price:.4f}")
                    
                    if position_size == 0:  # Se non abbiamo già una posizione
                        order = trading.buy_limit(symbol, quantity, price)
                        
                        if order.get("success", False):
                            order_id = order.get("data", {}).get("order_id")
                            print(f"Ordine di acquisto inviato con ID: {order_id}")
                            
                            # Simuliamo l'esecuzione dell'ordine
                            execution = trading.simulate_order_execution(order_id, fill_price=price)
                            
                            if execution.get("success", False):
                                print("Ordine eseguito con successo!")
                        else:
                            print(f"Errore ordine di acquisto: {order.get('error')}")
                    else:
                        print("Già in posizione, nessun ordine eseguito")
                        
                elif last_signal['position'] < 0:  # Segnale di vendita
                    print(f"Esecuzione ordine di VENDITA: {quantity} {symbol} @ {price:.4f}")
                    
                    if position_size > 0:  # Se abbiamo una posizione
                        sell_quantity = min(position_size, quantity)
                        order = trading.sell_limit(symbol, sell_quantity, price)
                        
                        if order.get("success", False):
                            order_id = order.get("data", {}).get("order_id")
                            print(f"Ordine di vendita inviato con ID: {order_id}")
                            
                            # Simuliamo l'esecuzione dell'ordine
                            execution = trading.simulate_order_execution(order_id, fill_price=price)
                            
                            if execution.get("success", False):
                                print("Ordine eseguito con successo!")
                        else:
                            print(f"Errore ordine di vendita: {order.get('error')}")
                    else:
                        print("Nessuna posizione da vendere")
                
                # Ottieni lo stato finale del portafoglio
                final_portfolio = trading.get_portfolio()
                if final_portfolio.get("success", False):
                    stocks = final_portfolio.get("data", {}).get("stocks", [])
                    print("\nPortafoglio finale:")
                    for stock in stocks:
                        print(f"Titolo: {stock.get('symbol')}, Quantità: {stock.get('quantity')}, Prezzo medio: {stock.get('avg_price')}")
        else:
            print(f"Nessun segnale attivo per oggi. Ultimo segnale: {last_date.strftime('%Y-%m-%d')}")
    else:
        print("Nessun segnale generato dall'analisi")

def live_market_data_analysis():
    """
    Esempio di analisi combinata di dati storici e attuali.
    
    Questo esempio mostra come:
    1. Ottenere dati storici per un'analisi di base
    2. Interrogare l'API di trading per i dati di mercato attuali
    3. Combinare le informazioni per supportare decisioni di trading
    """
    print("\nDirecta API - Esempio di Analisi Live e Storica")
    print("=============================================")
    
    # Simbolo da analizzare
    symbol = "ENI.MI"
    
    print(f"Analisi combinata per {symbol}")
    
    try:
        # Fase 1: Ottieni dati storici per analisi contestuale
        print("\n--- Fase 1: Analisi storica ---")
        with HistoricalData() as historical:
            # Ottieni dati giornalieri degli ultimi 30 giorni
            days = 30
            candles = historical.get_daily_candles(symbol, days)
            
            if not candles.get("success", False):
                print(f"Errore nel recupero dei dati storici: {candles.get('error')}")
                return
            
            data = candles.get("data", [])
            print(f"Ricevute {len(data)} candele giornaliere")
            
            if data:
                # Calcoliamo alcune statistiche di base dai dati storici
                df = pd.DataFrame(data)
                prices = [d.get('close') for d in data]
                avg_price = sum(prices) / len(prices)
                max_price = max(prices)
                min_price = min(prices)
                
                print(f"Prezzo medio (30 giorni): {avg_price:.4f}")
                print(f"Prezzo massimo (30 giorni): {max_price:.4f}")
                print(f"Prezzo minimo (30 giorni): {min_price:.4f}")
                
                # Calcola alcuni livelli tecnici
                support_level = min_price * 0.98
                resistance_level = max_price * 1.02
                
                print(f"Livello di supporto stimato: {support_level:.4f}")
                print(f"Livello di resistenza stimato: {resistance_level:.4f}")
        
        # Fase 2: Ottieni dati attuali di mercato
        print("\n--- Fase 2: Dati di mercato attuali ---")
        with DirectaTrading(simulation_mode=True) as trading:
            # Ottieni il portafoglio per vedere se abbiamo posizioni aperte
            portfolio = trading.get_portfolio()
            
            position_size = 0
            position_avg_price = 0
            
            if portfolio.get("success", False):
                # Cerca se abbiamo una posizione sul titolo
                for stock in portfolio.get("data", {}).get("stocks", []):
                    if stock.get("symbol") == symbol:
                        position_size = stock.get("quantity", 0)
                        position_avg_price = stock.get("avg_price", 0)
                        print(f"Posizione attuale su {symbol}: {position_size} azioni, prezzo medio: {position_avg_price:.4f}")
            
            # Per questo esempio, simuliamo un prezzo attuale vicino all'ultimo prezzo storico
            current_price = prices[-1] * (1 + (0.01 * (1 - 2 * (time.time() % 2))))  # Simulazione di una fluttuazione
            print(f"Prezzo attuale simulato: {current_price:.4f}")
            
            # Fase 3: Analisi combinata
            print("\n--- Fase 3: Analisi combinata e decisioni ---")
            
            # Confrontiamo il prezzo attuale con i livelli tecnici
            if current_price <= support_level:
                print(f"ALERT: Prezzo ({current_price:.4f}) è al/sotto del livello di supporto ({support_level:.4f})")
                print("Considerare un possibile acquisto.")
                
                # Strategie potenziali
                target_price = current_price * 1.05  # Target di profitto a +5%
                stop_loss = current_price * 0.97     # Stop loss a -3%
                
                print(f"Target suggerito: {target_price:.4f} (+5%)")
                print(f"Stop loss suggerito: {stop_loss:.4f} (-3%)")
                
            elif current_price >= resistance_level:
                print(f"ALERT: Prezzo ({current_price:.4f}) è al/sopra del livello di resistenza ({resistance_level:.4f})")
                print("Considerare una possibile vendita.")
                
                # Strategie potenziali
                target_price = current_price * 0.95  # Target di profitto a -5% (short)
                stop_loss = current_price * 1.03     # Stop loss a +3%
                
                print(f"Target suggerito: {target_price:.4f} (-5%)")
                print(f"Stop loss suggerito: {stop_loss:.4f} (+3%)")
                
            else:
                print(f"Prezzo ({current_price:.4f}) è tra supporto ({support_level:.4f}) e resistenza ({resistance_level:.4f})")
                print("Mercato in range, considerare strategie di attesa o trading range-bound.")
            
            # Riepilogo finale
            print("\nRiepilogo analisi:")
            print(f"- Prezzo attuale: {current_price:.4f}")
            print(f"- Media 30 giorni: {avg_price:.4f}")
            print(f"- Posizione: {position_size} azioni a {position_avg_price:.4f}")
            
            # P&L simulato
            if position_size > 0:
                pl_pct = ((current_price / position_avg_price) - 1) * 100
                pl_abs = (current_price - position_avg_price) * position_size
                print(f"- P&L non realizzato: {pl_pct:.2f}% ({pl_abs:.2f})")
    
    except Exception as e:
        print(f"Errore durante l'analisi: {str(e)}")

if __name__ == "__main__":
    try:
        print("Directa API - Esempi Combinati")
        print("==============================")
        
        print("\nEsempio 1: Strategia di trading basata su dati storici")
        trading_strategy_example()
        
        print("\nEsempio 2: Analisi di mercato combinata (storica e attuale)")
        live_market_data_analysis()
        
    except Exception as e:
        print(f"Errore durante l'esecuzione degli esempi: {str(e)}") 