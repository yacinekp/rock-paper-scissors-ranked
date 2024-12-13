import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 11037))

pseudo = input("Enter your username: ").strip()
client.sendall(pseudo.encode('ascii'))

mode = input("Choose mode: 'normal' or 'tournament': ").strip().lower()

while mode not in ['normal', 'tournament']:
    mode = input("Invalid mode. Please choose 'normal' or 'tournament': ").strip().lower()
client.sendall(mode.encode('ascii'))

if mode == 'tournament':
    action = input("Do you want to 'create' a tournament or 'join' an existing one? ").strip().lower()
    while action not in ['create', 'join']:
        action = input("Invalid action. Please choose 'create' or 'join': ").strip().lower()
    client.sendall(action.encode('ascii'))

    if action == 'create':
        tournament_password = input("Enter a password for your tournament: ").strip()
        client.sendall(tournament_password.encode('ascii'))

        while True:
            try:
                tourn_nbr = int(input("Enter the number of players (must be at least 4): "))
                if tourn_nbr < 4:
                    print("Number of players must be at least 4.")
                    continue
                break
            except ValueError:
                print("Please enter a valid number.")
        client.sendall(str(tourn_nbr).encode('ascii'))
    elif action == 'join':
        tournament_password = input("Enter the tournament password: ").strip()
        client.sendall(tournament_password.encode('ascii'))
        print("joining tournament...")

print("Waiting for opponent matching...")
matched_confirmation = client.recv(1024).decode('ascii') 
if not matched_confirmation:
    print("server closed connection")
else:
    print(matched_confirmation)

try:
    while True:

        choice = input("Enter paper, rock, or scissors (or type 'quit' or q to exit): ").strip().lower()

        if choice == "quit" or choice == 'q':
            break
        if choice not in ["paper", "rock", "scissors"]:
            print("Invalid choice. Please try again.")
            continue
        client.sendall(choice.encode())
        response = client.recv(1024).decode()
        if not response:
                print("Server has shut down.")
                break
        if response == "Server was shut down":
            print("Server was shut down. Disconnecting...")
            break 
        print(response)

except (ConnectionError, OSError):
    print("Connection was closed by the server.")
finally:
    client.close()