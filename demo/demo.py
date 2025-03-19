# python demo.py
# see coredumps in /tmp/cores/

import os
import socket
import time
import subprocess


# hardcoded
nginx_bin = "../objs/nginx"
conf_file = "demo.conf"
host = "127.0.0.1"
error_log_path = '/tmp/nginx/error.log'
http_port = 8080
smtp_port = 2525
pop3_port = 1111

def get_nginx_worker_pid():
    try:
        output = subprocess.check_output(["ps", "aux"]).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print("Error executing ps aux:", e)
        return None

    for line in output.splitlines():
        if "nginx: worker process" in line:
            # Split the line into columns (the PID is the second column)
            columns = line.split()
            if len(columns) >= 2:
                return int(columns[1])
    return None

def start_nginx(config_file):
    absolute_config_path = os.path.abspath(config_file) 
    command = f"{nginx_bin} -c {absolute_config_path}"
    ret = os.system(command)
    if ret != 0:
        raise RuntimeError(f"[!] Failed to start NGINX with config file: {config_file}")
    print(f"[+] NGINX started with config file: {config_file}")


def send_request(request, verbose=False):
    if not request:
        raise RuntimeError("[!] Error: Request file is empty.")
    
    port = 0
    # rather simplistic and overfit logic
    if b'HTTP' in request:
        port = http_port
    elif b'USER' in request:
        port = pop3_port
    else:
        port = smtp_port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((host, port))
        except socket.error as e:
            raise RuntimeError(f"[!] Error connecting to server: {e}")

        sock.sendall(request)

        response = sock.recv(4096).decode('utf-8')
        if verbose:
            print("[+] Response from server:\n" + response)


def list_blob_files(directory="."):
    return [f for f in os.listdir(directory) if f.endswith('.blob') and os.path.isfile(os.path.join(directory, f))]


def run_triggers():
    blob_files = list_blob_files()
    worker_pid = -1
    prev_pid = -1
    for blob_file in blob_files:
        print(f'[+] Running trigger {blob_file} ' + 20 * '=')
        try:
            # record the PID of the Nginx worker (these could be used to analyse the resulting error.log file)
            prev_pid = get_nginx_worker_pid()
            print(f'[*] Nginx worker PID = {prev_pid}')
            with open(blob_file, "rb") as file:
                request = file.read()
                send_request(request, verbose=False)
            time.sleep(1) # allow some time
            worker_pid = get_nginx_worker_pid()
            if worker_pid != prev_pid:
                print(f'[+] Nginx worker process crashed!')
            else:
                print(f"[!] Nginx worker process didn't crash")
        except FileNotFoundError:
            raise RuntimeError(f"[!] Error: Request file '{blob_file}' not found.")


def main():
    try:
        os.remove(error_log_path)
        with open(error_log_path, 'w') as fp:
            pass
        start_nginx(config_file=conf_file)

        # Wait for NGINX to fully start
        time.sleep(2)

        run_triggers()
    finally:
        os.system(f"{nginx_bin} -s stop")
        print("NGINX stopped")

if __name__ == "__main__":
    main()
