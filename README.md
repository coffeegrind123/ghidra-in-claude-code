# Ghidra in Claude Code

Use [Ghidra](https://ghidra-sre.org/) as an MCP tool in [Claude Code](https://docs.anthropic.com/en/docs/claude-code), enabling AI-assisted reverse engineering directly from the CLI.

Claude gets access to 193 MCP tools — decompile, rename, document, create structs, trace call graphs, detect malware — all powered by [GhidraMCP](https://github.com/bethington/ghidra-mcp) v5.0.0 running headlessly.

## How It Works

```
Claude Code CLI
    |
    |-- starts launch_ghidra_mcp.py as MCP server
            |
            |-- launches Ghidra headless server (Java, port 8089)
            |-- execs bridge_mcp_ghidra.py on stdio (MCP protocol)
                    |
                    |-- fetches /mcp/schema from Ghidra HTTP server
                    |-- dynamically registers all 193 tools
                    |-- translates MCP tool calls <-> Ghidra HTTP API
```

## Prerequisites

- **JDK 21+** — Required by Ghidra 12.x ([Adoptium Temurin](https://adoptium.net/))
- **Ghidra 12.x** — [Download](https://github.com/NationalSecurityAgency/ghidra/releases)
- **Python 3.10+** — For the MCP bridge
- **Claude Code** — [Install](https://docs.anthropic.com/en/docs/claude-code)

## Installation

### 1. Install JDK and Ghidra

```bash
# Example — adjust paths for your system
export JAVA_HOME=/opt/jdk-21
export GHIDRA_HOME=/opt/ghidra_12.0.3_PUBLIC
```

### 2. Download GhidraMCP v5.0.0

No Maven build required — download the pre-built release:

```bash
mkdir -p ~/ghidra-mcp && cd ~/ghidra-mcp

# Download release artifacts
curl -fsSL -o GhidraMCP-5.0.0.zip https://github.com/bethington/ghidra-mcp/releases/download/v5.0.0/GhidraMCP-5.0.0.zip
curl -fsSL -o bridge_mcp_ghidra.py https://github.com/bethington/ghidra-mcp/releases/download/v5.0.0/bridge_mcp_ghidra.py
curl -fsSL -o requirements.txt https://github.com/bethington/ghidra-mcp/releases/download/v5.0.0/requirements.txt

# Install Python deps
pip install -r requirements.txt

# Install Ghidra extension
unzip -qo GhidraMCP-5.0.0.zip -d $GHIDRA_HOME/Extensions/Ghidra/GhidraMCP
```

### 3. Clone this repo (launcher + config)

```bash
git clone https://github.com/coffeegrind123/ghidra-in-claude-code.git
cd ghidra-in-claude-code
chmod +x launch_ghidra_mcp.py
```

### 4. Configure Claude Code

```bash
claude mcp add ghidra -s user -- python3 /path/to/launch_ghidra_mcp.py
```

Or edit `~/.claude/.claude.json` directly:

```json
{
  "mcpServers": {
    "ghidra": {
      "command": "python3",
      "args": ["/path/to/launch_ghidra_mcp.py"],
      "env": {
        "GHIDRA_HOME": "/opt/ghidra_12.0.3_PUBLIC",
        "JAVA_HOME": "/opt/jdk-21"
      }
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JAVA_HOME` | Auto-detected | JDK 21+ installation |
| `GHIDRA_HOME` | Auto-detected | Ghidra installation directory |
| `GHIDRA_MCP_PORT` | `8089` | Port for the headless server |
| `GHIDRA_MCP_DIR` | Script directory | Directory containing bridge + JAR |

## Usage

### Loading a binary

Binaries are loaded via the headless server's HTTP API (not an MCP tool):

```bash
curl -s -X POST http://127.0.0.1:8089/load_program -d "file=/absolute/path/to/binary.exe"
```

Or ask Claude: *"Load /tmp/malware.dll into Ghidra and analyze it"*

### Example session

```
$ claude

You: Load /tmp/RegMaster.dll and document all exported functions

Claude: [loads binary, runs analysis, documents using V5 protocol]
  - list_exports → finds Meta_Query, Meta_Attach, GetEntityAPI2
  - decompile_function → reverse engineers each export
  - rename_function → PascalCase names with collision checking
  - set_function_prototype → typed prototypes
  - batch_set_comments → plate + inline comments
  - analyze_function_completeness → verify documentation quality
```

## What Changed in v5.0.0

### Breaking Changes from v4.2.0

| Change | Before | After |
|--------|--------|-------|
| `batch_rename_variables` | Old name | **Renamed** to `rename_variables` |
| `add_struct_field` | `insertAtOffset` | `replaceAtOffset` (overlays undefined bytes) |
| `set_local_variable_type` | Accepted no-ops | **Rejects** undefined→undefined |
| Struct field names | Pass-through | **Auto-prefixed** with Hungarian notation |

### New Features
- **Naming convention enforcement** — PascalCase functions, Hungarian variables, auto-fix struct prefixes
- **Completeness scoring redesign** — log-scaled budgets, tiered plate scoring, effective score
- **`set_variables`** — atomic type + rename in one transaction
- **`check_tools`** — verify if tools are callable
- **Dynamic tool registration** — bridge fetches `/mcp/schema` at startup, auto-registers all tools

See [GhidraMCP CHANGELOG](https://github.com/bethington/ghidra-mcp/blob/main/CHANGELOG.md) for full details.

## License

Scripts in this repo are MIT licensed. Ghidra is Apache 2.0. GhidraMCP — see [bethington/ghidra-mcp](https://github.com/bethington/ghidra-mcp).
