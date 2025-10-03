import typing

class Commands:
    def __init__(self, socket:"socket.socket", server:"server.Server", clients:"list[server.Server]"):
        self.socket = socket
        self.server = server
        self.clients = clients
        self.mapping = {
            "NAME" : self.NAME,
            "MSG": self.MSG,
            "LIST": self.LIST,
            "QUIT": self.QUIT,
        }

    def NAME(self, arg:str):
        self.server.username = arg

    def MSG(self, arg:str):
        if not self.server.username:
            self.socket.send(b"ERR No username\n")
            return
        for client in self.clients:
            client.recieve_message(arg,self.server.username)

    def LIST(self, arg:str):
        self.socket.send(b"CTRL begin list\n")
        for client in self.clients:
            if not client.username: continue
            self.socket.send((client.username+"\n").encode("ascii"))
        self.socket.send(b"CTRL end list\n")

    def QUIT(self,arg:str):
        self.server.active = False
        self.clients.remove(self.server)

if typing.TYPE_CHECKING:
    import socket, server