import socket
import threading
import commands
import json
from collections import deque

host = "localhost"
port = 3000
ipv6 = False
maxClient = 16

messages:deque[tuple[str,str,str]] = []

try:
    with open("cfg.json") as config:
        configs =  json.load(config)
        host = configs["host"]
        port = configs["port"]
        ipv6 = configs["ipv6"]
        maxClient = configs["maxClient"]
except FileNotFoundError:
    pass
if ipv6:
    sock = socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
else:
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sock.bind((host,port))
sock.listen(maxClient)

clients = []

class Server(threading.Thread):
    def __init__(self, sockt:tuple[socket.socket,tuple[str,int]]):
        self.socket, self.address = sockt
        global clients
        global messages
        self.commands = commands.Commands(self.socket,self, clients, messages)
        self.clients = clients # list is mutable so umm
        self.clients.append(self)
        super().__init__(target=self.run,daemon=True)

        self.username = ""
        self.channel = "all"

        self.active = False

    def recieve_message(self, message, channel, sender="*"):
        try:
            self.socket.send(f"RECV {channel} : {sender} : {message}\n".encode("ascii"))
        except BrokenPipeError:
            return

    def run(self):
        print(f"{self.address[0]} port {self.address[1]} Connected")

        self.active = True
        sock = self.socket
        commands = self.commands
        sock.send(b"NOTE LF used for this connection\n")

        while self.active:
            command = sock.recv(512).decode()
            if not command:
                self.active = False
            try:
                name = command.split()[0]
            except IndexError:
                continue
            arg = command[len(name):].strip()

            try:
                func = commands.mapping[name]
            except KeyError:
                sock.send(b"ERR Invalid Command\n")
                continue
            func(arg)

        self.clients.remove(self)
        sock.close()
        print(f"{self.address[0]} port {self.address[1]} Disconnected")

if __name__ == "__main__":
    while True:
        connection = sock.accept()
        server = Server(connection)
        server.start()
