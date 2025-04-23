#!/usr/bin/env python3
"""
Directa API - Modulo di simulazione

Questo modulo contiene la classe TradingSimulation che implementa
la simulazione di trading per testare strategie senza utilizzare denaro reale.
"""

import logging
import datetime
import random
import uuid
from typing import Optional, Dict, List, Union, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class TradingSimulation:
    """
    Classe per simulare le operazioni di trading senza utilizzare denaro reale.
    
    Questa classe implementa una simulazione completa di trading, inclusi:
    - Gestione del portafoglio simulato
    - Creazione e gestione di ordini
    - Esecuzione di ordini
    - Aggiornamento del saldo e dell'equity
    """
    
    def __init__(self):
        """Inizializza lo stato della simulazione"""
        self.logger = logging.getLogger("TradingSimulation")
        self.logger.info("Inizializzazione modalità simulazione")
        
        # Stato della simulazione
        self.portfolio = []  # Posizioni aperte
        self.orders = {}     # Ordini attivi (order_id: order_data)
        self.account = {     # Informazioni account
            "account_code": "SIM1234",
            "liquidity": 10000.0,
            "equity": 10000.0
        }
        
        # Storico delle operazioni
        self.transactions = []  # Storico delle transazioni
        
        self.logger.warning("MODALITÀ SIMULAZIONE ATTIVA - Nessuna operazione reale sarà eseguita")
    
    def reset_state(self) -> Dict[str, Any]:
        """
        Reimposta lo stato della simulazione ai valori predefiniti
        
        Returns:
            Dict con conferma di reset
        """
        self.__init__()
        self.logger.info("Stato simulazione reimpostato")
        return {"success": True, "data": "Simulazione reimpostata"}
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Ottiene le informazioni dell'account simulato
        
        Returns:
            Dict con le informazioni dell'account
        """
        return {
            "success": True,
            "data": {
                "account_code": self.account["account_code"],
                "liquidity": self.account["liquidity"],
                "equity": self.account["equity"],
                "simulation": True
            }
        }
    
    def get_portfolio(self) -> Dict[str, Any]:
        """
        Ottiene il portafoglio simulato
        
        Returns:
            Dict con il portafoglio
        """
        return {
            "success": True,
            "data": {
                "stocks": self.portfolio,
                "simulation": True
            }
        }
    
    def add_position(self, symbol: str, quantity: int, price: float) -> bool:
        """
        Aggiunge una posizione al portafoglio simulato
        
        Args:
            symbol: Simbolo del titolo
            quantity: Quantità
            price: Prezzo medio
            
        Returns:
            bool: True se l'aggiunta è riuscita
        """
        # Cerca se il titolo è già nel portafoglio
        for position in self.portfolio:
            if position["symbol"] == symbol:
                # Aggiorna la posizione esistente
                current_qty = position["quantity"]
                current_avg = position["avg_price"]
                new_qty = current_qty + quantity
                
                # Calcola il nuovo prezzo medio
                if new_qty > 0:
                    position["avg_price"] = (current_qty * current_avg + quantity * price) / new_qty
                    position["quantity"] = new_qty
                else:
                    # Rimuovi la posizione se la quantità è 0 o negativa
                    self.portfolio.remove(position)
                
                self.logger.info(f"Posizione aggiornata: {symbol}, quantità: {new_qty}")
                return True
        
        # Se il titolo non esiste, aggiungilo
        if quantity > 0:
            self.portfolio.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": price
            })
            self.logger.info(f"Posizione aggiunta: {symbol}, quantità: {quantity}")
            return True
        
        return False
    
    def remove_position(self, symbol: str) -> bool:
        """
        Rimuove una posizione dal portafoglio simulato
        
        Args:
            symbol: Simbolo del titolo
            
        Returns:
            bool: True se la rimozione è riuscita
        """
        for position in self.portfolio:
            if position["symbol"] == symbol:
                self.portfolio.remove(position)
                self.logger.info(f"Posizione rimossa: {symbol}")
                return True
        
        self.logger.warning(f"Impossibile rimuovere posizione: {symbol} (non trovata)")
        return False
    
    def update_account(self, liquidity: Optional[float] = None, equity: Optional[float] = None) -> None:
        """
        Aggiorna i dati dell'account simulato
        
        Args:
            liquidity: Nuovo valore di liquidità (opzionale)
            equity: Nuovo valore di equity (opzionale)
        """
        if liquidity is not None:
            self.account["liquidity"] = liquidity
        
        if equity is not None:
            self.account["equity"] = equity
            
        self.logger.debug(f"Account aggiornato: liquidità {self.account['liquidity']}, equity {self.account['equity']}")
    
    def update_total_balance(self) -> None:
        """
        Aggiorna il valore totale dell'account in base al portafoglio
        """
        # Valore liquidità è già presente
        liquidity = self.account["liquidity"]
        
        # Calcola il valore del portafoglio
        portfolio_value = 0.0
        for position in self.portfolio:
            # In una simulazione reale, qui si utilizzerebbe il prezzo attuale
            # Per semplicità usiamo il prezzo medio
            portfolio_value += position["quantity"] * position["avg_price"]
        
        # Aggiorna l'equity
        self.account["equity"] = liquidity + portfolio_value
        self.logger.debug(f"Saldo totale aggiornato: {self.account['equity']}")
    
    def create_order(self, symbol: str, side: str, quantity: int, price: Optional[float] = None, 
                     order_type: str = "LIMIT") -> Dict[str, Any]:
        """
        Crea un ordine simulato
        
        Args:
            symbol: Simbolo del titolo
            side: Lato (BUY o SELL)
            quantity: Quantità
            price: Prezzo (per ordini limite)
            order_type: Tipo di ordine (LIMIT, MARKET, ecc.)
            
        Returns:
            Dict con i dati dell'ordine creato
        """
        # Genera un ID ordine univoco simulato
        order_id = f"SIM{uuid.uuid4().hex[:8].upper()}"
        
        # Timestamp corrente
        timestamp = datetime.datetime.now()
        
        # Crea l'oggetto ordine
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "filled_quantity": 0,
            "remaining_quantity": quantity,
            "price": price,
            "order_type": order_type,
            "status": "ACTIVE",
            "timestamp": timestamp,
            "simulation": True
        }
        
        # Aggiungi alla lista degli ordini
        self.orders[order_id] = order
        
        self.logger.info(f"Ordine creato: {order_id}, {side} {quantity} {symbol} @ {price}")
        
        # Formato risposta per compatibilità con l'API
        return {
            "success": True,
            "data": {
                "order_id": order_id,
                "status": "ACTIVE",
                "message": "Ordine creato in simulazione"
            }
        }
    
    def modify_order(self, order_id: str, price: float, signal_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Modifica un ordine simulato
        
        Args:
            order_id: ID dell'ordine
            price: Nuovo prezzo
            signal_price: Nuovo prezzo segnale (per ordini stop)
            
        Returns:
            Dict con il risultato della modifica
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            
            # Verifica che l'ordine sia attivo
            if order["status"] != "ACTIVE":
                return {
                    "success": False,
                    "error": f"Ordine {order_id} non è attivo (stato: {order['status']})"
                }
            
            # Aggiorna i prezzi
            old_price = order["price"]
            order["price"] = price
            
            if signal_price is not None and "signal_price" in order:
                order["signal_price"] = signal_price
            
            self.logger.info(f"Ordine {order_id} modificato: prezzo {old_price} -> {price}")
            
            return {
                "success": True,
                "data": {
                    "order_id": order_id,
                    "status": "ACTIVE",
                    "message": "Ordine modificato in simulazione"
                }
            }
        
        return {
            "success": False,
            "error": f"Ordine {order_id} non trovato"
        }
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancella un ordine simulato
        
        Args:
            order_id: ID dell'ordine
            
        Returns:
            Dict con il risultato della cancellazione
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            
            # Verifica che l'ordine sia attivo
            if order["status"] != "ACTIVE":
                return {
                    "success": False,
                    "error": f"Ordine {order_id} non è attivo (stato: {order['status']})"
                }
            
            # Aggiorna lo stato
            order["status"] = "CANCELLED"
            
            self.logger.info(f"Ordine {order_id} cancellato")
            
            return {
                "success": True,
                "data": {
                    "order_id": order_id,
                    "status": "CANCELLED",
                    "message": "Ordine cancellato in simulazione"
                }
            }
        
        return {
            "success": False,
            "error": f"Ordine {order_id} non trovato"
        }
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancella tutti gli ordini attivi, opzionalmente per un simbolo specifico
        
        Args:
            symbol: Simbolo specifico (opzionale)
            
        Returns:
            Dict con il risultato della cancellazione
        """
        cancelled = 0
        
        for order_id, order in list(self.orders.items()):
            if order["status"] == "ACTIVE":
                if symbol is None or order["symbol"] == symbol:
                    order["status"] = "CANCELLED"
                    cancelled += 1
        
        self.logger.info(f"Cancellati {cancelled} ordini{' per ' + symbol if symbol else ''}")
        
        return {
            "success": True,
            "data": {
                "cancelled_orders": cancelled,
                "message": f"Cancellati {cancelled} ordini in simulazione"
            }
        }
    
    def execute_order(self, order_id: str, fill_price: Optional[float] = None, 
                     quantity: Optional[int] = None) -> Dict[str, Any]:
        """
        Simula l'esecuzione di un ordine
        
        Args:
            order_id: ID dell'ordine
            fill_price: Prezzo di esecuzione (opzionale, se None usa il prezzo dell'ordine)
            quantity: Quantità da eseguire (opzionale, se None esegue tutto)
            
        Returns:
            Dict con il risultato dell'esecuzione
        """
        if order_id not in self.orders:
            return {
                "success": False,
                "error": f"Ordine {order_id} non trovato"
            }
        
        order = self.orders[order_id]
        
        # Verifica che l'ordine sia attivo
        if order["status"] != "ACTIVE":
            return {
                "success": False,
                "error": f"Ordine {order_id} non è attivo (stato: {order['status']})"
            }
        
        # Determina la quantità da eseguire
        remaining = order["remaining_quantity"]
        exec_quantity = min(remaining, quantity or remaining)
        
        if exec_quantity <= 0:
            return {
                "success": False,
                "error": f"Quantità non valida per l'esecuzione: {exec_quantity}"
            }
        
        # Determina il prezzo di esecuzione
        execution_price = fill_price if fill_price is not None else order["price"]
        
        # Calcola il valore della transazione
        transaction_value = exec_quantity * execution_price
        
        # Aggiorna lo stato dell'ordine
        order["filled_quantity"] += exec_quantity
        order["remaining_quantity"] -= exec_quantity
        
        # Se tutto eseguito, imposta lo stato a FILLED
        if order["remaining_quantity"] == 0:
            order["status"] = "FILLED"
        else:
            order["status"] = "PARTIALLY_FILLED"
        
        # Aggiorna il portafoglio
        side = order["side"]
        symbol = order["symbol"]
        
        if side == "BUY":
            # Sottrai la liquidità e aggiungi al portafoglio
            self.account["liquidity"] -= transaction_value
            self.add_position(symbol, exec_quantity, execution_price)
        else:  # SELL
            # Aggiungi alla liquidità e rimuovi dal portafoglio
            self.account["liquidity"] += transaction_value
            self.add_position(symbol, -exec_quantity, execution_price)
        
        # Aggiorna il saldo totale
        self.update_total_balance()
        
        # Aggiungi alla cronologia transazioni
        transaction = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": exec_quantity,
            "price": execution_price,
            "value": transaction_value,
            "timestamp": datetime.datetime.now(),
            "type": "EXECUTION"
        }
        self.transactions.append(transaction)
        
        self.logger.info(
            f"Ordine {order_id} eseguito: {side} {exec_quantity} {symbol} @ {execution_price} "
            f"(valore: {transaction_value})"
        )
        
        return {
            "success": True,
            "data": {
                "order_id": order_id,
                "status": order["status"],
                "filled_quantity": exec_quantity,
                "remaining_quantity": order["remaining_quantity"],
                "fill_price": execution_price,
                "value": transaction_value,
                "message": "Ordine eseguito in simulazione"
            }
        }
    
    def get_orders(self, symbol: Optional[str] = None, include_inactive: bool = False) -> Dict[str, Any]:
        """
        Ottiene la lista degli ordini simulati
        
        Args:
            symbol: Filtra per simbolo (opzionale)
            include_inactive: Includi ordini non attivi
            
        Returns:
            Dict con la lista degli ordini
        """
        filtered_orders = []
        
        for order_id, order in self.orders.items():
            # Filtra per simbolo se specificato
            if symbol is not None and order["symbol"] != symbol:
                continue
            
            # Filtra per stato se richiesto
            if not include_inactive and order["status"] != "ACTIVE":
                continue
            
            filtered_orders.append(order)
        
        return {
            "success": True,
            "data": {
                "orders": filtered_orders,
                "simulation": True
            }
        }
    
    def get_darwin_status(self) -> Dict[str, Any]:
        """
        Simula lo stato di Darwin (sempre connesso in simulazione)
        
        Returns:
            Dict con lo stato simulato
        """
        # Genera un tempo di connessione simulato
        current_time = datetime.datetime.now()
        
        return {
            "success": True,
            "data": {
                "connection_status": "CONN_OK",
                "application_status": "TRUE",
                "version": "SIMULATION 1.0",
                "simulation_mode": True,
                "connection_metrics": {
                    "connection_attempts": 1,
                    "last_connection_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "current_session_time": 3600,  # Simulato a 1 ora
                    "total_connected_time": 3600,
                    "connection_history_summary": "Simulazione (sempre connesso)"
                }
            }
        } 