
# python test.py <cp_folder>
# see coredumps in /tmp/cores/

import os
import socket
import time

nginx_bin = "objs/nginx"

def start_nginx(config_file):
    """Start NGINX with a custom configuration file."""
    command = f"{nginx_bin} -c {config_file}"
    ret = os.system(command)
    if ret != 0:
        raise RuntimeError(f"Failed to start NGINX with config file: {config_file}")
    print(f"NGINX started with config file: {config_file}")

def send_request(file_path, host, port):
    """Send an HTTP request to NGINX."""
    # Read the request data from the file
    try:
        with open(file_path, "r") as file:
            request = file.read()
    except FileNotFoundError:
        raise RuntimeError(f"Error: Request file '{file_path}' not found.")

    if not request:
        raise RuntimeError("Error: Request file is empty.")

    # Create a socket and connect to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((host, port))
        except socket.error as e:
            raise RuntimeError(f"Error connecting to server: {e}")

        # Send the HTTP request
        sock.sendall(request.encode('utf-8'))

        # Receive and print the response
        response = sock.recv(4096).decode('utf-8')
        print("Response from server:\n" + response)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Start NGINX and send a request.")
    parser.add_argument("cp_folder", help="Path to the test folder")
    parser.add_argument("request_file", default="request.txt", help="Filename of the request")

    args = parser.parse_args()

    cp_folder = os.path.abspath(args.cp_folder)
    conf_file = os.path.join(cp_folder, "test.conf")
    data_file = os.path.join(cp_folder, args.request_file)

    try:
        # Start NGINX with the custom configuration
        start_nginx(config_file=conf_file)

        # Wait for NGINX to fully start
        time.sleep(2)

        # Send the request to NGINX
        send_request(data_file, "127.0.0.1", 8080)

    finally:
        # Stop NGINX after testing
        os.system(f"{nginx_bin} -s stop")
        print("NGINX stopped")

if __name__ == "__main__":
    main()
