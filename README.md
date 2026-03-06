# Ghidra in Claude Code

Use [Ghidra](https://ghidra-sre.org/) as an MCP tool in [Claude Code](https://docs.anthropic.com/en/docs/claude-code), enabling AI-assisted reverse engineering directly from the CLI.

Claude gets access to MCP tools like `decompile_function`, `list_exports`, `list_imports`, `list_strings`, `search_byte_patterns`, `read_memory`, `get_xrefs_to`, and more — all powered by Ghidra's analysis engine running headlessly.

## How It Works

```
Claude Code CLI
    |
    |-- starts run-ghidra-mcp-bridge.sh as MCP server
            |
            |-- launches Ghidra headless server (Java, port 8089)
            |-- launches bridge_mcp_ghidra.py on stdio (MCP protocol)
                    |
                    |-- translates MCP tool calls <-> Ghidra HTTP API
```

1. Claude Code launches the bridge script as an MCP server
2. The script starts Ghidra's headless server on port 8089 in the background
3. The Python MCP bridge runs on stdio, handling the MCP protocol
4. Claude Code gets access to all Ghidra analysis tools via MCP
5. You load binaries via HTTP, then Claude can analyze them using MCP tools

## Prerequisites

- **Ghidra 12.x** — [Download](https://github.com/NationalSecurityAgency/ghidra/releases)
- **JDK 21** — Required by Ghidra 12.x ([Adoptium](https://adoptium.net/))
- **Python 3.8+** — For the MCP bridge
- **Claude Code** — [Install](https://docs.anthropic.com/en/docs/claude-code)
- **GhidraMCP** — [bethington/ghidra-mcp](https://github.com/bethington/ghidra-mcp) v4.2.0+

## Installation

### 1. Install Ghidra and JDK

```bash
# Example paths — adjust for your system
export GHIDRA_HOME=/opt/ghidra_12.0.3_PUBLIC
export JAVA_HOME=/opt/jdk-21.0.10+7
```

### 2. Build GhidraMCP

```bash
git clone https://github.com/bethington/ghidra-mcp.git
cd ghidra-mcp
mvn package -DskipTests
# Produces target/GhidraMCP-4.2.0.jar
```

### 3. Copy scripts

```bash
# Clone this repo
git clone https://github.com/coffeegrind123/ghidra-in-claude-code.git
cd ghidra-in-claude-code

# Copy scripts to your preferred location
cp run-ghidra-mcp-bridge.sh start-ghidra-mcp.sh ~/ghidra-mcp/

# Make executable
chmod +x ~/ghidra-mcp/*.sh
```

### 4. Set environment variables

The scripts use these environment variables (with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `GHIDRA_HOME` | `/opt/ghidra_12.0.3_PUBLIC` | Ghidra installation directory |
| `JAVA_HOME` | `/opt/jdk-21.0.10+7` | JDK 21 installation directory |
| `GHIDRA_MCP_DIR` | `~/ghidra-mcp` | Directory containing ghidra-mcp repo |
| `GHIDRA_MCP_PORT` | `8089` | Port for the headless server |
| `GHIDRA_MCP_JAR` | `GhidraMCP-4.2.0.jar` | JAR filename |

Set these in your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export GHIDRA_HOME=/opt/ghidra_12.0.3_PUBLIC
export JAVA_HOME=/opt/jdk-21.0.10+7
export GHIDRA_MCP_DIR=/home/youruser/ghidra-mcp
```

### 5. Configure Claude Code

Add the MCP server to your Claude Code settings. Either:

**Option A**: Edit `~/.claude/settings.local.json` directly:

```json
{
  "mcpServers": {
    "ghidra": {
      "command": "/bin/bash",
      "args": ["/path/to/run-ghidra-mcp-bridge.sh"]
    }
  }
}
```

**Option B**: Copy and edit the example config:

```bash
cp claude-mcp-config.json ~/.claude/settings.local.json
# Edit the path in the file
```

### 6. (Optional) Copy the CLAUDE.md workflow guide

Place `CLAUDE.md` in your reverse engineering project directory so Claude knows the workflow:

```bash
cp CLAUDE.md ~/my-re-project/CLAUDE.md
```

## Usage

### Loading a binary

Binaries are loaded via the Ghidra headless server's HTTP API (not exposed as an MCP tool):

```bash
curl -s -X POST http://127.0.0.1:8089/load_program -d "file=/absolute/path/to/binary.exe"
```

Or ask Claude to do it:

> "Load /tmp/malware.dll into Ghidra and run analysis"

Claude will use `curl` via bash to hit the HTTP endpoint, then call `run_analysis` via MCP.

### Example session

```
$ claude

You: Load /tmp/RegMaster.dll into Ghidra, analyze it, and tell me what it does

Claude: [loads binary via curl, runs analysis, then uses MCP tools]
  - list_exports → finds Meta_Query, Meta_Attach, GetEntityAPI2
  - list_imports → sees wsock32.dll dynamic loading
  - list_strings → finds master server protocol strings
  - decompile_function → reverse engineers the heartbeat protocol
  ...
```

See [`examples/regmaster-analysis.md`](examples/regmaster-analysis.md) for a complete real-world analysis session.

## Available MCP Tools

Once the bridge is running, Claude has access to these tools:

| Tool | Description |
|------|-------------|
| `check_connection` | Verify the Ghidra server is running |
| `run_analysis` | Trigger Ghidra's auto-analysis on the loaded program |
| `list_exports` | List exported functions/symbols |
| `list_imports` | List imported functions/libraries |
| `list_strings` | List strings found in the binary (supports `filter` param) |
| `decompile_function` | Decompile a function to pseudocode |
| `get_function_by_address` | Look up function at a given address |
| `get_xrefs_to` | Find cross-references to an address |
| `search_byte_patterns` | Search for byte sequences in the binary |
| `read_memory` | Read raw bytes at an address |
| `create_function` | Define a new function at an address |
| `rename_function` | Rename a function |
| `set_comment` | Add a comment at an address |

### HTTP-only endpoints (not in MCP)

These are available on the headless server but not exposed through the MCP bridge:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/load_program` | POST | Load a binary from disk |
| `/close_program` | POST | Close a loaded program |
| `/open_project` | POST | Open an existing .gpr project |
| `/close_project` | POST | Close the current project |
| `/create_project` | POST | Create a new project |

## Tips and Gotchas

- **No GUI tools**: `open_program`, `launch_codebrowser`, `list_project_files` require GUI mode and will error in headless mode.
- **Binary loading is HTTP-only**: The Python bridge does not expose `/load_program` as an MCP tool. Use `curl` or ask Claude to do it.
- **Unanalyzed code**: Ghidra's auto-analysis may miss functions, especially in Delphi/C++Builder binaries. Use `read_memory` to find function prologues (`55 8B EC`) and `create_function` to define them.
- **Dynamic imports**: Some binaries load APIs at runtime via `GetProcAddress`. These won't appear in `list_imports` — search for API name strings instead.
- **Data xref workaround**: When `get_xrefs_to` returns nothing, convert the target address to little-endian bytes and use `search_byte_patterns` to find references.
- **Memory**: The headless server defaults to `-Xmx4g`. Adjust `JAVA_OPTS` for larger binaries.
- **Port conflicts**: The script kills any existing process on the configured port before starting.
- **Startup delay**: The Ghidra server takes a few seconds to start. The MCP bridge starts immediately for the handshake; Ghidra calls will fail gracefully until the server is ready.

## Standalone headless server

If you want to run the Ghidra headless server without the MCP bridge (e.g., for direct HTTP API access):

```bash
./start-ghidra-mcp.sh
# Server runs on 127.0.0.1:8089
# Hit Ctrl+C to stop
```

## License

Scripts in this repo are MIT licensed. Ghidra is Apache 2.0. GhidraMCP has its own license — see [bethington/ghidra-mcp](https://github.com/bethington/ghidra-mcp).
