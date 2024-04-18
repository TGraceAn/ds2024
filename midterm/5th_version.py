import os
import socket
import random
import redis
import logging
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Redis server configuration
redis_hosts = os.getenv("REDIS_HOSTS", "127.0.0.1:6379").split(",")

# Round-robin load balancing algorithm
def handle_request_round_robin(next_server_index):
    if not redis_hosts:
        return None, next_server_index
    redis_server = redis_hosts[next_server_index]
    next_server_index = (next_server_index + 1) % len(redis_hosts)
    return redis_server, next_server_index

# Least connections load balancing algorithm
def handle_request_least_connections(next_server_index):
    if not redis_hosts:
        return None, next_server_index
    redis_server = min(redis_hosts, key=lambda host: get_connection_count(host))
    return redis_server, next_server_index

# Dictionary to store the connection counts for each Redis server
connection_counts = {}

# Function to get the number of active connections for a Redis server
def get_connection_count(redis_server):
    if redis_server in connection_counts:
        return connection_counts[redis_server]
    else:
        return 0

# Function to update the connection count for a Redis server
def update_connection_count(redis_server, increment):
    if redis_server in connection_counts:
        connection_counts[redis_server] += increment
    else:
        connection_counts[redis_server] = 1 if increment > 0 else 0

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
        # Choose a Redis server
        redis_server, next_server_index = handle_request_least_connections(next_server_index)
        if not redis_server:
            logging.error("No Redis servers available, unable to forward request")
            conn.sendall(b'Error: No Redis servers available.')
            conn.close()
            return

        logging.info(f'[{threading.current_thread().name}] Forwarding request to Redis server: {redis_server}')

        # Update the connection count for the Redis server
        update_connection_count(redis_server, 1)

        # Forward the request to the Redis server
        try:
            r = redis.Redis(host=redis_server.split(":")[0], port=int(redis_server.split(":")[1]), socket_timeout=5)
            response = r.get(conn.recv(1024))
            if response:
                conn.sendall(response)
            else:
                conn.sendall(b'Error: Key not found.')
        except redis.exceptions.RedisError as e:
            logging.error(f'[{threading.current_thread().name}] Error forwarding request to Redis server: {e}')
            conn.sendall(b'Error: Could not connect to Redis server.')
            conn.close()
            update_connection_count(redis_server, -1)
            return

        logging.info(f'[{threading.current_thread().name}] Sent response to {addr}')

        # Wait for the client to disconnect
        conn.settimeout(60)  # Timeout after 60 seconds of inactivity
        try:
            data = conn.recv(1)
            if not data:
                update_connection_count(redis_server, -1)
                logging.info(f'[{threading.current_thread().name}] Client {addr} disconnected')
        except socket.timeout:
            update_connection_count(redis_server, -1)
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