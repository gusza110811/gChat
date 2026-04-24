# gChat Protocol Specification

## Client Commands

| Command            | Description                                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| `NAME [name]`      | Sets the user's display name. Names cannot contain whitespace.                                                |
| `JOIN [channel]`   | Joins a chat channel. Channel names cannot contain whitespace.                                                |
| `MSG [message]`    | Sends a message to the current channel.                                                                       |
| `LIST`             | Requests a list of active users.                                                                              |
| `FETCH [?amount]`  | Retrieves the most recent messages (newest first). If no amount is given, all available messages are fetched. |
| `FETCHC [?amount]` | Same as `FETCH`, but filters messages to the current channel only.                                            |
| `QUIT`             | Disconnects from the server gracefully.                                                                       |
| `PING`             | Keeps the connection alive. The server replies with `PONG`.                                                   |

## Server Commands

| Command                                 | Description                                                               |
| --------------------------------------- | ----------------------------------------------------------------------    |
| `NOTE [variable] = [value]`             | Sends information or notification                                         |
| `CTRL [subcommand] [command]`           | Marks the start or end of a multi-line response (e.g., fetch or list).    |
| `ERR [type] [?info]`                    | Reports an error. Optional `info` may provide more context.               |
| `RECV [channel] ; [sender] ; [message]` | Indicates a received message from a client (including the current client).|
| `PONG`                                  | Response to `PING`, indicating the connection is alive.                   |

## Connection and Handshake

Once a TCP connection is established, the server must send one of the following to indicate the line-ending convention used:

* `NOTE LINE_END = LF`
* `NOTE LINE_END = CRLF`

And the channel the user is currently in:
* eg. `NOTE CH = all`

After receiving this notice, the client must send:

```
NAME [username]
```

This initiates the handshake and sets the user's name.

Once the handshake is complete, both sides can begin normal communication. The client may send `MSG` to broadcast messages or `JOIN` to switch channels. Incoming messages from any client are sent via the `RECV` command.

When the user wishes to disconnect, the client should send `QUIT`.

## Packet Structures

### `FETCH` and `FETCHC` Responses

```
CTRL begin fetch
[timestamp] ; [channel] ; [sender] ; [message]
[timestamp] ; [channel] ; [sender] ; [message]
...
CTRL end fetch
```

### `LIST` Responses

```
CTRL begin list
[name]
[name]
...
CTRL end list
```

### Other usage of `NOTE`
- The user's current channel after successful `JOIN`
    - ex. `NOTE CH = all`
- The user's current username after successful `NAME`
    - ex. `NOTE NAME = Alice`

## Error Handling

| Error             | Description                                                       |
| ----------------- | ----------------------------------------------------------------- |
| `InvalidCommand`  | The command sent was not recognized by the server.                |
| `NoParameter`     | A required command parameter was missing.                         |
| `MissingUsername` | The client attempted to send a message before setting a username. |
| `Rejected`        | The server rejected the client's request                          |

Servers may define additional error codes, but all clients and servers must support these standard types.

## Connection Maintenance

To maintain an active connection, clients must periodically send a `PING` command every **30–120 seconds**. The server must reply with `PONG` to confirm the connection remains active.

If either side does not receive the expected `PING` or `PONG` within a reasonable timeframe, it should assume the connection is lost and act accordingly.

Servers must wait at least **120 seconds** of inactivity before closing a connection due to timeout.
