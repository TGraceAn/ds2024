import os
import socket
import random
import requests
from kubernetes import client, config

# Kubernetes API client configuration
kubernetes_host = os.getenv("KUBERNETES_HOST", "https://kubernetes.default.svc")
kubernetes_token = os.getenv("KUBERNETES_TOKEN")

configuration = client.Configuration()
configuration.host = kubernetes_host
configuration.api_key = {"authorization": f"Bearer {kubernetes_token}"}
configuration.verify_ssl = False

client.Configuration.set_default(configuration)
v1 = client.CoreV1Api()

# Function to get the list of Reddit server pods

def get_reddit_servers():
    reddit_servers = ['https://www.reddit.com/r/Music/', 'https://www.reddit.com/r/musictheory/', 'https://www.reddit.com/r/red_velvet/']
    return reddit_servers

# Round-robin load balancing algorithm
def handle_request_round_robin(next_server_index):
    reddit_servers = get_reddit_servers()
    reddit_server = reddit_servers[next_server_index]
    next_server_index = (next_server_index + 1) % len(reddit_servers)
    return reddit_server, next_server_index

# Least connections load balancing algorithm
def handle_request_least_connections(next_server_index):
    reddit_servers = get_reddit_servers()
    reddit_server = min(reddit_servers, key=lambda server: get_connection_count(server))
    return reddit_server, next_server_index

# Dictionary to store the connection counts for each Reddit server
connection_counts = {}

# Function to get the number of active connections for a Reddit server
def get_connection_count(reddit_server):
    if reddit_server in connection_counts:
        return connection_counts[reddit_server]
    else:
        return 0

# Function to update the connection count for a Reddit server
def update_connection_count(reddit_server, increment):
    if reddit_server in connection_counts:
        connection_counts[reddit_server] += increment
    else:
        connection_counts[reddit_server] = 1 if increment > 0 else 0

# Load balancer server address and port
lb_address = os.getenv("LB_ADDRESS", "127.0.0.1") #localhost address
lb_port = int(os.getenv("LB_PORT", 8080))

# Create a socket for the load balancer
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((lb_address, lb_port))
sock.listen(5)

# Next server index for round-robin
next_server_index = 0

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
    print(f'Sent response to {addr}')

    get_connection_count(reddit_server)
    update_connection_count(reddit_server, 1)

    print(connection_counts)


    # Wait for the client to disconnect
    conn.settimeout(10)  # Timeout after 60 seconds of inactivity
    try:
        data = conn.recv(1)
        if not data:
            update_connection_count(reddit_server, -1)
            print('client disconnected')
            conn.close()
    except socket.timeout:
        update_connection_count(reddit_server, -1)
        print('client disconnected')
        conn.close()
    
    # finally:
    #     # conn.close()