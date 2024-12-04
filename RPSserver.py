import socket
import threading
import random
import sys
import signal
import psycopg2

conn = psycopg2.connect(
    dbname="RPS_TP",
    user="postgres",
    password="bddrsql2024",
    host="localhost",
    port="5432"
)

server = None
waiting_players = []


def determine_winner(Choice1, Choice2):
    if Choice1 == Choice2:
        return "Draw!"
    elif ((Choice1 == "rock" and Choice2 == "scissors") or 
          (Choice1 == "paper" and Choice2 == "rock") or 
          (Choice1 == "scissors" and Choice2 == "paper")):
        return "Player1 wins!"
    else:
        return "Player2 wins!"

def handle_players(client1, client2):
    try:
        while True:
            # recieve p1's choice
            choice1 = client1.recv(1024).decode('ascii')
            if not choice1:
                return
            
            # recieve p2's choice
            choice2 = client2.recv(1024).decode('ascii')
            if not choice2:
                return
                
            result = determine_winner(choice1, choice2)

            client1.send(f'{result}'.encode('ascii'))
            client2.send(f'{result}'.encode('ascii'))

    finally:
        client1.close()
        client2.close()

def handle_client(client):
    global waiting_players
    waiting_players.append(client)

    # matchmaking 2 players from the lounge
    if len(waiting_players) >= 2:
        player1 = waiting_players.pop(0)
        player2 = waiting_players.pop(0)
        game_thread = threading.Thread(target=handle_players, args=(player1, player2))
        game_thread.start()

def signal_handler(sig, frame):
    print("\nShutting down the server...")
    if server:
        server.close()
    sys.exit(0)

def start_server():
    global server
    host = '127.0.0.1'
    port = 11037

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    server.settimeout(1) 
    print("server started! waiting for connections...")

    while True:
        try:
            client, address = server.accept()
            client_thread = threading.Thread(target=handle_client, args=(client,))
            client_thread.start()
            print(f"Connection from {address} has been established.")
        except socket.timeout:
            continue 
        except OSError:
            break

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    start_server()
