import socket
import struct
import threading
import time
from termcolor import colored  # Import termcolor for colored output

# Constants for message protocol and communication
MAGIC_COOKIE = 0xabcddcba  # Unique identifier for valid messages
OFFER_MESSAGE_TYPE = 0x2  # Indicates an offer message to clients
REQUEST_MESSAGE_TYPE = 0x3  # Indicates a request message from clients
PAYLOAD_MESSAGE_TYPE = 0x4  # Indicates a data payload message
UDP_PORT = 14117  # Port for broadcasting offer messages
TCP_PORT = 65432  # Port for TCP connections
BUFFER_SIZE = 1024  # Size of data chunks

def send_offers():
    """
    Continuously send UDP offer messages to clients.

    This function broadcasts a message containing the server's UDP and TCP port
    to notify clients that the server is available for communication.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        offer_message = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, UDP_PORT, TCP_PORT)
        while True:
            udp_socket.sendto(offer_message, ('<broadcast>', UDP_PORT))
            print(colored("Offer message sent via broadcast", "green"))
            time.sleep(1)

def handle_tcp_client(connection, client_address):
    """
    Handle a TCP client request.

    This function processes a client's request for a file transfer over TCP,
    sends the requested data, and calculates the transfer speed.

    Args:
        connection (socket): The TCP connection to the client.
        client_address (tuple): The client's address (IP, port).
    """
    try:
        print(colored(f"Handling TCP connection from {client_address}", "green"))
        file_size = int(connection.recv(BUFFER_SIZE).decode().strip())
        print(colored(f"TCP client requested file of size: {file_size} bytes", "green"))
        data = b'X' * BUFFER_SIZE
        bytes_sent = 0
        start_time = time.time()
        while bytes_sent < file_size:
            connection.send(data)
            bytes_sent += len(data)
        end_time = time.time()
        speed = (bytes_sent / (end_time - start_time)) * 8  # Convert to bits/second
        print(colored(f"Sent {bytes_sent} bytes over TCP to {client_address} at {speed:.2f} bits/second", "green"))
    except Exception as e:
        print(colored(f"Error handling TCP client {client_address}: {e}", "red"))
    finally:
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        connection.close()
        print(colored(f"Connection with {client_address} closed", "green"))

def handle_udp_client(client_address, file_size):
    """
    Handle a UDP client request.

    This function sends the requested file data in chunks over UDP
    and calculates the transfer speed.

    Args:
        client_address (tuple): The client's address (IP, port).
        file_size (int): The size of the file to send in bytes.
    """
    try:
        print(colored(f"Handling UDP client from {client_address} requesting file of size: {file_size}", "green"))
        total_segments = file_size // BUFFER_SIZE
        bytes_sent = 0
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            for segment_num in range(total_segments):
                payload = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, total_segments, segment_num)
                payload += b'X' * (BUFFER_SIZE - len(payload))
                udp_socket.sendto(payload, client_address)
                bytes_sent += len(payload)
                print(colored(f"Sent segment {segment_num + 1}/{total_segments} to {client_address}", "green"))
        end_time = time.time()
        speed = (bytes_sent / (end_time - start_time)) * 8  # Convert to bits/second
        print(colored(f"Sent {bytes_sent} bytes over UDP to {client_address} at {speed:.2f} bits/second", "green"))
    except Exception as e:
        print(colored(f"Error handling UDP client {client_address}: {e}", "red"))

def start_tcp_server():
    """
    Start the TCP server to handle client connections.

    The server listens for incoming TCP connections and starts a new thread
    to handle each client.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_socket.bind(('172.20.10.3', TCP_PORT))  # Listen on all interfaces
        tcp_socket.listen()
        print(colored(f"TCP server listening on port {TCP_PORT}", "green"))
        while True:
            try:
                connection, client_address = tcp_socket.accept()
                threading.Thread(target=handle_tcp_client, args=(connection, client_address)).start()
            except Exception as e:
                print(colored(f"Error accepting TCP connection: {e}", "red"))

def start_udp_server():
    """
    Start the UDP server to handle client requests.

    The server listens for incoming UDP requests and starts a new thread
    to handle each client.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('172.20.10.3', UDP_PORT))  # Listen on all interfaces
        print(colored(f"UDP server listening on port {UDP_PORT}", "green"))
        while True:
            try:
                data, client_address = udp_socket.recvfrom(BUFFER_SIZE)
                if len(data) >= 13:
                    cookie, message_type, file_size = struct.unpack('!IBQ', data[:13])
                    if cookie == MAGIC_COOKIE and message_type == REQUEST_MESSAGE_TYPE:
                        threading.Thread(target=handle_udp_client, args=(client_address, file_size)).start()
            except Exception as e:
                print(colored(f"Error in UDP server: {e}", "red"))

def start_server():
    """
    Start the server to handle TCP and UDP requests.

    This function initializes the server by starting threads for broadcasting
    offer messages, handling TCP connections, and handling UDP requests.
    """
    print(colored("Server started, listening on all interfaces", "green"))
    threading.Thread(target=send_offers, daemon=True).start()
    threading.Thread(target=start_tcp_server, daemon=True).start()
    start_udp_server()  # Start the UDP server in the main thread

if __name__ == '__main__':
    start_server()
