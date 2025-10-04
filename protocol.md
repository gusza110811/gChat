# The gChat protocol
## Client commands
| command | description |
| --- | --- |
| `NAME [name]` | Set user name |
| `MSG [message]` | Send message |
| `LIST` | Get list of active users |
| `QUIT` | Stop connection |

## Server commands
| command | description |
| --- | --- |
| `NOTE [message]` | Information, not required to be parsed |
| `CTRL [message]` | Control command, part of another command's output |
| `ERR [message]` | Information on a failed command |
| `RECV [message]` | Recieved message command |
