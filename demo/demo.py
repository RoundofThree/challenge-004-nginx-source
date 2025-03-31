# python demo.py
# see coredumps in /tmp/cores/

import os
import socket
import time
import subprocess

# ugly sleep times too
# hardcoded
conf_file = "demo.conf"
host = "127.0.0.1"
http_port = 8080
smtp_port = 2525
pop3_port = 1111

# 3 configurations: aarch64, aarch64c, aarch64c+Q0
configurations = ["aarch64", "aarch64c", "aarch64c+Q0"]
nginx_aarch64c_bin = "../objs_aarch64c/nginx"
nginx_aarch64_bin = "../objs_aarch64/nginx"
aarch64_error_log_path = '/tmp/nginx_aarch64/error.log'
aarch64c_error_log_path = '/tmp/nginx_aarch64c/error.log'

def get_nginx_worker_pid():
    try:
        output = subprocess.check_output(["ps", "aux"]).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print("Error executing ps aux:", e)
        return None

    for line in output.splitlines():
        # very hackish and prone to error
        if "nginx: worker" in line:
            # Split the line into columns (the PID is the second column)
            columns = line.split()
            if len(columns) >= 2:
                return int(columns[1])
    return None

def start_nginx(config_file, configuration):
    absolute_config_path = os.path.abspath(config_file)
    if configuration == "aarch64":
        command = f"{nginx_aarch64_bin} -c {absolute_config_path}"
    elif configuration == "aarch64c":
        command = f"{nginx_aarch64c_bin} -c {absolute_config_path}"
    elif configuration == "aarch64c+Q0":
        command = f"_RUNTIME_REVOCATION_EVERY_FREE_ENABLE=1 {nginx_aarch64c_bin} -c {absolute_config_path}"
    else:
        raise Exception(f"Unknown configuration {configuration}")
    ret = os.system(command)
    if ret != 0:
        raise RuntimeError(f"[!] Failed to start NGINX with config file: {config_file}")
    # print(f"[+] NGINX started with config file: {config_file}")


def stop_nginx(configuration):
    if configuration == "aarch64":
        os.system(f"{nginx_aarch64_bin} -s stop")
    else:
        os.system(f"{nginx_aarch64c_bin} -s stop")
    # print("[+] NGINX stopped")


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
        response = sock.recv(4096)
        if verbose:
            print("[+] Response from server:\n" + response)


def list_blob_files(directory="."):
    return [f for f in os.listdir(directory) if f.endswith('.blob') and os.path.isfile(os.path.join(directory, f))]


# run in three configurations
def run_triggers():
    blob_files = list_blob_files()
    worker_pid = -1
    prev_pid = -1
    for blob_file in blob_files:
        request = None
        try:
            with open(blob_file, "rb") as file:
                request = file.read()
        except FileNotFoundError:
            raise RuntimeError(f"[!] Error: Request file '{blob_file}' not found.")
        
        print(f'[+] Running trigger {blob_file} ' + 20 * '=')

        for configuration in configurations:
            try:
                print(f'[*] Configuration {configuration}')
                start_nginx(conf_file, configuration)
                time.sleep(2)
                prev_pid = get_nginx_worker_pid()
                print(f'[*] Nginx worker PID = {prev_pid}')
                send_request(request, verbose=False)
                time.sleep(1) # allow some time
                worker_pid = get_nginx_worker_pid()
                if worker_pid != prev_pid:
                    print(f'[+] Nginx worker process crashed!')
                else:
                    print(f"[!] Nginx worker process didn't crash")
            finally:
                stop_nginx(configuration)
                time.sleep(1)


def main():
    try:
        os.remove(aarch64_error_log_path)
    except:
        pass
    try:
        os.remove(aarch64c_error_log_path)
    except:
        pass
    with open(aarch64_error_log_path, 'w') as fp:
        pass
    with open(aarch64c_error_log_path, 'w') as fp:
        pass
    run_triggers()

if __name__ == "__main__":
    main()
