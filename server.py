import socket
import threading
import commands

HOST = "localhost"
PORT = 3000

sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sock.bind((HOST,PORT))
sock.listen(8)

clients = []

class Server(threading.Thread):
    def __init__(self, sockt:tuple[socket.socket,tuple[str,int]]):
        self.socket, self.address = sockt
        global clients
        self.commands = commands.Commands(self.socket,self, clients)
        self.clients = clients # list is mutable so umm
        self.clients.append(self)
        super().__init__(target=self.run,daemon=True)

        self.username = ""
        self.channel = ""

        self.active = False

    def recieve_message(self, message, sender="*"):
        self.socket.send(f"RECV {sender} : {message}\n".encode("ascii"))

    def run(self):
        self.active = True
        sock = self.socket
        commands = self.commands
        sock.send(b"NOTE LF used for this connection\n")

        while self.active:
            command = sock.recv(512).decode()
            name = command.split()[0]
            if not command:
                continue

            try:
                func = commands.mapping[name]
            except KeyError:
                sock.send(b"ERR Invalid Command\n")
            func(command)
        
        sock.close()



if __name__ == "__main__":
    while True:
        connection = sock.accept()
        server = Server(connection)
        server.start()