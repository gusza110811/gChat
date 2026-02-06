# cli client for gChat server
import datetime
import socket
import sys
import threading
import time

class Client:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.create_connection((self.host, self.port))
        self.CTRLstat = None
        self.channel = "all"

        self.pending_messages = []

    def receive_messages(self):
        while True:
            buffer = b""
            chunk = self.socket.recv(1024)
            if not chunk:
                break
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                self.processLine(line)

    def processLine(self,line:bytes):
        if line.startswith(b"CTRL"):
            subcommand, ctrl, *junk = line[5:].decode().split()
            if ctrl == "fetch" and subcommand == "begin":
                self.CTRLstat = "fetch"
            elif ctrl == "list" and subcommand == "begin":
                self.CTRLstat = "list"
            elif subcommand == "end":
                self.CTRLstat = None
        elif line.startswith(b"RECV"):
            data = line.decode()[5:]
            channel, sender, *message = data.split(";")
            channel = channel.strip()
            sender = sender.strip()
            message = ";".join(message).strip()
            if channel == self.channel:
                self.pending_messages.append(f"[{datetime.datetime.fromtimestamp(round(time.time())).astimezone()}] @{sender}: {message}\n")
        elif line.startswith(b"ERR"):
            err = line.decode()[4:].split()[0]
            if err == "MissingUsername":
                self.pending_messages.append("[ERROR] No name provided, use /name to set your name\n")
            else:
                # Generic/Unknown errors
                self.pending_messages.append(f"[ERROR] {line.decode()[4:]}\n")
        elif self.CTRLstat == "fetch":
            try:
                timestamp, channel, sender, *message = line.strip().decode().split(";")
            except ValueError:
                self.pending_messages.append("[INFO] Junk data found, please contact server owner\n")
                return
            timestamp = int(timestamp.strip())
            sender = sender.strip()
            message = ";".join(message).strip()
            tmp = []
            tmp.insert(0,f"[{datetime.datetime.fromtimestamp(timestamp).astimezone()}] @{sender}: {message}\n")
            self.pending_messages += tmp

    def keep_alive(self):
        while True:
            self.socket.sendall(b"PING\n")
            time.sleep(30)

    def main(self):

        receiver_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receiver_thread.start()

        keep_alive_thread = threading.Thread(target=self.keep_alive, daemon=True)
        keep_alive_thread.start()

        name = input("Enter your username: ")
        self.socket.sendall(b"NAME " + name.encode('utf-8') + b'\n')
        self.fetch()
        
        self.chchan("all")

        while True:
            while not self.pending_messages:pass
            while self.pending_messages:
                print(self.pending_messages.pop(0), end="")
            msg = input(f"Sending as {name}: ").strip()
            if not msg:
                continue
            if msg.lower() == '/exit':
                break
            elif msg.lower().startswith('/join'):
                self.chchan(msg[4:].strip())
            elif msg.lower() == "/load":
                self.fetch()
            else:
                self.socket.sendall(b"MSG " + msg.encode('utf-8') + b'\n')
    
    def chchan(self, channel):
        self.channel = channel
        self.socket.send(f"JOIN {channel}\n".encode())
        self.fetch()
        print(f"now talking in {channel}")
    
    def fetch(self):
        self.socket.send(b"FETCHC 100\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client-cli.py <host> [port]")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 3355

    client = Client(host, port)
    try:
        client.main()
    except KeyboardInterrupt:pass

    print("exit")
