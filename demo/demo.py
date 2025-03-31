# python demo.py
# see coredumps in /tmp/cores/

import os
import socket
import time
import signal
import re
import subprocess
from tabulate import tabulate

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

# results. cpv number (where bcpv counts as 17+i) -> PID
aarch64_pids = {}
aarch64c_pids = {}
aarch64c_q0_pids = {}

table_headers = ["CPV", "aarch64", "aarch64c", "aarch64c+Q0"]
table_rows = []

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
        cpv_number = int(blob_file.split('cpv')[1].split('.blob')[0])
        if 'bcpv' in blob_file:
            cpv_number += 17 # hack
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
                # save the pid
                if configuration == "aarch64":
                    aarch64_pids[cpv_number] = prev_pid
                elif configuration == "aarch64c":
                    aarch64c_pids[cpv_number] = prev_pid
                else:
                    aarch64c_q0_pids[cpv_number] = prev_pid
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


def find_exit_signal(log_file, pid):
    pattern = re.compile(rf"\b{pid}\b exited on signal (\d+)")
    with open(log_file, 'r') as file:
        for line in file:
            match = pattern.search(line)
            if match:
                signal = match.group(1)
                return int(signal)
    return None


def get_signal_name(sig_num):
    for name in dir(signal):
        if name.startswith("SIG") and not name.startswith("SIG_"):
            if sig_num == getattr(signal, name):
                return name
    if sig_num == 34:
        return "SIGPROT"
    return f"Unknown signal ({sig_num})"


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

    # analyse error.log with process ids in order to determine the signal
    for i in range(1, 17+2+1):
        if not i in aarch64_pids.keys(): # assume keys are the same for other configs
            continue
        aarch64_signal = find_exit_signal(aarch64_error_log_path, aarch64_pids[i])
        aarch64c_signal = find_exit_signal(aarch64c_error_log_path, aarch64c_pids[i])
        aarch64c_q0_signal = find_exit_signal(aarch64c_error_log_path, aarch64c_q0_pids[i])
        if i > 17:
            cpv_number = "B" + str(i - 17)
        else:
            cpv_number = str(i)
        if cpv_number == "12": # Linux-specific code path
            row = [cpv_number, "N/A", "N/A", "N/A"]
        else:
            row = [cpv_number, get_signal_name(aarch64_signal) if aarch64_signal else '-',
                    get_signal_name(aarch64c_signal) if aarch64c_signal else '-',
                    get_signal_name(aarch64c_q0_signal) if aarch64c_q0_signal else '-']
        table_rows.append(row)
        
    print(tabulate(table_rows, headers=table_headers, tablefmt="plain"))

if __name__ == "__main__":
    main()
