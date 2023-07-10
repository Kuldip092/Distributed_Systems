import socket
import threading
import sqlite3
import datetime
import time


HOST = 'localhost'
PORT = 9999

clients = {}  # dictionary to store connected clients

# Create a connection to the local SQLite database
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Create a table to store the usernames and passwords if it does not exist
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT)''')

# Create a table to store offline messages
c.execute('''CREATE TABLE IF NOT EXISTS offline_messages
             (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, message TEXT, timestamp TEXT)''')

conn.commit()

def receive_messages(data):
    while True:
        message,recipient, port = data.split('|',2)
        if port == '12345':
            username, fmessage = message.split(':',1)
            if username in clients:
                clients[username].sendall(f'{recipient}: {fmessage}'.encode())  # send message to recipient
                break


def handle_client(conn, addr):
    # Create a new database connection and cursor
    db = sqlite3.connect('users.db')
    c = db.cursor()
    username = conn.recv(1024).decode()  # receive username from client

    if ':' in username:
        receive_messages(username)
        return
    
    conn.sendall("Are you a new user? (Y/N)".encode())
    response = conn.recv(1024).decode()

    if response.lower() == 'y':
        # register new user
            c.execute("SELECT password FROM users WHERE username=?", (username,))
            result = c.fetchone()
            if result:
                conn.sendall("Username already exists. Please try again with a different username.".encode())
                conn.sendall("you are disconnected".encode())
            else:
                conn.sendall("Enter a password:".encode())
                password = conn.recv(1024).decode()
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                db.commit()
                conn.sendall("You have been registered successfully!".encode())
                conn.sendall("You can now log in with your new credentials.".encode())
                
    elif response.lower() == 'n':
        # authenticate existing user
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        result = c.fetchone()
        if result is None:
            conn.sendall("User not found. Please try again with a different username or register as a new user.".encode())
            conn.sendall("you are disconnected".encode())
            # del clients[username]
            # conn.close()
            return
        else:
            while True:
                conn.sendall("Enter your password:".encode())
                password = conn.recv(1024).decode()
                if result[0] != password:
                    conn.sendall("Incorrect password. Please try again with a different password.".encode())
                else:
                    break
    else:
        conn.sendall("Invalid response. Please try again with 'Y' or 'N'.".encode())
        # conn.close()
        return

    clients[username] = conn  # add client to dictionary
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f'[{now}] {username} connected from {addr}')

    # Notify all other clients that a new client has joined
    for client_name, client_conn in clients.items():
        if client_name != username:
            client_conn.sendall(f'A new client {username} has joined the chat'.encode())

    # Check for offline messages and send them to the client
    c.execute("SELECT * FROM offline_messages WHERE recipient=?", (username,))
    offline_messages = c.fetchall()
    for message in offline_messages:
        sender = message[1]
        msg = message[3]
        message_time = message[4]
        conn.sendall(f'[{message_time}] {sender}: {msg}\n'.encode())
    
    # Delete offline messages from the table
    c.execute("DELETE FROM offline_messages WHERE recipient=?", (username,))
    db.commit()
    try:
        while True:
            data = conn.recv(1024).decode()  # receive message from client
            if not data:
                break

            if data == 'clients':  # check if the message is "clients"
                conn.sendall(str(list(clients.keys() - {username})).encode())  # send list of clients to client
            elif data == 'all':  # check if the message is "all"
                c.execute("SELECT username FROM users WHERE username!=?", (username,))
                result = c.fetchall()
                conn.sendall(str([row[0] for row in result]).encode())  # send list of clients to client
            elif data == 'disconnect':  # check if the message is "disconnect"
                print(f'{username} Disconnected from server.')
                del clients[username]  # remove client from dictionary
                break
            elif ':' in data:
                timestamp = time.time()
                timestamp_str = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                recipient, message = data.split(':', 1)  # extract recipient and message
                if recipient in clients:
                    clients[recipient].sendall(f'{username}: {message}'.encode())  # send message to recipient
                else:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s1:
                        s1.connect(('localhost', 12345))  # connect to other server
                        combined = f"{data}|{username}|{PORT}"
                        s1.sendall(combined.encode())  # send message
                    
                    # store the message in the database for the offline recipient
                    c.execute("INSERT INTO offline_messages (sender, recipient, message, timestamp) VALUES (?, ?, ?, ?)",
                              (username, recipient, message, timestamp_str))
                    db.commit()
            else:
                conn.sendall('Invalid message format. Please use "recipient:message" format.'.encode())  # Send error message to client

    except ConnectionResetError:
        del clients[username]  # remove client from dictionary
        print(f'{username} Disconnected from server.')

    for client_name, client_conn in clients.items():
        if client_name != username:
            client_conn.sendall(f'Client {username} has left.'.encode())

    conn.close()
    # Close the database connection
    db.close()


def start_server():
    print('Server is online')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server started on {HOST}:{PORT}')

        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

if __name__ == '__main__':
    start_server()
