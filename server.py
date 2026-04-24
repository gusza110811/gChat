#!/usr/bin/python3
import socket
import threading
import commands
import json
import os, sys
import argparse
import signal
import random

host = "localhost"
port = 3355
ipv6 = False
maxClient = 16

messages:list[tuple[int,str,str,str]] = []

clients:list["Server"] = []

class Server(threading.Thread):
    def __init__(self, sockt:tuple[socket.socket,tuple[str,int]]):
        self.socket, self.address = sockt
        global clients
        global messages
        self.clients = clients # list is mutable so umm
        self.clients.append(self)
        super().__init__(target=self.run,daemon=True)
        self.uid = None

        uid = random.randint(0,65535)
        while any(client.uid == uid for client in clients):
            uid = random.randint(0,65535)
        self.uid = uid

        self.username = f"anon-{self.uid}"
        self.channel = "all"

        self.active = False

        self.commands = commands.Commands(self.socket,self, clients, messages)

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
        sock.settimeout(120.0)

        buffer = ""
        sock.send(b"NOTE LINE_END = LF\n")
        sock.send(b"NOTE CH = all\n")
        sock.send(f"NOTE NAME = {self.username}\n".encode("utf-8"))
        try:
            while self.active:
                try:
                    data = sock.recv(512).decode("utf-8", errors="ignore")
                except ConnectionResetError:
                    break
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    name, *args = line.split(maxsplit=1)
                    arg = args[0] if args else ""

                    try:
                        func = commands.mapping[name]
                    except KeyError:
                        sock.send(b"ERR InvalidCommand\n")
                        continue

                    func(arg)
        except TimeoutError:
            pass
        if self.username:
            for client in self.clients:
                client.recieve_message(f"left the server",self.channel,self.username)

        self.clients.remove(self)
        sock.close()
        print(f"{self.address[0]} port {self.address[1]} Disconnected")

def exit_handler(path):
    print(messages)
    with open(path,"w") as msg:
        print(f"Saving messages to {path}")
        json.dump(messages,msg)
    sys.exit(0)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="gChat Server")
    argparser.add_argument("--config", "-c", help="Path to config file (default: ./cfg.json)", default="cfg.json")
    argparser.add_argument("--messages", "-m", help="Path to messages file (default: ./messages.json)", default="messages.json")
    argparser.add_argument("--env", "-e", help="Load config from environment variables (overrides config file)", action="store_true")

    args = argparser.parse_args()

    if not args.env:
        try:
            with open(args.config) as config:
                configs:dict =  json.load(config)
                host:str = configs.get("host","localhost")
                port:int = configs.get("port",3355)
                maxClient = configs.get("maxClient",16)
            if host.startswith("[") and host.endswith("]"):
                host = host[1:-1]
                ipv6 = True
        except FileNotFoundError:
            with open("cfg.json","w") as config:
                configs = {
                    "host": host,
                    "port": port,
                    "maxClient": maxClient
                }
                json.dump(configs,config, indent=4)
    else:
        host = os.getenv("GCHAT_HOST", host)
        port = int(os.getenv("GCHAT_PORT", port))
        maxClient = int(os.getenv("GCHAT_MAX_CLIENT", maxClient))
        if host.startswith("[") and host.endswith("]"):
            host = host[1:-1]
            ipv6 = True
    if ipv6:
        if not socket.has_ipv6:
            raise RuntimeError("IPv6 is not supported on this system")
        if host == "auto":
            # get public ip automatically
            host = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET6)[0][4][0]
        sock = socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    print(f"Listening on {host} port {port} with max {maxClient} clients")
    sock.bind((host,port))
    sock.listen(maxClient)

    filedir = os.path.dirname(__file__)

    message_save_path = args.messages
    print(f"Message save path: {message_save_path}")
    signal.signal(signal.SIGTERM, lambda signum, frame: exit_handler(message_save_path))
    signal.signal(signal.SIGINT, lambda signum, frame: exit_handler(message_save_path))

    if os.path.isfile(message_save_path):
        print(f"Loading messages from {message_save_path}")
        with open(message_save_path,"r") as msg:
            messages = json.load(msg)
    try:
        while True:
            connection = sock.accept()
            server = Server(connection)
            server.start()
    except KeyboardInterrupt:
        print("\n\nStopping")
