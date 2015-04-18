import subprocess

def get_network_info():
    cmd = 'wpa_cli status | egrep "(wpa_state|id_str|ip_address)"'
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    entries = {}
    for line in iter(proc.stdout.readline, ''):
        line = line.strip()
        if '=' in line:
            (k, v) = line.split('=')
            entries[k] = v
    return entries
