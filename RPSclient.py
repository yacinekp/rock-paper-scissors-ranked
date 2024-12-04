import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 11037))

while True:
    choice = input("Enter paper, rock, or scissors (or type 'quit' or q to exit): ").strip().lower()

    if choice == "quit" or choice == 'q':
        break

    if choice not in ["paper", "rock", "scissors"]:
        print("Invalid choice. Please try again.")
        continue

    client.sendall(choice.encode())
    response = client.recv(1024).decode()
    print(response)

client.close()