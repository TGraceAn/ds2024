import socket
import random
import requests

# List of Reddit server addresses
reddit_servers = ['https://www.reddit.com/r/Music/', 'https://www.reddit.com/r/musictheory/', 'https://www.reddit.com/r/red_velvet/']

# Load balancer server address and port
lb_address = '127.0.0.1'
lb_port = 8080

# Create a socket for the load balancer
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

sock.bind((lb_address, lb_port))
sock.listen(5)

# Round-robin (most basic) load balancing algorithm
next_server_index = 0

def handle_request_round_robin(next_server_index):
    reddit_server = reddit_servers[next_server_index]
    next_server_index = (next_server_index + 1) % len(reddit_servers)
    return reddit_server, next_server_index

# Least connections load balancing algorithm
def handle_request_least_connections(next_server_index):
    reddit_server = min(reddit_servers, key=lambda server: server.get_connection_count())
    return reddit_server, next_server_index


print(f'Load balancer listening on {lb_address}:{lb_port}')

while True:
    # Wait for a connection
    conn, addr = sock.accept()
    print(f'Received connection from {addr}')

    # Choose a Reddit server
    reddit_server, next_server_index = handle_request_round_robin(next_server_index)


    print(f'Forwarding request to Reddit server: {reddit_server}')

    # Forward the request to the Reddit server
    try:
        response = requests.get(reddit_server)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f'Error forwarding request to Reddit server: {e}')
        conn.sendall(b'Error: Could not connect to Reddit server.')
        conn.close()
        continue

    # Send the response back to the client
    conn.sendall(response.content)
    conn.close()