#!/usr/bin/env python3
"""
Script di test che simula telnet per diagnosticare problemi di connessione con l'API Directa
"""

import socket
import sys
import time

def main():
    # Parametri di connessione
    HOST = "127.0.0.1"
    PORT = 10002
    BUFFER_SIZE = 4096
    
    print(f"Connessione a {HOST}:{PORT}...")
    
    try:
        # Crea socket esattamente come telnet
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        print("Connesso!")
        
        # Attendi 1 secondo per eventuali messaggi di benvenuto
        time.sleep(1)
        
        # Prova a ricevere dati (potrebbe non esserci nulla)
        s.setblocking(0)  # Non-blocking per non rimanere bloccati
        try:
            initial_data = s.recv(BUFFER_SIZE)
            if initial_data:
                print(f"Dati iniziali ricevuti:\n{initial_data.decode('utf-8')}")
        except (socket.error, BlockingIOError):
            print("Nessun dato iniziale ricevuto.")
        
        # Torna in modalità bloccante
        s.setblocking(1)
        
        # Invia comando DARWINSTATUS
        print("\nInvio comando DARWINSTATUS...")
        s.sendall(b"DARWINSTATUS\n")
        
        # Leggi la risposta
        response = s.recv(BUFFER_SIZE)
        print(f"Risposta:\n{response.decode('utf-8')}")
        
        # Invia alcuni comandi base per verificare
        print("\nInvio comando INFOACCOUNT...")
        s.sendall(b"INFOACCOUNT\n")
        response = s.recv(BUFFER_SIZE)
        print(f"Risposta:\n{response.decode('utf-8')}")
        
        print("\nInvio comando INFOSTOCKS...")
        s.sendall(b"INFOSTOCKS\n")
        response = s.recv(BUFFER_SIZE)
        print(f"Risposta:\n{response.decode('utf-8')}")
        
        print("\nInvio comando ORDERLIST...")
        s.sendall(b"ORDERLIST\n")
        response = s.recv(BUFFER_SIZE)
        print(f"Risposta:\n{response.decode('utf-8')}")
        
        # Chiudi la connessione
        s.close()
        print("\nConnessione chiusa.")
        
    except socket.error as e:
        print(f"Errore socket: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 