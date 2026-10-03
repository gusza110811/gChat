# gchat.py
import socket
import threading
import time

class GChat:
    def __init__(self, host, port,
                 on_message=None, on_note=None, on_error=None,
                 on_list=None, on_fetch=None, on_pong=None,
                 on_disconnect=None, on_raw=None,
                 auto_ping=True, ping_interval=60,
                 connect_timeout=10):
        self.host = host
        self.port = port

        # Callbacks
        self.on_message = on_message or (lambda *a: None)
        self.on_note = on_note or (lambda *a: None)
        self.on_error = on_error or (lambda *a: None)
        self.on_list = on_list or (lambda *a: None)
        self.on_fetch = on_fetch or (lambda *a: None)
        self.on_pong = on_pong or (lambda *a: None)
        self.on_disconnect = on_disconnect or (lambda *a: None)
        self.on_raw = on_raw or (lambda *a: None)

        self.auto_ping = auto_ping
        # Clamp to protocol recommendation 30–120s
        self.ping_interval = max(30, min(120, ping_interval)) if auto_ping else ping_interval
        self.connect_timeout = connect_timeout

        self.sock = None
        self.reader_thread = None
        self.ping_thread = None
        self.running = False

        self.send_lock = threading.Lock()
        self.line_end = '\n'          # default until server tells us
        self.channel = None
        self.username = None

        self._handshake_done = threading.Event()
        self._pong_event = threading.Event()

        # Parser state
        self._in_fetch = False
        self._fetch_messages = []
        self._in_list = False
        self._list_names = []

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self):
        """Connect, perform handshake, and start background threads."""
        self.sock = socket.create_connection((self.host, self.port),
                                             timeout=self.connect_timeout)
        self.sock.settimeout(None)
        self.running = True

        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()

        # Step 1: client must send one PING to start communication.
        # We use LF here because line-ending is not yet known.
        self._send_line("PING", use_default=True)

        # Wait for server to send NOTE LINE_END, NOTE CH, NOTE NAME, then PONG.
        if not self._handshake_done.wait(timeout=self.connect_timeout):
            self.close()
            raise TimeoutError("Handshake timed out")

        if self.auto_ping:
            self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
            self.ping_thread.start()

        return self

    def close(self):
        """Force-close the connection."""
        self.running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def quit(self):
        """Send QUIT and close gracefully."""
        if self.running:
            self.send_command("QUIT")
        self.close()

    @property
    def connected(self):
        return self.running and self.sock is not None

    # ------------------------------------------------------------------
    # Command sending
    # ------------------------------------------------------------------
    def _send_line(self, line, use_default=False):
        if not self.sock:
            return
        end = '\n' if use_default else self.line_end
        data = (line + end).encode('utf-8')
        with self.send_lock:
            try:
                self.sock.sendall(data)
            except OSError:
                self.running = False

    def send_command(self, cmd, *args):
        """Send a raw protocol command with optional arguments."""
        parts = [cmd] + [str(a) for a in args if a is not None]
        self._send_line(" ".join(parts))

    # Public command helpers
    def name(self, name):
        self.send_command("NAME", name)

    def join(self, channel):
        self.send_command("JOIN", channel)

    def msg(self, message):
        self.send_command("MSG", message)

    def list_users(self):
        self.send_command("LIST")

    def fetch(self, amount=None):
        if amount is None:
            self.send_command("FETCH")
        else:
            self.send_command("FETCH", amount)

    def fetchc(self, amount=None):
        if amount is None:
            self.send_command("FETCHC")
        else:
            self.send_command("FETCHC", amount)

    def ping(self):
        self.send_command("PING")

    # ------------------------------------------------------------------
    # Background threads
    # ------------------------------------------------------------------
    def _ping_loop(self):
        while self.running:
            time.sleep(self.ping_interval)
            if self.running:
                self.ping()

    def _reader_loop(self):
        try:
            file = self.sock.makefile('rb')
            while self.running:
                raw = file.readline()
                if not raw:
                    break
                line = raw.decode('utf-8').rstrip('\r\n')
                self._handle_line(line)
        except Exception:
            pass
        finally:
            self.running = False
            self.on_disconnect()

    # ------------------------------------------------------------------
    # Protocol parsing
    # ------------------------------------------------------------------
    def _handle_line(self, line):
        # NOTE key = value
        if line.startswith("NOTE "):
            rest = line[5:]
            if '=' in rest:
                key, value = rest.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key == "LINE_END":
                    if value.upper() == "CRLF":
                        self.line_end = '\r\n'
                    else:
                        self.line_end = '\n'
                elif key == "CH":
                    self.channel = value
                elif key == "NAME":
                    self.username = value

                self.on_note(key, value)
            return

        # PONG
        if line == "PONG":
            if not self._handshake_done.is_set():
                self._handshake_done.set()
            self._pong_event.set()
            self.on_pong()
            return

        # RECV channel ; sender ; message
        if line.startswith("RECV "):
            rest = line[5:]
            parts = rest.split(';', 2)
            if len(parts) == 3:
                channel = parts[0].strip()
                sender = parts[1].strip()
                message = parts[2].lstrip()
                self.on_message(channel, sender, message)
            return

        # CTRL begin fetch / end fetch
        if line == "CTRL begin fetch":
            self._in_fetch = True
            self._fetch_messages = []
            return
        if line == "CTRL end fetch":
            self._in_fetch = False
            self.on_fetch(self._fetch_messages)
            self._fetch_messages = []
            return
        if self._in_fetch:
            parts = line.split(';', 3)
            if len(parts) == 4:
                ts = int(parts[0].strip())
                channel = parts[1].strip()
                sender = parts[2].strip()
                message = parts[3].lstrip()
                self._fetch_messages.append((ts, channel, sender, message))
            return

        # CTRL begin list / end list
        if line == "CTRL begin list":
            self._in_list = True
            self._list_names = []
            return
        if line == "CTRL end list":
            self._in_list = False
            self.on_list(self._list_names)
            self._list_names = []
            return
        if self._in_list:
            self._list_names.append(line.strip())
            return

        # ERR type subtype ?info
        if line.startswith("ERR "):
            rest = line[4:]
            parts = rest.split(' ', 2)
            err_type = parts[0] if len(parts) > 0 else ""
            err_subtype = parts[1] if len(parts) > 1 else ""
            info = parts[2] if len(parts) > 2 else ""
            self.on_error(err_type, err_subtype, info)
            return

        # Unknown line
        self.on_raw(line)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()