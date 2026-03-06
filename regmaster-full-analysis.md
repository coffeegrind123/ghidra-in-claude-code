# RegMaster.dll - CS 1.6 Master Server Registration Protocol Analysis

## Overview

RegMaster.dll is a **Metamod plugin** (compiled with Delphi/C++Builder) that registers a CS 1.6 (HLDS) server with multiple master servers. It hooks into the HLDS engine via Metamod's API and periodically sends heartbeat packets to keep the server listed.

## Architecture

### Plugin Lifecycle

1. **Meta_Query** (`0x44f0b0`): Version check - requires Metamod 5:13+
2. **Meta_Attach** (`0x44f7fc`):
   - Finds `swds.dll` (HLDS engine) in memory
   - Scans swds.dll for a byte pattern to locate the **server UDP socket handle** (stored at `DAT_00450d40`)
   - Creates a background thread (TThread subclass at VMT `0x44e1c8`)
3. **Meta_Detach** (`0x44f9ac`): Cleans up the thread

### Engine Hooks (GetEntityAPI2)

- **ServerActivate** (`0x44f4c0`): Marks server as active
- **StartFrame** (`0x44f530`): Called each server frame (used for timing)
- **ServerDeactivate** (`0x44f4f8`): Marks server as inactive

### WinSock Loading

All socket functions are dynamically loaded from **wsock32.dll** via `GetProcAddress`:
- `socket`, `sendto`, `recvfrom`, `closesocket`, `ioctlsocket`
- `gethostbyname`, `inet_addr`, `inet_ntoa`, `ntohs`, `htons`

The plugin **reuses the HLDS server's existing UDP socket** (found by scanning swds.dll memory) rather than creating its own.

## Master Server List Loading

**Function**: `RegMaster_RegisterToMasterServers` (`0x44e4b0`)

1. Gets the module path via `GetModuleFileNameA()`
2. Constructs path: `<dll_directory>\MasterServerList.txt`
3. Reads the file line by line:
   - Skips lines starting with `#` or `;` (comments)
   - Parses format: `hostname:port` or just `hostname`
   - **Default port**: `0x6982` = **27010** (standard GoldSrc master server port)
4. Resolves hostnames:
   - First tries `inet_addr()` for IP addresses
   - Falls back to `gethostbyname()` for hostnames
5. Checks for duplicates via `FUN_0044e32c` (compares IP + port)
6. Stores entries in a dynamic array at `object+0x60`, each entry is 16 bytes:
   - Offset 0x00: IP address (4 bytes, network order)
   - Offset 0x04: Port (2 bytes)
   - Offset 0x08: Last heartbeat timestamp (8 bytes, double/TDateTime)

## Registration Protocol

### Step 1: Challenge Request

**Function**: `RegMaster_SendChallenge` (`0x44dd4c`)

Sends via `sendto()` on the HLDS socket to each master server:

```
Packet: FF FF FF FF 71
         ^^^^^^^^^^^  ^^
         Header       'q' (0x71) = Challenge request
```

Total: **5 bytes**

### Step 2: Challenge Response

**Function**: `RegMaster_RecvFrom` (`0x44dcac`)

Expected response from master server:

```
Offset  Bytes         Meaning
0x00    FF FF FF FF   Header (4 bytes)
0x04    73            's' (0x73) = Challenge response type
0x05    0A            '\n' (0x0A) = Separator
0x06    XX XX XX XX   Challenge number (4 bytes, unsigned 32-bit)
```

The response is validated by comparing the first 6 bytes against `\xFF\xFF\xFF\xFF\x73\x0A` (stored at `0x44eb4c`). Minimum response length: **10 bytes**.

### Step 3: Heartbeat/Registration Packet

**Function**: `RegMaster_SendHeartbeat` (`0x44e790`)

After receiving the challenge, the plugin gathers server info from the HLDS engine and sends a formatted registration string via `sendto()`:

```
0\n\protocol\48\challenge\%u\players\%u\max\%u\bots\%u\gamedir\%s\map\%s\type\d\password\1\os\w\secure\%d\lan\%d\version\1.1.2.7/Stdio\region\%u\product\%s\n
```

**Field breakdown:**

| Field | Value | Source |
|-------|-------|--------|
| `protocol` | `48` | Hardcoded - GoldSrc protocol version 48 |
| `challenge` | `%u` | Challenge value from Step 2 response |
| `players` | `%u` | Current non-bot player count (counted at runtime) |
| `max` | `%u` | `sv_maxplayers` from engine |
| `bots` | `%u` | Bot count (detected by checking player flags & 0x2000) |
| `gamedir` | `%s` | Game directory (e.g., "cstrike") from engine |
| `map` | `%s` | Current map name from engine |
| `type` | `d` | Hardcoded - 'd' = dedicated server |
| `password` | `1` | Hardcoded - always reports password=1 |
| `os` | `w` | Hardcoded - 'w' = Windows |
| `secure` | `%d` | VAC status (checked via GetProcAddress for VAC function) |
| `lan` | `%d` | LAN mode flag |
| `version` | `1.1.2.7/Stdio` | Hardcoded version string |
| `region` | `%u` | Server region code |
| `product` | `%s` | Same as gamedir |

### Timing

- **Heartbeat interval**: **19 seconds** (stored as float `19.0` at `0x44eb54`)
- Each master server entry tracks its own last-heartbeat timestamp independently

### Bot Detection

The plugin counts players by iterating through all client slots:
- Uses engine function table offsets to get player info
- Checks flag at `player_info + 0x222`: if bit `0x2000` is set, player is a **bot**
- Players matching `"BOT"` string comparison are also counted as bots

## Complete Protocol Flow

```
HLDS Server                          Master Server
     |                                     |
     |--- FF FF FF FF 71 ----------------->|  (Challenge request)
     |                                     |
     |<-- FF FF FF FF 73 0A [challenge] ---|  (Challenge response)
     |                                     |
     |--- "0\n\protocol\48\challenge\..."->|  (Registration heartbeat)
     |                                     |
     |  (repeat every 19 seconds)          |
     |                                     |
```

## MasterServerList.txt Format

```
# Comments start with # or ;
; This is also a comment

# Format: hostname:port or hostname (default port 27010)
hl2master.steampowered.com:27011
46.165.194.14:27010
ms.gs4u.net
88.198.47.43:27011
```

## Implementation Notes

To register a CS 1.6 server with master servers, you need:

1. **UDP socket** bound to the server's port (typically 27015)
2. **Send** `\xFF\xFF\xFF\xFF\x71` to master server IP:port
3. **Receive** `\xFF\xFF\xFF\xFF\x73\x0A` + 4-byte challenge
4. **Send** the formatted heartbeat string with the challenge value
5. **Repeat** every ~19-30 seconds to stay listed
6. The source IP:port of your heartbeat packets is what gets listed, so use the actual game server socket
