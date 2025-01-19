import socket
import struct
import threading
import time
from termcolor import colored  # Import termcolor for colored output
# Constants used for message identification and communication
MAGIC_COOKIE = 0xabcddcba  # Unique identifier for valid messages
OFFER_MESSAGE_TYPE = 0x2  # Indicates an offer message from the server
REQUEST_MESSAGE_TYPE = 0x3  # Indicates a client request message
PAYLOAD_MESSAGE_TYPE = 0x4  # Indicates a data payload message
UDP_PORT = 14117  # Default UDP port for communication
TCP_PORT = 65432  # Default TCP port for communication
BUFFER_SIZE = 1024  # Size of data chunks for sending/receiving

def listen_for_offers():
    """
    Listen for server offers broadcasted via UDP.

    This function continuously listens for UDP messages on a specified port.
    Once an offer message with the correct structure and MAGIC_COOKIE is received,
    it extracts and returns the server's IP address, TCP port, and UDP port.

    Returns:
        tuple: A tuple containing the server's IP address (str), TCP port (int), and UDP port (int).
    """
    print(colored("Client started, listening for offer requests...", "green"))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow multiple binds to the same port
        udp_socket.bind(('', UDP_PORT))  # Bind to the specified UDP port for listening
        while True:
            try:
                # Receive data from the server
                message, address = udp_socket.recvfrom(BUFFER_SIZE)
                if len(message) >= 9:
                    # Unpack the message and validate its contents
                    cookie, message_type, udp_port, tcp_port = struct.unpack('!IBHH', message[:9])
                    if cookie == MAGIC_COOKIE and message_type == OFFER_MESSAGE_TYPE:
                        print(colored(f"Received offer from {address[0]} on TCP port {tcp_port}, UDP port {udp_port}", "green"))
                        return address[0], tcp_port, udp_port
            except Exception as e:
                print(colored(f"Error receiving offer: {e}", "red"))

def tcp_transfer(server_ip, tcp_port, file_size):
    """
    Perform a TCP transfer with the server.

    This function connects to the server over TCP, sends a request for a file
    of the specified size, and measures the time and speed of the transfer.

    Args:
        server_ip (str): The IP address of the server.
        tcp_port (int): The TCP port to connect to on the server.
        file_size (int): The size of the file to request (in bytes).
    """
    start_time = time.time()  # Record the start time of the transfer
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, tcp_port))  # Connect to the server
            tcp_socket.sendall(f"{file_size}\n".encode())  # Send the file size request
            received = 0
            while received < file_size:
                # Receive data in chunks until the requested file size is reached
                data = tcp_socket.recv(BUFFER_SIZE)
                received += len(data)
        end_time = time.time()  # Record the end time of the transfer
        speed = (received / (end_time - start_time)) * 8  # Calculate speed in bits/second
        print(colored(f"TCP transfer finished, total time: {end_time - start_time:.2f} seconds, speed: {speed:.2f} bits/second", "green"))
    except Exception as e:
        print(colored(f"Error during TCP transfer: {e}", "red"))

def udp_transfer(server_ip, udp_port, file_size):
    """
    Perform a UDP transfer with the server.

    This function sends a request to the server's UDP port for a file of the
    specified size and measures the time, speed, and success rate of the transfer.

    Args:
        server_ip (str): The IP address of the server.
        udp_port (int): The UDP port to connect to on the server.
        file_size (int): The size of the file to request (in bytes).
    """
    total_received = 0  # Total bytes received from the server
    total_segments = file_size // BUFFER_SIZE  # Total expected segments
    received_segments = 0  # Count of successfully received segments

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            # Send a request to the server for the specified file size
            udp_socket.sendto(struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size), (server_ip, udp_port))
            print(colored(f"UDP request sent to {server_ip}:{udp_port} for file size {file_size} bytes.", "green"))
            start_time = time.time()  # Record the start time of the transfer
            while time.time() - start_time < 1:  # Continue receiving until timeout
                try:
                    udp_socket.settimeout(1)  # Set timeout for receiving packets
                    data, _ = udp_socket.recvfrom(BUFFER_SIZE)
                    if len(data) >= 20:  # Ensure the data contains the payload structure
                        received_segments += 1
                        total_received += len(data) - 20  # Exclude header size from payload
                except socket.timeout:
                    break

        end_time = time.time()  # Record the end time of the transfer
        success_rate = (received_segments / total_segments) * 100 if total_segments > 0 else 0  # Calculate success rate
        speed = (total_received / (end_time - start_time)) * 8 if end_time > start_time else 0  # Speed in bits/second
        print(colored(f"UDP transfer finished, total time: {end_time - start_time:.2f} seconds, speed: {speed:.2f} bits/second, percentage of packets received successfully: {success_rate:.2f}%", "green"))
    except Exception as e:
        print(colored(f"Error during UDP transfer: {e}", "red"))

def start_client():
    """
    Start the client application.

    This function prompts the user for the file size, number of TCP connections,
    and number of UDP connections. It listens for server offers and starts the
    requested file transfers using separate threads for each connection.
    """
    file_size = int(input("Enter file size in bytes: "))  # Get file size from user
    tcp_connections = int(input("Enter number of TCP connections: "))  # Get number of TCP connections
    udp_connections = int(input("Enter number of UDP connections: "))  # Get number of UDP connections

    server_ip, tcp_port, udp_port = listen_for_offers()  # Wait for server offer

    # Start TCP and UDP transfers in separate threads
    threads = []
    for i in range(1, tcp_connections + 1):
        t = threading.Thread(target=tcp_transfer, args=(server_ip, tcp_port, file_size))
        t.start()
        threads.append(t)
        print(colored(f"TCP transfer #{i} started", "green"))

    for i in range(1, udp_connections + 1):
        t = threading.Thread(target=udp_transfer, args=(server_ip, udp_port, file_size))
        t.start()
        threads.append(t)
        print(colored(f"UDP transfer #{i} started", "green"))

    # Wait for all threads to complete
    for t in threads:
        t.join()
    print(colored("All transfers complete, listening to offer requests...", "green"))

if __name__ == '__main__':
    start_client()