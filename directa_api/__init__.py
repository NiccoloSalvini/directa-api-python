#!/usr/bin/env python3
"""
Directa API

Una libreria Python per interagire con le API di Directa Trading,
consentendo di effettuare operazioni di trading e recuperare dati storici.
"""

from directa_api.trading import DirectaTrading
from directa_api.historical import HistoricalData
from directa_api.connection import TradingConnection, HistoricalConnection
from directa_api.simulation import TradingSimulation

__version__ = '0.2.0'
__all__ = ['DirectaTrading', 'HistoricalData', 'TradingConnection', 
           'HistoricalConnection', 'TradingSimulation'] 