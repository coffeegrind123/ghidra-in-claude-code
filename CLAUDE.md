# Ghidra MCP Workflow Guide

## Loading Binaries into Ghidra Headless MCP

The Ghidra MCP headless server (`GhidraMCPHeadlessServer`) does NOT expose a `load_program` MCP tool through the Python bridge. You must use the HTTP API directly.

### Step 1: Verify Connection

Use the MCP tool `check_connection` to confirm the server is running.

### Step 2: Load a Binary

The headless server has a `/load_program` HTTP endpoint that is NOT mapped to an MCP tool. Call it directly via curl:

```bash
curl -s -X POST http://127.0.0.1:8089/load_program -d "file=/absolute/path/to/binary.dll"
```

Returns: `{"success": true, "program": "binary.dll"}`

### Step 3: Run Analysis

Use the MCP tool `run_analysis` to trigger Ghidra's auto-analysis on the loaded program.

### Step 4: Use MCP Tools Normally

Once loaded and analyzed, all MCP tools work: `list_exports`, `list_imports`, `list_strings`, `decompile_function`, `search_byte_patterns`, etc.

## Key Gotchas

- **No import MCP tool**: The Python bridge (`bridge_mcp_ghidra.py`) does not expose `/load_program` as an MCP tool. You MUST use the HTTP endpoint directly.
- **No GUI tools**: `open_program`, `launch_codebrowser`, `list_project_files` all require GUI mode and will error in headless mode.
- **Create project first** (optional): `create_project` MCP tool works, but `/load_program` can load binaries without a project.
- **Java version**: Ghidra 12.0.3 requires Java 21 LTS.
- **Default port**: The headless server runs on `127.0.0.1:8089` by default.

## Useful HTTP Endpoints Not in MCP Bridge

These endpoints exist on the headless HTTP server but are NOT exposed as MCP tools:

| Endpoint | Method | Params | Purpose |
|----------|--------|--------|---------|
| `/load_program` | POST | `file=<path>` | Import and load a binary from disk |
| `/close_program` | POST | `name=<name>` | Close a loaded program |
| `/open_project` | POST | `path=<path>` | Open an existing .gpr project |
| `/close_project` | POST | (none) | Close the current project |
| `/load_program_from_project` | POST | `path=<path>` | Load a program from within a project |
| `/get_project_info` | GET | (none) | Get current project details |
| `/create_project` | POST | `parentDir`, `name` | Create a new project |
| `/delete_project` | POST | `projectPath` | Delete a project |

## Reverse Engineering Workflow

### Initial Recon
1. `list_exports` - Find entry points and exported functions
2. `list_imports` - Identify libraries and APIs used
3. `list_strings` with `filter` param - Search for interesting strings (IPs, paths, format strings, error messages)

### Finding Code
- `search_byte_patterns` - Find references to string addresses or byte sequences (e.g., search for little-endian address `ac eb 44 00` to find xrefs to string at `0x0044ebac`)
- `get_xrefs_to` - Find cross-references to an address (only works if Ghidra has properly analyzed the referring code)
- `get_function_by_address` - Check if an address is inside a known function

### Dealing with Unanalyzed Code
Ghidra's auto-analysis may miss functions, especially in Delphi/BCB binaries:
- `read_memory` to examine raw bytes at an address
- Look for function prologues: `55 8B EC` (push ebp; mov ebp, esp) or `55 8B EC 83 C4` / `55 8B EC 81 C4` (with stack frame)
- `create_function` at the prologue address to define the function
- `decompile_function` to get pseudocode

### Dynamic Imports
Some binaries load APIs at runtime via `GetProcAddress` instead of the import table. Look for:
- API name strings (e.g., `"sendto"`, `"recvfrom"`) in the string list
- These won't appear in `list_imports` - they're resolved at runtime
- Search for the string address bytes to find the loading code

### Data Pattern Searching
When `get_xrefs_to` returns nothing (common for data in unanalyzed regions):
1. Take the target address (e.g., `0x0044ebac`)
2. Convert to little-endian bytes: `ac eb 44 00`
3. Use `search_byte_patterns` with those bytes
4. This finds any code that references that address as an immediate operand
