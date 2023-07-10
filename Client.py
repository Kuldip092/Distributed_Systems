
import socket
import threading
import time
import random

HOST = 'localhost'
PORT = 12345
B_PORT = 9999

random_port = random.choice([PORT, B_PORT])

if random_port == B_PORT:
    B_PORT = PORT
    PORT = random_port
    
    
def receive_messages(sock):
    while True:
        try:
            data = sock.recv(1024).decode()
            if not data:
                print("1Disconnected from server.")
                break
            print(data)
        except ConnectionResetError:
            print("Disconnected from server.")
            print("try to reconnect again")
            break

def connect_to_server(s, username):
    s.sendall(username.encode())
    recv_thread = threading.Thread(target=receive_messages, args=(s,))
    recv_thread.start()

    try:
        while True:
            message = input('')
            if message == 'help':
                print('Codewords and their functionalities:')
                print('clients  => Displays the usernames of all online clients.')
                print('all      => Displays the username of all the clients')
                print('help     => to see codewords and their functionalities')
            elif message == 'clients':
                s.sendall(message.encode())
            elif message == 'disconnect':
                s.sendall(message.encode())
                break
            elif message == 'exit':
                s.sendall(message.encode())
                break
            else:
                s.sendall(message.encode())
    except KeyboardInterrupt:
        s.sendall('disconnect'.encode())
        print('Disconnected from server.')
    finally:
        s.close()

def start_client():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                username = input('Enter your username: ')
                connect_to_server(s, username)
        except ConnectionError:
            print('Primary server is down. Connecting to backup server...')
            time.sleep(5) # wait for 5 seconds before connecting to the backup server
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((HOST, B_PORT))
                    username = input('Enter your username: ')
                    connect_to_server(s, username)
            except ConnectionError:
                print('Backup server is down. Retrying in 10 seconds...')
                time.sleep(10) # wait for 10 seconds before retrying
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    start_client()
