import typing
import time, datetime

class Commands:
    def __init__(self, socket:"socket.socket", server:"server.Server", clients:"list[server.Server]", messages:list[tuple[str,str,str,str]]):
        self.socket = socket
        self.server = server
        self.address = server.address
        self.clients = clients
        self.messages = messages
        self.mapping = {
            "NAME" : self.NAME,
            "JOIN" : self.JOIN,
            "MSG": self.MSG,
            "LIST": self.LIST,
            "FETCH": self.FETCH,
            "FETCHC": self.FETCHC,
            "PING": self.PING,
            "QUIT": self.QUIT,

            "GET": self.teapot,
            "HEAD": self.teapot,
        }

    def NAME(self, arg:str):
        try:
            self.server.username = arg.split()[0]
            print(f"{self.address[0]} is now {self.server.username}")
        except IndexError:
            self.socket.send(b"ERR NoParameter\n")

    def JOIN(self, arg:str):
        try:
            self.server.channel = arg.split()[0]
            print((self.server.username or "unnamed") + f" joined {self.server.channel}")
        except IndexError:
            self.socket.send(b"ERR NoParameter\n")

    def MSG(self, arg:str):
        if not self.server.username:
            self.socket.send(b"ERR MissingUsername\n")
            return
        print(f"{datetime.datetime.fromtimestamp(round(time.time()))} #{self.server.channel} <{self.server.username}> {arg}")
        self.messages.append((round(time.time()),self.server.channel,self.server.username,arg))
        for client in self.clients:
            client.recieve_message(arg,self.server.channel,self.server.username)

    def LIST(self, arg:str):
        print((self.server.username or "unnamed") + " requested list")
        self.socket.send(b"CTRL begin list\n")
        for client in self.clients:
            if not client.username: continue
            self.socket.send((client.username+"\n").encode("utf-8"))
        self.socket.send(b"CTRL end list\n")
    
    def FETCH(self, arg:str):
        try:
            n = int(arg.split()[0])
        except (IndexError, ValueError):
            n = len(self.messages)  # default: all
        
        print((self.server.username or "unnamed") + " requested {n} messages")

        messages = self.messages[-n:].copy()  # get last n
        messages.reverse()
        self.socket.send(b"CTRL begin fetch\n")
        for message in messages:
            self.socket.send(
                f"{message[0]} ; {message[1]} ; {message[2]} ; {message[3]}\n".encode("utf-8")
            )
        self.socket.send(b"CTRL end fetch\n")

    def FETCHC(self, arg:str):
        try:
            n = int(arg.split()[0])
        except (IndexError, ValueError):
            n = len(self.messages)  # default: all

        messages = self.messages[-n:].copy()  # get last n
        messages.reverse()
        print((self.server.username or "unnamed") + f" requested {n} messages in {self.server.channel}")
        self.socket.send(b"CTRL begin fetch\n")
        for message in messages:
            if message[1] != self.server.channel:
                continue
            self.socket.send(
                f"{message[0]} ; {message[1]} ; {message[2]} ; {message[3]}\n".encode("utf-8")
            )
        self.socket.send(b"CTRL end fetch\n")
    
    def PING(self,arg:str):
        print((self.server.username or "unnamed") + " sent PING")
        self.socket.send(b"PONG\n")

    def QUIT(self,arg:str):
        print((self.server.username or "unnamed") + " requested to disconnect")
        self.server.active = False

    def teapot(self,arg:str):
        print(f"{self.address[0]} (\"{self.server.username}\") attempted to use http command")
        self.socket.send(b"ERR I'm a teapot!\n")

if typing.TYPE_CHECKING:
    import socket, server
