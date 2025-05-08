# python demo.py
# see coredumps in /tmp/cores/

import os
import socket
import time
import signal
import re
import subprocess
from tabulate import tabulate
import concurrent.futures

# ugly sleep times too
# hardcoded
conf_file = {
    'aarch64': 'demo-aarch64.conf',
    'aarch64c': 'demo-aarch64c.conf',
    'aarch64c+Q0': 'demo-aarch64c-q0.conf',
}
host = "127.0.0.1"
http_port = {
    'aarch64': 8080,
    'aarch64c': 8081,
    'aarch64c+Q0': 8082,
}
smtp_port = {
    'aarch64': 2525,
    'aarch64c': 2526,
    'aarch64c+Q0': 2527,
}
pop3_port = {
    'aarch64': 1111,
    'aarch64c': 1112,
    'aarch64c+Q0': 1113,
}

# 3 configurations: aarch64, aarch64c, aarch64c+Q0
configurations = ["aarch64", "aarch64c", "aarch64c+Q0"]
nginx_aarch64c_bin = "../install_aarch64c/sbin/nginx"
nginx_aarch64_bin = "../install_aarch64/sbin/nginx"
aarch64_error_log_path = '/tmp/nginx_aarch64/error.log'
aarch64c_error_log_path = '/tmp/nginx_aarch64c/error.log'
aarch64_pid_path = '/tmp/nginx_aarch64/nginx.pid'
aarch64c_pid_path = '/tmp/nginx_aarch64c/nginx.pid'
aarch64c_q0_pid_path = '/tmp/nginx_aarch64c/nginx-q0.pid'

# hardcoded envvars
envvars = 'MALLOC_CONF="junk:false"'

# results. cpv number (where bcpv counts as 17+i) -> PID
aarch64_pids = {}
aarch64c_pids = {}
aarch64c_q0_pids = {}

table_headers = ["CPV", "aarch64", "aarch64c", "aarch64c+Q0", "Mitigated", "Note"]
table_rows = []

# hardcoded Notes column
notes_columns = {}
for i in [1, 2, 3, 4, 8, 10, 14, 15, 18, 19, 12]:
    notes_columns[i] = 'Spatial'
for i in [5, 13]:
    notes_columns[i] = 'NULL deref'
for i in [9, 11, 17]:
    notes_columns[i] = 'Temporal'


def get_nginx_worker_pid(configuration):
    master_pid = None
    if configuration == "aarch64":
        pid_path = aarch64_pid_path
    elif configuration == "aarch64c":
        pid_path = aarch64c_pid_path
    else:
        pid_path = aarch64c_q0_pid_path
    try:
        with open(pid_path, 'r') as fp:
            master_pid = int(fp.read().strip())
    except:
        print("Error reading pid file", pid_path)
        return None
    worker_pid = int(subprocess.check_output(["pgrep", "-P", str(master_pid)]).decode().split()[0])
    return worker_pid

def start_nginx(config_file, configuration):
    absolute_config_path = os.path.abspath(config_file)
    if configuration == "aarch64":
        command = f"{envvars} {nginx_aarch64_bin} -c {absolute_config_path}"
    elif configuration == "aarch64c":
        command = f"{envvars} {nginx_aarch64c_bin} -c {absolute_config_path}"
    elif configuration == "aarch64c+Q0":
        command = f"{envvars} _RUNTIME_REVOCATION_EVERY_FREE_ENABLE=1 {nginx_aarch64c_bin} -c {absolute_config_path}"
    else:
        raise Exception(f"Unknown configuration {configuration}")
    ret = os.system(command)
    if ret != 0:
        raise RuntimeError(f"[!] Failed to start NGINX with config file: {config_file}")
    # print(f"[+] NGINX started with config file: {config_file}")


def stop_nginx(configuration):
    if configuration == "aarch64":
        os.system(f"{nginx_aarch64_bin} -s stop")
    elif configuration == "aarch64c":
        os.system(f"{nginx_aarch64c_bin} -s stop")
    else: # aarch64c+Q0
        os.system(f"kill $(cat {aarch64c_q0_pid_path})")
    # print("[+] NGINX stopped")


def send_request(request, configuration, verbose=False):
    if not request:
        raise RuntimeError("[!] Error: Request file is empty.")
    
    port = 0
    # rather simplistic and overfit logic
    if b'HTTP' in request:
        port = http_port[configuration]
    elif b'USER' in request:
        port = pop3_port[configuration]
    else:
        port = smtp_port[configuration]

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


def run_trigger(configuration, cpv_number, request):
    worker_pid = -1
    prev_pid = -1
    try:
        # print(f'[*] Configuration {configuration}')
        start_nginx(conf_file[configuration], configuration)
        # time.sleep(2)
        prev_pid = get_nginx_worker_pid(configuration)
        # print(f'[*] Nginx worker PID = {prev_pid}')
        # save the pid
        if configuration == "aarch64":
            aarch64_pids[cpv_number] = prev_pid
        elif configuration == "aarch64c":
            aarch64c_pids[cpv_number] = prev_pid
        else:
            aarch64c_q0_pids[cpv_number] = prev_pid
        send_request(request, configuration, verbose=False)
        time.sleep(1) # allow some time
        worker_pid = get_nginx_worker_pid(configuration)
        if worker_pid != prev_pid:
            print(f'[+] {configuration} Nginx worker process (PID={prev_pid}) crashed!')
        else:
            print(f"[!] {configuration} Nginx worker process (PID={prev_pid}) didn't crash")
    finally:
        stop_nginx(configuration)
        time.sleep(1)

# run in three configurations
def run_triggers():
    blob_files = list_blob_files()
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

        # run triggers in all configurations in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_trigger, configuration, cpv_number, request) for configuration in configurations]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()


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
            row = [cpv_number, "N/A", "N/A", "N/A", "N/A", notes_columns[i]]
        else:
            row = [cpv_number, get_signal_name(aarch64_signal) if aarch64_signal else '-',
                    get_signal_name(aarch64c_signal) if aarch64c_signal else '-',
                    get_signal_name(aarch64c_q0_signal) if aarch64c_q0_signal else '-',
                    "Yes" if aarch64c_q0_signal else "No",
                    notes_columns[i]]
        table_rows.append(row)
        
    print(tabulate(table_rows, headers=table_headers, tablefmt="plain"))

if __name__ == "__main__":
    main()
