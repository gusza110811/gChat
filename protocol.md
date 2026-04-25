# gChat Protocol Specification

## Client Commands

| Command | Description |
| --- | --- |
| `NAME [name]` | Sets the user's display name. Names cannot contain whitespace or semicolon. |
| `JOIN [channel]` | Joins a chat channel. Channel names cannot contain whitespace or semicolon. |
| `MSG [message]` | Sends a message to the current channel. |
| `LIST` | Requests a list of active users. |
| `FETCH [?amount]` | Retrieves the most recent messages (newest first). If no amount is given, all available messages are fetched. |
| `FETCHC [?amount]` | Same as FETCH, but only returns messages in the current channel. |
| `QUIT` | Disconnects from the server gracefully.|
| `PING` | Keeps the connection alive. The server replies with `PONG`. |

## Server Commands

| Command | Description |
| --- | --- |
| `NOTE [key] = [value]` | Sends information or notification |
| `CTRL [subcommand] [command]` | Indicate the start or end of a multi-line response (e.g., fetch or list). |
| `ERR [type] [subtype*] [?info]` | Reports an error. Optional `info` may provide more context.|
| `RECV [channel] ; [sender] ; [message]` | Indicates a received message from a client (including the current client). |
| `PONG` | Response to `PING`, indicating the connection is alive. |

## Connection and Handshake

Once a TCP connection is established:

1. The client must send one `PING` to start communication

2. Then server must send connection info:

    The line ending used
    * `NOTE LINE_END = LF`
    * `NOTE LINE_END = CRLF`

    The channel the user is currently in
    * eg. `NOTE CH = all`

    The default username given to user
    * eg. `NOTE NAME = anon-42069`

    Then normal response to `PING`
    * `PONG`

The client may send `MSG` to broadcast messages or `JOIN` to switch channels. Incoming messages from any client are sent via the `RECV` command.

When the user wishes to disconnect, the client should send `QUIT`.

## Packet Structures

### Command format
- All commands are line-based and terminated by the configured LINE_END sequence.
Each line represents a complete command.
- The semicolon `;` is used as a field separator in certain server responses.
Clients MUST NOT include `;` in usernames or channel names.
- All text is encoded in UTF-8.

### `FETCH` and `FETCHC` Responses
**Newest message first**

```
CTRL begin fetch
[timestamp] ; [channel] ; [sender] ; [message]
[timestamp] ; [channel] ; [sender] ; [message]
...
CTRL end fetch
```
[timestamp] is a Unix timestamp (seconds since epoch, UTC).

### `LIST` Responses

```
CTRL begin list
[name]
[name]
...
CTRL end list
```

## `NOTE` Command
| Key | Description |
| --- | --- |
| `LINE_END` | Indicates the line-ending convention used by the server (`LF` or `CRLF` case insensitive). |
| `CH` | Indicates the current channel the user is in. |
| `NAME` | Indicates the current username of the user. |
The server MUST send updated NOTE values whenever the corresponding state changes.

## Error Handling

| Error | Description |
| --- | --- |
| `BadCommand` | Command sent by the client is malformed |
| `Rejected` | The server rejected the client's request |

### `BadCommand` suberror types

| Suberror | Description |
| --- | --- |
| `InvalidCommand` | The command sent was not recognized by the server. |
| `NoParameter` | A required command parameter was missing. |

### `Rejected` suberror types

| Suberror | Description |
| --- | --- |
| `InvalidUsername` | The username provided is invalid (e.g., contains ';') |
| `UsernameTaken` | The username provided is already in use by another client. |
| `InvalidChannel` | The channel name provided is invalid (e.g., contains ';') |
| `Unauthorized` | A plugin unauthorized the client's request (e.g., due to rate-limiting or other rules) |

Servers may define additional error codes, but all clients and servers must support these standard types.

## Connection Maintenance

To maintain an active connection, clients must periodically send a `PING` command every **30–120 seconds**. The server must reply with `PONG` to confirm the connection remains active.

If either side does not receive the expected `PING` or `PONG` within a reasonable timeframe, it should assume the connection is lost and act accordingly.

Servers must wait at least **120 seconds** of inactivity before closing a connection due to timeout.
