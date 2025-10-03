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
| `NOTE` | Information, not necessary to be parsed |
| `CTRL` | Control command, part of another command's output |
| `RECV` | Recieved message command |
| `ERR` | Information on a failed command |
