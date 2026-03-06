# Example: RegMaster.dll Analysis

This is a real-world example of using Ghidra + Claude Code to reverse engineer a CS 1.6 Metamod plugin. The entire analysis was performed through Claude Code using MCP tools — no GUI needed.

## The Target

**RegMaster.dll** — a Metamod plugin (compiled with Delphi/C++Builder) that registers a CS 1.6 (HLDS) server with multiple master servers.

## Session

### Loading and initial analysis

```
You: Load /tmp/RegMaster.dll into Ghidra and run analysis

Claude: [executes via bash]
  curl -s -X POST http://127.0.0.1:8089/load_program -d "file=/tmp/RegMaster.dll"
  → {"success": true, "program": "RegMaster.dll"}

Claude: [calls run_analysis via MCP]
  → Analysis complete
```

### Identifying the plugin type

```
Claude: [calls list_exports]
  → Meta_Query (0x44f0b0)
  → Meta_Attach (0x44f7fc)
  → Meta_Detach (0x44f9ac)
  → GetEntityAPI2 (0x44f6e0)
  → GiveFnptrsToDll (0x44fa08)

These are Metamod plugin exports. This is an HLDS server plugin.
```

### Discovering dynamic imports

```
Claude: [calls list_imports]
  → kernel32.dll: GetModuleFileNameA, GetProcAddress, LoadLibraryA, CreateThread...
  → No wsock32.dll in imports!

Claude: [calls list_strings with filter="sendto"]
  → "sendto" at 0x44ea30
  → "recvfrom" at 0x44ea38

The plugin loads WinSock functions dynamically via GetProcAddress.
```

### Reverse engineering the protocol

```
Claude: [searches for protocol-related strings]
  list_strings filter="protocol" → "\protocol\48\challenge\%u\players\%u..."
  list_strings filter="master"  → "MasterServerList.txt"
  list_strings filter="\xff"    → "\xff\xff\xff\xff\x71" (challenge request)
```

### Decompiling key functions

```
Claude: [calls decompile_function for 0x44e790]
  → RegMaster_SendHeartbeat - builds and sends the registration packet

Claude: [calls decompile_function for 0x44dd4c]
  → RegMaster_SendChallenge - sends 5-byte challenge request

Claude: [calls decompile_function for 0x44e4b0]
  → RegMaster_RegisterToMasterServers - reads MasterServerList.txt
```

### Finding unanalyzed code

Ghidra missed some functions due to the Delphi compiler:

```
Claude: [calls read_memory at suspected function address]
  → Bytes: 55 8B EC 83 C4 F0 ... (function prologue)

Claude: [calls create_function at that address]
  → Function created

Claude: [calls decompile_function]
  → Now we can see the decompiled code
```

## Results

The complete analysis revealed:

1. **Plugin lifecycle**: Meta_Query/Meta_Attach/Meta_Detach hooks
2. **Socket reuse**: Scans swds.dll memory to find the HLDS server's UDP socket handle
3. **Master server protocol**:
   - Challenge request: `\xFF\xFF\xFF\xFF\x71` (5 bytes)
   - Challenge response: `\xFF\xFF\xFF\xFF\x73\x0A` + 4-byte challenge
   - Heartbeat: Key-value string with server info, sent every 19 seconds
4. **MasterServerList.txt**: Configurable master server list with hostname:port format
5. **Dynamic WinSock loading**: All socket functions loaded at runtime via GetProcAddress
6. **Bot detection**: Checks player flag bit 0x2000 and "BOT" string comparison

## Protocol Compatibility

The analysis was cross-referenced against 6 open-source master server implementations (hlmaster variants, pymaster, phantasma, xash3d-master) — RegMaster.dll's protocol is compatible with all of them.

See the full analysis: [RegMaster.dll Protocol Analysis](../regmaster-full-analysis.md)
