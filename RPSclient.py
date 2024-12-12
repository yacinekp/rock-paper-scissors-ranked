import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 11037))

pseudo = input("Enter your username: ").strip()
client.sendall(pseudo.encode('ascii'))
try:
    while True:

        choice = input("Enter paper, rock, or scissors (or type 'quit' or q to exit): ").strip().lower()

        if choice == "quit" or choice == 'q':
            break

        try:
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
        except socket.timeout:
            print("Waiting for server response...")
            continue 
        
        print(response)

except (ConnectionError, OSError):
    print("Connection was closed by the server.")
finally:
    client.close()