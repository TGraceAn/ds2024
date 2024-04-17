import os
import socket
import random
import requests
from kubernetes import client, config
import logging
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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
    try:
        pods = v1.list_pod_for_all_namespaces(watch=False)
        reddit_servers = []
        for pod in pods.items:
            if pod.metadata.name.startswith("reddit-server-"):
                reddit_servers.append(f"http://{pod.status.pod_ip}:8000")
        
        print(len(reddit_servers))
        return reddit_servers
    
    except Exception as e:
        logging.error(f"Error getting Reddit server pods: {e}")
        return []


# Round-robin load balancing algorithm
def handle_request_round_robin(next_server_index):
    reddit_servers = get_reddit_servers()
    if not reddit_servers:
        return None, next_server_index
    reddit_server = reddit_servers[next_server_index]
    next_server_index = (next_server_index + 1) % len(reddit_servers)
    return reddit_server, next_server_index

# Least connections load balancing algorithm
def handle_request_least_connections(next_server_index):
    reddit_servers = get_reddit_servers()
    if not reddit_servers:
        return None, next_server_index
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
lb_address = os.getenv("LB_ADDRESS", "127.0.0.1")
lb_port = int(os.getenv("LB_PORT", 8080))

# Create a socket for the load balancer
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((lb_address, lb_port))
sock.listen(5)

# Next server index for round-robin
next_server_index = 0

logging.info(f'Load balancer listening on {lb_address}:{lb_port}')

def handle_client(conn, addr, next_server_index):
    try:
        # Choose a Reddit server
        reddit_server, next_server_index = handle_request_least_connections(next_server_index)
        if not reddit_server:
            logging.error("No Reddit servers available, unable to forward request")
            conn.sendall(b'Error: No Reddit servers available.')
            conn.close()
            return

        logging.info(f'[{threading.current_thread().name}] Forwarding request to Reddit server: {reddit_server}')

        # Update the connection count for the Reddit server
        update_connection_count(reddit_server, 1)

        # Forward the request to the Reddit server
        try:
            response = requests.get(reddit_server)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f'[{threading.current_thread().name}] Error forwarding request to Reddit server: {e}')
            conn.sendall(b'Error: Could not connect to Reddit server.')
            conn.close()
            update_connection_count(reddit_server, -1)
            return

        # Send the response back to the client
        conn.sendall(response.content)
        logging.info(f'[{threading.current_thread().name}] Sent response to {addr}')

        # Wait for the client to disconnect
        conn.settimeout(60)  # Timeout after 60 seconds of inactivity
        try:
            data = conn.recv(1)
            if not data:
                update_connection_count(reddit_server, -1)
                logging.info(f'[{threading.current_thread().name}] Client {addr} disconnected')
        except socket.timeout:
            update_connection_count(reddit_server, -1)
            logging.info(f'[{threading.current_thread().name}] Client {addr} disconnected (timeout)')
        finally:
            conn.close()
    except Exception as e:
        logging.error(f'[{threading.current_thread().name}] Unexpected error: {e}')

while True:
    try:
        # Wait for a connection
        conn, addr = sock.accept()
        logging.info(f'Received connection from {addr}')
        threading.Thread(target=handle_client, args=(conn, addr, next_server_index), daemon=True).start()
    except Exception as e:
        logging.error(f'Unexpected error: {e}')