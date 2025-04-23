"""
Error codes and messages for Directa Trading API
"""

ERROR_CODES = {
    "0": "ERR_UNKNOWN - Errore generico",
    "1000": "ERR_MAX_SUBSCRIPTION_OVERFLOW - Limite massimo di titoli sottoscritti raggiunto",
    "1001": "ERR_ALREADY_SUBSCRIBED - Titolo richiesto già sottoscritto",
    "1002": "ERR_EMPTY_LIST - Nessun titolo inviato nel comando",
    "1003": "ERR_UNKNOWN_COMMAND - Comando sconosciuto",
    "1004": "ERR_COMMAND_NOT_EXECUTED - Comando non eseguito",
    "1005": "ERR_NOT_SUBSCRIBED - Errore sottoscrizione",
    "1006": "ERR_DARWIN_STOP - Chiusura Darwin in corso",
    "1007": "ERR_BAD_SUBSCRIPTION - Errore titolo inesistente",
    "1008": "ERR_DATA_UNAVAILABLE - Flusso richiesto non disponibile",
    "1009": "ERR_TRADING_CMD_INCOMPLETE - Comando trading non completo",
    "1010": "ERR_TRADING_CMD_ERROR - Comando trading errato",
    "1011": "ERR_TRADING_UNAVAILABLE - Trading non abilitato",
    "1012": "ERR_TRADING_REQUEST_ERROR - Errore immissione ordine",
    "1013": "ERR_HISTORYCALL_PARAMS - Errore numero paramentri nel comando",
    "1015": "ERR_HISTORYCALL_RANGE_INTRADAY - Errore range per chiamate intraday",
    "1016": "ERR_HISTORYCALL_DAY_OR_RANGE - Errore nei giorni o nel range date nel comando inviato",
    "1018": "ERR_EMPTY_STOCKLIST - Nessuno strumento nel portafoglio",
    "1019": "ERR_EMPTY_ORDERLIST - Nessun ordine presente",
    "1020": "ERR_DUPLICATED_ID - ID Ordine duplicato",
    "1021": "ERR_INVALID_ORDER_STATE - Stato ordine incongruente con l'operazione richiesta",
    "1024": "ERR_TRADING_PUSH_DISCONNECTED - Segnala la disconnessione del trading",
    "1025": "ERR_TRADING_PUSH_RECONNECTION_OK - Segnale di riconnessione",
    "1026": "ERR_TRADING_PUSH_RELOAD - Segnala il reload del trading",
    "1027": "ERR_DATAFEED_DISCONNECTED - Segnala la disconessione del datafeed",
    "1028": "ERR_DATAFEED_RELOAD - Segnala il reload del datafeed",
    "1030": "ERR_MARKET_UNAVAILABLE - Mercato non abilitato per il ticker richiesto",
    "1031": "CONTATTO_NON_ATTIVO - Contatto verso il nostro server di trading scaduto, necessario riavviare l'applicazione",
    "1032": "DATAFEED NON ABILITATO - Quotazioni non abilitate"
}

ORDER_STATUS_CODES = {
    "2000": "In negoziazione",
    "2001": "Errore immissione",
    "2002": "In negoziazione dopo conferma ricevuta",
    "2003": "Eseguito",
    "2004": "Revocato",
    "2005": "In attesa di conferma",
    "2006": "Modificato"
}

def get_error_message(error_code: str) -> str:
    """
    Get the error message for an error code
    
    Args:
        error_code: The error code
        
    Returns:
        The error message or a generic message if not found
    """
    if error_code in ERROR_CODES:
        return ERROR_CODES[error_code]
    return f"Codice errore sconosciuto: {error_code}"

def get_order_status(status_code: str) -> str:
    """
    Get the order status description for a status code
    
    Args:
        status_code: The status code
        
    Returns:
        The status description or a generic message if not found
    """
    if status_code in ORDER_STATUS_CODES:
        return ORDER_STATUS_CODES[status_code]
    return f"Stato ordine sconosciuto: {status_code}"

def is_error_response(response: str) -> bool:
    """
    Check if a response is an error response
    
    Args:
        response: The API response
        
    Returns:
        True if it's an error response, False otherwise
    """
    return response.strip().startswith("ERR;") or response.strip()[0:4].isdigit() and response.strip()[4] == ":"

def parse_error_response(response: str) -> dict:
    """
    Parse an error response into a JSON-compatible dictionary
    
    Args:
        response: The error response string
        
    Returns:
        A dictionary with error information in JSON format
    """
    # Handle the format ERR;CMD;ERROR_CODE
    if response.strip().startswith("ERR;"):
        parts = response.strip().split(';')
        if len(parts) >= 3:
            error_code = parts[2]
            return {
                "success": False,
                "error_code": error_code,
                "error_message": get_error_message(error_code),
                "raw_response": response
            }
    
    # Handle the format ERROR_CODE:ERROR_MESSAGE
    elif response.strip()[0:4].isdigit() and response.strip()[4] == ":":
        error_code = response.strip()[0:4]
        return {
            "success": False,
            "error_code": error_code,
            "error_message": get_error_message(error_code),
            "raw_response": response
        }
    
    # Generic error format
    return {
        "success": False,
        "error_code": "unknown",
        "error_message": "Formato di errore sconosciuto",
        "raw_response": response
    } 