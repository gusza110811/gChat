# The gChat protocol
## Client commands
| command | description |
| --- | --- |
| `NAME [name]` | Set user name (no whitespace) |
| `JOIN [channel]` | Join a channel (no whitespace) |
| `MSG [message]` | Send message |
| `LIST` | Get list of active users |
| `FETCH [begin], [?end]` | Fetch message from `begin` to `end`, `end` is 0 (latest message) if not provided |
| `QUIT` | Stop connection |

## Server commands
| command | description |
| --- | --- |
| `NOTE [message]` | Generic information |
| `CTRL [subcommand] [command]` | Control command, part of another command's output |
| `ERR [message]` | Information on a failed command |
| `RECV [channel] : [sender] : [message]` | Recieved message command |

## Communication
After connection has been established, the server must send `NOTE LF used for this connection` or `NOTE CRLF used for this connection` to signal the newline character used for communication

Once the client receives the newline character signal, if the user wants to send messages the client must send `NAME [username]` with the user's choice of name in place of `username`

After this handshake, double-sided chatting protocol can be initiated, the client can use `MSG` to send user's message and `JOIN` to change channel. client will receive `RECV` command from the server when any client sends a message.

The client can finally send `QUIT` once they wish to stop communicating