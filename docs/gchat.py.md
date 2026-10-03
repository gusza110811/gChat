# gchat.py documentation

This module provides a small socket-based client for the gChat protocol. It connects to a gChat server, negotiates the protocol, sends commands, and reacts to server events through callback hooks.

## Overview

`gchat.py` is a client class designed for:

- connecting to a TCP server
- sending protocol commands such as `NAME`, `JOIN`, `MSG`, `LIST`, and `FETCH`
- reading incoming protocol lines in the background
- handling handshake, auto-ping, and disconnect logic
- dispatching events via callback functions

## Class

`gchat.py(host, port, on_message=None, on_note=None, on_error=None, on_list=None, on_fetch=None, on_pong=None, on_disconnect=None, on_raw=None, auto_ping=True, ping_interval=60, connect_timeout=10)`

### Parameters

- `host`: server hostname or IP
- `port`: TCP port number
- `on_message`: callback invoked for incoming chat messages
- `on_note`: callback invoked for protocol `NOTE` lines
- `on_error`: callback invoked for protocol `ERR` lines
- `on_list`: callback invoked for list results
- `on_fetch`: callback invoked when a fetch session ends
- `on_pong`: callback invoked when a `PONG` is received
- `on_disconnect`: callback invoked when the connection ends
- `on_raw`: callback invoked for unrecognized protocol lines
- `auto_ping`: if `True`, the client sends periodic `PING` messages
- `ping_interval`: ping interval in seconds, clamped to the protocol recommendation range of 30–120 seconds
- `connect_timeout`: timeout for connection and handshake

## Connection lifecycle

### `connect()`

Connects to the server, starts the reader thread, and performs the initial handshake.

Behavior:

1. Opens a socket with the configured timeout.
2. Starts a background reader thread.
3. Sends an initial `PING` command using the default line ending (`\n`).
4. Waits for the server to respond with:
   - `NOTE LINE_END = ...`
   - `NOTE CH = ...`
   - `NOTE NAME = ...`
   - `PONG`
5. If the handshake does not complete within `connect_timeout`, it closes the socket and raises `TimeoutError`.

If `auto_ping` is enabled, it also starts a ping thread.

### `close()`

Forces the socket closed and marks the client as not running.

### `quit()`

Sends a `QUIT` command if connected, then closes the socket.

### `connected`

Property returning whether the client is currently connected.

## Sending commands

All commands are serialized as text lines ending with the negotiated protocol line ending. The client tracks `self.line_end`, which is initially `\n` and updated from `NOTE LINE_END`.

### `_send_line(line, use_default=False)`

Internal helper that sends a raw protocol line.

- `use_default=True` causes LF to be used immediately during handshake
- otherwise it uses the negotiated `line_end`

### `send_command(cmd, *args)`

Builds a command string like:
- `NAME alice`
- `JOIN general`
- `MSG hello`

and sends it using `_send_line()`.

### Public command helpers

- `name(name)`: sends `NAME`
- `join(channel)`: sends `JOIN`
- `msg(message)`: sends `MSG`
- `list_users()`: sends `LIST`
- `fetch(amount=None)`: sends `FETCH`
- `fetchc(amount=None)`: sends `FETCHC`
- `ping()`: sends `PING`

## Background threads

### `_reader_loop()`

Reads lines from the socket and passes each line to `_handle_line()`. This thread runs continuously while the client is connected.

If the socket closes or any exception occurs, it sets `running = False` and invokes `on_disconnect()`.

### `_ping_loop()`

If auto-ping is enabled, sends periodic `PING` commands at the configured interval.

## Protocol parsing

`_handle_line(line)` interprets incoming server messages and dispatches them to the appropriate callbacks.

### `NOTE key=value`

Used for protocol metadata. Examples:

- `NOTE LINE_END=LF`
- `NOTE LINE_END=CRLF`
- `NOTE CH=general`
- `NOTE NAME=alice`

Handled keys:

- `LINE_END`: updates `self.line_end` to `\r\n` for `CRLF`, otherwise `\n`
- `CH`: stores the current channel
- `NAME`: stores the username

Then the client calls:
- `on_note(key, value)`

### `PONG`

A response to a `PING`.

On receipt:
- handshake is marked complete if not already done
- `_pong_event` is set
- `on_pong()` is called

### `RECV channel ; sender ; message`

Incoming chat message format.

Example:
- `RECV general ; alice ; hello there`

This calls:
- `on_message(channel, sender, message)`

### Fetch blocks

Fetch messages are collected between:

- `CTRL begin fetch`
- `CTRL end fetch`

When fetch mode starts, the client buffers messages internally. When the end marker is received, it triggers:
- `on_fetch(list_of_messages)`

Each item in the fetch buffer is a tuple:
- `(timestamp, channel, sender, message)`

The fetch loop looks for lines in the form:
- `12345 ; general ; alice ; hello`

### List blocks

List output is collected between:

- `CTRL begin list`
- `CTRL end list`

When the end marker is received, it triggers:
- `on_list(list_of_names)`

### `ERR type subtype ?info`

Error notification line.

Example:
- `ERR BAD_CMD UNKNOWN`

This calls:
- `on_error(err_type, err_subtype, info)`

### Unknown lines

Any unhandled line is passed to:
- `on_raw(line)`

## Callback hooks

The client provides a set of callback functions:

- `on_message(channel, sender, message)`: called when a chat message is received
- `on_note(key, value)`: called when a protocol `NOTE` line is received
- `on_error(err_type, err_subtype, info)`: called when a protocol `ERR` line is received
- `on_list(names)`: called when a list of users is received
- `on_fetch(messages)`: called when a fetch session ends
- `on_pong()`: called when a `PONG` is received
- `on_disconnect()`: called when the connection is closed
- `on_raw(line)`: called for any unhandled lines

If a callback is not provided, the event is simply ignored

## State attributes

The client maintains:

- `sock`: active socket
- `reader_thread`: background reader thread
- `ping_thread`: periodic ping thread
- `running`: connection state
- `line_end`: current protocol line ending
- `channel`: current channel
- `username`: nickname
- `_handshake_done`: event used to wait for the handshake
- `_pong_event`: event set when a `PONG` is received

## Example usage

```python
from gchat import GChat

def on_message(channel, sender, message):
    print(f"[{channel}] {sender}: {message}")

def on_note(key, value):
    print(f"NOTE {key}={value}")

def on_error(err_type, err_subtype, info):
    print(f"Error: {err_type} {err_subtype} {info}")

client = GChat(
    "localhost",
    9000,
    on_message=on_message,
    on_note=on_note,
    on_error=on_error,
)

client.connect()
client.msg("hello from Python")

# Wait for messages...
time.sleep(5)

client.quit()
```

## Notes

- The protocol requires a client to send an initial `PING` before the server will begin normal communication.
- The client automatically adjusts `ping_interval` to a value between 30 and 120 seconds when `auto_ping` is enabled.
- The implementation uses `threading.Event` for handshake and pong synchronization.
- Raw protocol lines are read with `socket.makefile('rb')` and decoded as UTF-8.
- The parser expects protocol messages to be terminated with `\n` or `\r\n`.

## Summary

`gchat.py` is a small, event-driven client for the GChat protocol. It handles connection setup, line parsing, background I/O, heartbeat pings, fetch/list collections, and user-facing callbacks. It is suitable for simple chat clients and protocol testing tools.
