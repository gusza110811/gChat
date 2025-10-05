import socket
import threading
import commands
import json

host = "localhost"
port = 3355
ipv6 = False
maxClient = 16

messages:list[tuple[str,str,str,str]] = []

try:
    with open("cfg.json") as config:
        configs =  json.load(config)
        host:str = configs["host"]
        port:int = configs["port"]
        maxClient = configs["maxClient"]
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
        ipv6 = True
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
            self.socket.send(f"RECV {channel} ; {sender} ; {message}\n".encode("utf-8"))
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
                sock.send(b"ERR InvalidCommand\n")
                continue
            func(arg)

        self.clients.remove(self)
        sock.close()
        print(f"{self.address[0]} port {self.address[1]} Disconnected")

if __name__ == "__main__":
    try:
        while True:
            connection = sock.accept()
            server = Server(connection)
            server.start()
    except KeyboardInterrupt:
        print("\n\nStopping")
    finally:
        print(messages)
