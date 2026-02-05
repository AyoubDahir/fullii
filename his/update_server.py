
import paramiko
import time

hostname = "192.145.173.102"
username = "hussein"
password = "D2cdec4f12##"

# Using absolute paths and chaining commands to ensure context is preserved/correct
command = "sed -i 's/rasiin/his/g' /home/hussein/frappe-bench/apps/his/his/monkey_patches/__init__.py && cd /home/hussein/frappe-bench && bench restart"

def run_update():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {hostname}...")
        client.connect(hostname, username=username, password=password)
        print("Connected.")

        print(f"Running: {command}")
        stdin, stdout, stderr = client.exec_command(command)
        
        # Wait for command to complete
        exit_status = stdout.channel.recv_exit_status()
        
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        
        if out:
            print(f"STDOUT: {out}")
        if err:
            print(f"STDERR: {err}")
        
        if exit_status != 0:
            print(f"Command failed with exit status {exit_status}")
            return

        print("Update completed successfully.")
        client.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_update()
