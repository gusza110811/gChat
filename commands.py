import typing
from collections import deque

class Commands:
    def __init__(self, socket:"socket.socket", server:"server.Server", clients:"list[server.Server]", messages:deque[tuple[str,str,str]]):
        self.socket = socket
        self.server = server
        self.clients = clients
        self.messages = messages
        self.mapping = {
            "NAME" : self.NAME,
            "JOIN" : self.JOIN,
            "MSG": self.MSG,
            "LIST": self.LIST,
            "FETCH": self.FETCH,
            "QUIT": self.QUIT,
        }

    def NAME(self, arg:str):
        self.server.username = arg.split()[0]

    def JOIN(self, arg:str):
        self.server.channel = arg.split()[0]

    def MSG(self, arg:str):
        self.messages.append((self.server.channel,self.server.username,arg))
        if not self.server.username:
            self.socket.send(b"ERR Missing username\n")
            return
        for client in self.clients:
            client.recieve_message(arg,self.server.channel,self.server.username)

    def LIST(self, arg:str):
        self.socket.send(b"CTRL begin list\n")
        for client in self.clients:
            if not client.username: continue
            self.socket.send((client.username+"\n").encode("ascii"))
        self.socket.send(b"CTRL end list\n")
    
    def FETCH(self, arg:str):
        try:
            try:
                begin = int(arg.split()[0])
            except IndexError:
                begin = -1
            try:
                end = int(arg.split()[1])
            except IndexError:
                end = 0
        except ValueError:
            self.socket.send(b"ERR Not an integer\n")
        messages = self.messages[end:begin]
        self.socket.send(b"CTRL begin fetch\n")
        for message in messages:
            self.socket.send(f"{message[0]} : {message[1]} : {message[2]}\n".encode("ascii"))
        self.socket.send(b"CTRL end fetch\n")

    def QUIT(self,arg:str):
        self.server.active = False

if typing.TYPE_CHECKING:
    import socket, server