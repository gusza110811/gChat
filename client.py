import socket
import tkinter
import threading
from tkinter import scrolledtext
from collections import deque
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
                    wasAtBottom = self.chat.yview()[1] > 0.99
                    self.chat.config(state=tkinter.NORMAL)
                    self.chat.insert(tkinter.END,params[0])
                    if wasAtBottom:
                        self.chat.see(1.0)
                    self.chat.config(state=tkinter.DISABLED)
                elif command == "insert":
                    self.chat.config(state=tkinter.NORMAL)
                    self.chat.insert(1.0,params[0])
                    self.chat.yview_scroll(1,"units")
                    self.chat.config(state=tkinter.DISABLED)
                elif command == "clear":
                    self.chat.config(state=tkinter.NORMAL)
                    self.chat.delete(1.0,tkinter.END)
                    self.chat.config(state=tkinter.DISABLED)
                elif command == "chname":
                    self.username.config(text=params[0])

            self.root.update()
    
    def sendCommand(self,command:str,params:list):
        self.pendingOp.append((command,params))

class App():
    def __init__(self, ui:UI):
        self.ui = ui
        self.helpMSG = """
/help : show this message
/join : change channel
/name : change name
/connect [server] : connect to a server
/connect [server] [port] : connect to a server on a specific port
/disconnect : leave a server
"""
        self.active = False
        ui.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.socket:socket.socket

        self.pingInterval = 30

        self.listenThread = threading.Thread(target=self.listen,daemon=True)

        self.CTRLstat = None
        def sending(event,textvar:tkinter.Variable):
            message = textvar.get()
            threading.Thread(target=lambda:self.onSend(event,message)).start()
            textvar.set("")
        ui.onSend = sending

        ui.sendCommand("print",["[INFO] Welcome to gChat Client!\n"])
        ui.sendCommand("print",["[INFO] You can start by using /connect to connect to a server\n"])
        ui.sendCommand("print",["[INFO] Use /name to set your name and you're all set to chat!\n"])
        ui.sendCommand("print",["[INFO] Try connecting to chat.gusza.xyz!\n"])

    def keepAlive(self):
        while self.active:
            try:
                self.socket.send(b"PING\n")
            except BrokenPipeError:
                self.ui.sendCommand("print",["[ERROR] Disconnected"])
                self.disconnect()
            time.sleep(7)

    def connect(self, server:str, port:int):
        try:
            self.socket = socket.create_connection((server, port),timeout=10)
        except TimeoutError:
            self.ui.sendCommand("print",[f"[ERROR] Failed to connect to {server} : Connection timed out\n"])
            return
        except socket.gaierror:
            self.ui.sendCommand("print",[f"[ERROR] Unknown server\n"])
            return
        self.active = True
        sock = self.socket

        endlineNotice = sock.recv(128).decode().strip()
        if endlineNotice != "NOTE LF used for this connection":
            self.ui.sendCommand("print",["[WARNING] Protocol mismatch"])
        
        self.changeCh("all")
        self.listenThread = threading.Thread(target=self.listen, daemon=True)
        self.listenThread.start()
        self.keepAliveThread = threading.Thread(target=self.keepAlive, daemon=True)
        self.keepAliveThread.start()
    def disconnect(self):
        self.active = False
        try:
            self.socket.send(b"QUIT\n")
            self.socket.close()
        except Exception as e:
            print(e)
        self.changeName("None")
        self.ui.sendCommand("print",[f"[INFO] Disconnected"])

    def onSend(self, event, message:str):
        if not message.startswith("/"):
            if not self.active:
                self.ui.sendCommand("print",["[ERROR] Not connected to a server\n"])
                return
            try:
                self.socket.send(f"MSG {message}\n".encode())
            except BrokenPipeError:
                self.ui.sendCommand("print",["[ERROR] Connection failed\n"])
                self.disconnect()
            except AttributeError:
                self.active = False
                self.ui.sendCommand("print",["[ERROR] Not connected\n"])
            return
        self.handleCommand(message[1:])
    
    def handleCommand(self, prompt):
        command, *params = shlex.split(prompt)
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
        elif command == "connect":
            try:
                server = params[0]
            except IndexError:
                self.ui.sendCommand("print",["[ERROR] please provide host name\n"])
                return
            self.ui.sendCommand("print",[f"[INFO] Connecting to {server}\n"])
            try:
                port = int(params[1])
            except IndexError:
                port = 3355
            except ValueError:
                self.ui.sendCommand("print",["[ERROR] Port must be a number\n"])
            self.connect(server,port)
        elif command == "disconnect":
            if not self.active:
                self.ui.sendCommand("print",["[WARN] Not connected\n"])
                return

            self.disconnect()
        elif command == "help":
            self.ui.sendCommand("print",[self.helpMSG])
        else:
            self.ui.sendCommand("print",["[ERROR] Invalid command, use /help for list of commands\n"])
    
    def fetch(self):
        self.socket.send(b"FETCHC 100\n")
    
    def changeCh(self,channel:str):
        self.ui.sendCommand("clear",[])
        channel = channel
        self.channel = channel
        self.socket.send(f"JOIN {channel}\n".encode())
        self.fetch()
        self.ui.sendCommand("print", [f"[INFO] Now talking in {channel}\n"])
    
    def changeName(self,name:str):
        self.ui.sendCommand("chname",[name])
        if self.active:
            self.socket.send(f"NAME {name}\n".encode())

    def listen(self):
        sock = self.socket
        while self.active:
            buffer = b""
            while self.active:
                try:
                    chunk = sock.recv(1024)
                except ConnectionResetError:
                    self.ui.sendCommand("print",["[ERROR] Server closed the connection\n"])
                    self.disconnect()
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self.processLine(line)
    def processLine(self,line:bytes):
        print(line)
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
            else:
                # Generic/Unknown errors
                self.ui.sendCommand("print",["[ERROR] "+line.decode()[4:]+"\n"])
        elif self.CTRLstat == "fetch":
            try:
                timestamp, channel, sender, *message = line.strip().decode().split(";")
            except ValueError:
                self.ui.sendCommand("print",["[INFO] Junk data found, please contact server owner"])
                return
            timestamp = timestamp.strip()
            sender = sender.strip()
            message = ";".join(message).strip()
            self.ui.sendCommand("insert",[f"[{timestamp}] @{sender}:{message}\n"])

    def on_close(self):
        ui.running = False
        self.disconnect()
        self.ui.root.destroy()

if __name__ == "__main__":
    ui = UI()
    server = "localhost"
    app = App(ui)

    ui.loop()