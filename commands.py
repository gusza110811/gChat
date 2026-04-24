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
        self.uid = server.uid

    def NAME(self, arg:str):
        try:
            newname = arg.split()[0]
            if ";" in newname:
                self.socket.send(b"ERR Rejected InvalidUsername\n")
                return
            if newname.startswith("anon-"):
                self.socket.send(b"ERR Rejected InvalidUsername\n")
                return
            for client in self.clients:
                if client.username == newname:
                    self.socket.send(b"ERR Rejected UsernameTaken\n")
                    return
            oldname = self.server.username
            self.server.username = newname
            self.socket.send(f"NOTE NAME = {self.server.username}\n".encode("utf-8"))
            print(f"[{self.uid}] " + (f"{oldname} is now" if oldname else "New user") + f" {self.server.username}")
        except IndexError:
            self.socket.send(b"ERR NoParameter\n")

    def JOIN(self, arg:str):
        if len(arg.split()) == 0:
            self.socket.send(b"ERR NoParameter\n")
            return
        target_channel = arg.split()[0]
        if target_channel == self.server.channel:
            return
        if ";" in target_channel:
            self.socket.send(b"ERR Rejected InvalidChannel\n")
            return
        if self.server.username:
            for client in self.clients:
                client.recieve_message("left the channel",self.server.channel,self.server.username)
        self.server.channel = target_channel
        self.socket.send(f"NOTE CH = {self.server.channel}\n".encode("utf-8"))
        print(f"[{self.uid}] {(self.server.username or '')} joined {self.server.channel}")
        if self.server.username:
            for client in self.clients:
                client.recieve_message("joined the channel",self.server.channel,self.server.username)

    def MSG(self, arg:str):
        print(f"[{self.uid}] {datetime.datetime.fromtimestamp(round(time.time()))} #{self.server.channel} <{self.server.username}> {arg}")
        self.messages.append((round(time.time()),self.server.channel,self.server.username,arg))
        for client in self.clients:
            client.recieve_message(arg,self.server.channel,self.server.username)

    def LIST(self, arg:str):
        print(f"[{self.uid}] {(self.server.username or '')} requested list")
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
        
        print(f"[{self.uid}] {(self.server.username or '')} requested {n} messages")

        messages = self.messages.copy()
        messages.reverse()
        self.socket.send(b"CTRL begin fetch\n")
        count = 0
        while count < n and messages:
            message = messages.pop(0)
            if message[1] != self.server.channel:
                continue
            self.socket.send(
                f"{message[0]} ; {message[1]} ; {message[2]} ; {message[3]}\n".encode("utf-8")
            )
            count += 1
        self.socket.send(b"CTRL end fetch\n")

    def FETCHC(self, arg:str):
        try:
            n = int(arg.split()[0])
        except (IndexError, ValueError):
            n = len(self.messages)  # default: all

        messages = self.messages.copy()
        messages.reverse()
        print(f"[{self.uid}] {(self.server.username or '')} requested {n} messages in {self.server.channel}")
        self.socket.send(b"CTRL begin fetch\n")
        count = 0
        while count < n and messages:
            message = messages.pop(0)
            if message[1] != self.server.channel:
                continue
            self.socket.send(
                f"{message[0]} ; {message[1]} ; {message[2]} ; {message[3]}\n".encode("utf-8")
            )
            count += 1
        self.socket.send(b"CTRL end fetch\n")
    
    def PING(self,arg:str):
        print(f"[{self.uid}] {(self.server.username or '')} sent PING")
        self.socket.send(b"PONG\n")

    def QUIT(self,arg:str):
        print(f"[{self.uid}] {(self.server.username or '')} requested to disconnect")
        self.server.active = False

    def teapot(self,arg:str):
        print(f"[{self.uid}] {(self.server.username or '')} attempted to use http command")
        self.socket.send(b"ERR Rejected I'm a teapot!\n")

if typing.TYPE_CHECKING:
    import socket, server
