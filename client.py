import socket
import tkinter
import threading
from tkinter import scrolledtext
from collections import deque
import json
import time
import datetime
import shlex

class UI:

    def onSend(self,event:tkinter.Event,textvar:tkinter.Variable):
        textvar.set("")

    def __init__(self):
        self.running = True
        self.root = tkinter.Tk()
        self.root.wm_title("gChat Client")
        root = self.root

        self.chat = scrolledtext.ScrolledText(root)
        self.chat.config(state=tkinter.DISABLED)
        self.chat.pack()

        self.inputbar = tkinter.Frame(root)
        inputbar = self.inputbar

        self.username = tkinter.Label(inputbar,text="None")

        self.inputtext = tkinter.Variable(inputbar)
        self.input = tkinter.Entry(inputbar,textvariable=self.inputtext, width=60)
        self.input.bind("<Return>", lambda e: self.onSend(e,self.inputtext))

        self.username.pack(side="left")
        self.input.pack(side="left",fill="x")

        self.inputbar.pack()

        self.pendingOp:deque[tuple] = deque()
    def loop(self):
        while self.running:
            if self.pendingOp:
                commandt = self.pendingOp.popleft()
                command = commandt[0]
                params = commandt[1]
                if command == "print":
                    self.chat.config(state=tkinter.NORMAL)
                    self.chat.insert(tkinter.END,params[0])
                    self.chat.config(state=tkinter.DISABLED)
                elif command == "insert":
                    self.chat.config(state=tkinter.NORMAL)
                    self.chat.insert(1.0,params[0])
                    self.chat.config(state=tkinter.DISABLED)
                elif command == "clear":
                    self.chat.config(state=tkinter.NORMAL)
                    self.chat.delete(1.0,tkinter.END)
                    self.chat.config(state=tkinter.DISABLED)

            self.root.update()
    
    def sendCommand(self,command:str,params:list):
        self.pendingOp.append((command,params))

class App(threading.Thread):
    def __init__(self, ui:UI, server:str, port=3355,name:str=None):
        self.helpMSG = """/join : change channel
/name : change name"""

        super().__init__(target=self.listen,daemon=True)
        self.ui = ui
        self.active = True
        if server.startswith("[") and server.endswith("]"):
            server = server[1:-1]
            self.socket = socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
        else:
            self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock = self.socket
        sock.connect((server, port))
        if name:
            sock.send(f"NAME {name}\n".encode())
        
        endlineNotice = sock.recv(128).decode().strip()
        if endlineNotice != "NOTE LF used for this connection":
            self.ui.sendCommand("print",["[WARNING] Protocol mismatch"])
        
        self.changeCh("all")
        
        ui.onSend = self.onSend
        if name:
            self.changeName(name)
        ui.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.CTRLstat = None
    
    def onSend(self, event, textvar:tkinter.Variable):
        message:str = textvar.get()
        textvar.set("")
        if not message.startswith("/"):
            self.socket.send(f"MSG {message}\n".encode())
            return
        command, *params = shlex.split(message[1:])
        if command == "join":
            try:
                self.changeCh(params[0])
            except IndexError:
                self.ui.sendCommand("print",["[ERROR] Please provide a channel\n"])
        elif command == "name":
            try:
                self.changeName(params[0])
            except IndexError:
                self.ui.sendCommand("print",["[ERROR] Please provide a name\n"])
    
    def fetch(self):
        self.socket.send(b"FETCHC 100\n")
    
    def changeCh(self,channel:str):
        self.ui.sendCommand("clear",[])
        channel = channel
        self.channel = channel
        self.socket.send(f"JOIN {channel}".encode())
        self.fetch()
        self.ui.sendCommand("print", [f"[INFO] Now talking in {channel}\n"])
    
    def changeName(self,name:str):
        ui.username.config(text=name)
        self.socket.send(f"NAME {name}".encode())

    def listen(self):
        sock = self.socket
        while self.active:
            response = sock.recv(1024)
            lines = response.splitlines()
            for line in lines:
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
                        self.ui.sendCommand("print",[f"[{datetime.datetime.fromtimestamp(round(time.time()))}] @{sender}:{message}\n"])
                elif line.startswith(b"ERR"):
                    err = line.decode()[4:].split()[0]
                    if err == "MissingUsername":
                        self.ui.sendCommand("print",["[ERROR] No name provided, use /name to set your name\n"])
                    self.ui.sendCommand("print",["[ERROR] "+line.decode()[4:]+"\n"])
                elif self.CTRLstat == "fetch":
                    timestamp, channel, sender, *message = line.strip().decode().split(";")
                    timestamp = timestamp.strip()
                    sender = sender.strip()
                    message = ";".join(message).strip()
                    self.ui.sendCommand("insert",[f"[{timestamp}] @{sender}:{message}\n"])
                print(self.CTRLstat,line)

    def on_close(self):
        self.active = False
        ui.running = False
        try:
            self.socket.send(b"QUIT\n")
            self.socket.close()
        except Exception:
            pass
        self.ui.root.destroy()

if __name__ == "__main__":
    ui = UI()
    server = "localhost"
    port = 3355
    name = None
    try:
        with open("cfg.json") as configFile:
            config = json.load(configFile)
            server = config["host"]
            try:
                port = config["port"]
            except KeyError:
                pass
            try:
                name = config["name"]
            except KeyError:
                pass
    except FileNotFoundError:
        pass
    app = App(ui,server,port,name)
    app.start()

    ui.loop()