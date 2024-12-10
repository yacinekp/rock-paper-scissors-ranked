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

cur = conn.cursor()
server = None
all_connected = []
waiting_players = [] # make sure to not allow 2 players to use the same username at the same time

def check_player(username):
    cur.execute("SELECT * FROM players WHERE username=%s", (username,))
    player = cur.fetchone()

    if player is None:
        # add player to db  if not exist
        cur.execute("INSERT INTO players (username) VALUES (%s)", (username,))
        conn.commit()

def update_player_rank(username, points):
    cur.execute("UPDATE players SET rank_points = rank_points + %s WHERE username = %s", (points, username))
    conn.commit()

def get_player_rank(username):
    cur.execute("SELECT rank_points FROM players WHERE username = %s", (username,))
    return cur.fetchone()[0] 


def get_rank_points(cur, username):
    cur.execute("SELECT rank_points FROM players WHERE username = %s;", (username,))
    result = cur.fetchone()
    if result is None:
        return 0
    return result[0]

def update_rank_points(cur, username, new_points):
    cur.execute("UPDATE players SET rank_points = %s WHERE username = %s;", (new_points, username))
    conn.commit()

def determine_winner(curr, P1, Choice1, P2, Choice2):
    rank1 = get_rank_points(cur, P1)
    rank2 = get_rank_points(cur, P2)

    if Choice1 == Choice2:
        return "Draw!", "Draw!"
    elif ((Choice1 == "rock" and Choice2 == "scissors") or 
          (Choice1 == "paper" and Choice2 == "rock") or 
          (Choice1 == "scissors" and Choice2 == "paper")):
        updated_rank1 = rank1 + 10  
        if( rank2 > 0):
            updated_rank2 = rank2 - 5
        else :
            updated_rank2 = 0
        result = f"Player {P1} wins!"
        
    else:
        updated_rank2 = rank2 + 10  
        if (rank1 > 0):
            updated_rank1 = rank1 - 5
        else:
            updated_rank1 = 0
        result = f"Player {P2} wins!"

    update_rank_points(cur, P1, updated_rank1)
    update_rank_points(cur, P2, updated_rank2)

    # Send personalized result to each player
    P1_message = f"{result} \n Your new rank: {updated_rank1} points."
    P2_message = f"{result} \n Your new rank: {updated_rank2} points."

    return P1_message, P2_message

def handle_players(client1, username1, client2, username2):
    try:
        while True:
            # recieve p1's choice
            choice1 = client1.recv(1024).decode('ascii')
            if not choice1:
                print(f"Connection from {username1} lost")
                return
            
            # recieve p2's choice
            choice2 = client2.recv(1024).decode('ascii')
            if not choice2:
                print(f"Connection from {username2} lost")
                return
                
            resultP1, resultP2 = determine_winner(cur,username1, choice1, username2, choice2)

            client1.send(resultP1.encode('ascii'))
            client2.send(resultP2.encode('ascii'))

    finally:
        client1.close()
        client2.close()

def handle_client(client):
    global waiting_players
    global all_connected
    all_connected.append(client)
    username = client.recv(1024).decode('ascii').strip()
    #check_player(username)
    
    #Make sure no players try to use the same username
    if any(player[1] == username for player in waiting_players):
        client.send("This username is already in use. Please try again.".encode('ascii'))
        client.close()
        return
    
    waiting_players.append((client, username))
    print(f"Connection from {username} has been established.")

    # matchmaking 2 players from the lounge
    if len(waiting_players) >= 2:
        (player1, username1) = waiting_players.pop(0)
        (player2, username2) = waiting_players.pop(0)
        game_thread = threading.Thread(target=handle_players, args=(player1, username1, player2, username2))
        game_thread.start()

def signal_handler(sig, frame):
    print("\nShutting down the server...")
    for client in all_connected:
        try:
            client.shutdown(socket.SHUT_RDWR)
            client.close()
        except Exception as e:
            print(f"Error closing client: {e}")

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
            client, _ = server.accept()
            client_thread = threading.Thread(target=handle_client, args=(client,))
            client_thread.start()
         
        except socket.timeout:
            continue 
        except OSError:
            break

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    start_server()
