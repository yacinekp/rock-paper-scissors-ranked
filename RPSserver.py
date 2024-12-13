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
tournaments = {}

rank_pts_req = {
    'D' : 0,
    'C' : 150,
    'B' : 500,
    'A' : 1200
}

server_running = True

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

def get_win_streak(username):
    cur.execute("SELECT win_streak FROM players WHERE username = %s;", (username,))
    WS = cur.fetchone()
    return WS[0]

def update_rank_points(cur, username, new_points):
    cur.execute("UPDATE players SET rank_points = %s WHERE username = %s;", (new_points, username))
    conn.commit()

def determine_winner(curr, P1, Choice1, P2, Choice2):
    rank1 = get_rank_points(cur, P1)
    rank2 = get_rank_points(cur, P2)

    WS_P1 = get_win_streak(P1)
    WS_P2 = get_win_streak(P2)

    if Choice1 == Choice2:
        return "Draw!", "Draw!"
    elif ((Choice1 == "rock" and Choice2 == "scissors") or 
          (Choice1 == "paper" and Choice2 == "rock") or 
          (Choice1 == "scissors" and Choice2 == "paper")):
        updated_rank1 = int( rank1 + 10  + (0.8 * WS_P1))
        cur.execute("UPDATE players SET win_streak = %s WHERE username = %s;", (WS_P1 +1 ,P1))
        conn.commit()
        if( rank2 > 0):
            updated_rank2 = rank2 - 5
        else :
            updated_rank2 = 0
        cur.execute("UPDATE players SET win_streak = 0 WHERE username = %s;", (P2,))
        conn.commit()
        result = f"Player {P1} wins! win streak : {WS_P1}"
        
    else:
        updated_rank2 = int( rank2 + 10  + (0.8 * WS_P2))
        cur.execute("UPDATE players SET win_streak = %s WHERE username = %s;", (WS_P2 +1 ,P2))
        conn.commit()
        if (rank1 > 0):
            updated_rank1 = rank1 - 5
        else:
            updated_rank1 = 0
        cur.execute("UPDATE players SET win_streak = 0 WHERE username = %s;", (P1,))
        conn.commit()
        result = f"Player {P2} wins! win streak :{WS_P2}"

    update_rank_points(cur, P1, updated_rank1)
    update_rank_points(cur, P2, updated_rank2)

    # Send personalized result to each player
    P1_message = f"{result} \n Your new rank: {updated_rank1} points."
    P2_message = f"{result} \n Your new rank: {updated_rank2} points."

    return P1_message, P2_message

def handle_players(client1, username1, client2, username2):
    client1.send(f"Your opponent : {username2}".encode('ascii'))
    client2.send(f"Your opponent : {username1}".encode('ascii'))
    try:
        while True:
            try:
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
            except OSError as e:
                print(f"Error during communication: {e}")
                break

            resultP1, resultP2 = determine_winner(cur,username1, choice1, username2, choice2)

            try:
                client1.send(resultP1.encode('ascii'))
            except OSError as e:
                print(f"Error sending data to {username1}: {e}")
                break 

            try:
                client2.send(resultP2.encode('ascii'))
            except OSError as e:
                print(f"Error sending data to {username2}: {e}")
                break  

    finally:
        client1.close()
        client2.close()

def handle_client(client):
    global waiting_players
    global all_connected
    all_connected.append(client)
    username = client.recv(1024).decode('ascii').strip()
    check_player(username)
    
    #Make sure no players try to use the same username
    if any(player[1] == username for player in waiting_players):
        client.send("This username is already in use. Please try again.".encode('ascii'))
        client.close()
        return
    
    game_mode = client.recv(1024).decode('ascii').strip()

    if game_mode == 'normal':
        waiting_players.append((client, username))
        print(f"{username} has entered normal mode.")

        # matchmaking 2 players from the lounge
        if len(waiting_players) >= 2:
            random.shuffle(waiting_players)  # randomizing the matchmaking
            (player1, username1) = waiting_players.pop(0)
            (player2, username2) = waiting_players.pop(0)

            game_thread = threading.Thread(target=handle_players, args=(player1, username1, player2, username2))
            game_thread.start()
    elif game_mode == 'tournament':
        #recieving player join or create tournament
        action = client.recv(1024).decode('ascii').strip()
        if action == 'create':
            # Receive tournament passwd
            password = client.recv(1024).decode('ascii').strip()

            #recieve nb of players set for the tournament
            try:
                nb_players = int(client.recv(1024).decode('ascii').strip())
            except ValueError:
                client.send("Invalid number of players.".encode('ascii'))
                return
            
            if username in tournaments:
                client.send("You already created a tournament.".encode('ascii'))
            else:
                tournaments[username] = {'password': password, 'players': [(client, username)], 'nb_players': nb_players}
                client.send("Tournament created. Waiting for players...".encode('ascii'))
                print(f"Tournament created by {username}.")
        elif action == 'join':
            password = client.recv(1024).decode('ascii').strip()

            # Find the tournament by password
            found_tournament = None
            for host, info in tournaments.items():
                if info['password'] == password:
                    found_tournament = host
                    break
            if found_tournament:
                tournaments[found_tournament]['players'].append((client, username))
                client.send("Successfully joined the tournament.".encode('ascii'))
                print(f"{username} joined {found_tournament}'s tournament.")
                
                # Check if nb players is reached
                if len(tournaments[found_tournament]['players']) == tournaments[found_tournament]['nb_players']:
                    players = tournaments[found_tournament]['players']
                    random.shuffle(players)
                    while len(players) >= 2:
                        (player1, username1) = players.pop(0)
                        (player2, username2) = players.pop(0)
                        game_thread = threading.Thread(target=handle_players, args=(player1, username1, player2, username2))
                        game_thread.start()
                    del tournaments[found_tournament]  # Tournament completed, remove it
            else:
                client.send("Invalid tournament password.".encode('ascii'))

def signal_handler(sig, frame):
    global server_running

    print("\nShutting down the server...")

    shutdown_message = "Server was shut down"
    server_running = False
    for client in all_connected[:]:
        try:
            client.sendall(shutdown_message.encode('ascii'))
            client.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            print(f"Error notifying client of shutdown: {e}")
        finally:
            try:
                client.close()  # Close the socket
            except Exception as e:
                print(f"Error closing client: {e}")
            all_connected.remove(client)

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

    while server_running:
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
