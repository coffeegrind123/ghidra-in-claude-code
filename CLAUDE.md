# Ghidra MCP Workflow Guide (v5.0.0)

## Loading Binaries

The headless server's `/load_program` is NOT an MCP tool. Load via HTTP:

```bash
curl -s -X POST http://127.0.0.1:8089/load_program -d "file=/absolute/path/to/binary"
```

Then: `run_analysis` + `get_current_program_info`

## Key Rules

1. **Pre-flight**: Always `check_connection` before any work.
2. **Save**: `save_program` after every 5-10 mutations. No auto-save.
3. **Ordering**: `set_function_prototype` WIPES plate comments. All naming/type changes BEFORE comments.
4. **Phantom variables**: `extraout_*`, `in_*` with undefined types — skip, note in plate comment.
5. **Hungarian notation**: All renames use Hungarian prefixes. Types BEFORE renaming.
6. **Name collisions**: `search_functions_enhanced` before `rename_function`.
7. **Context budget**: Always use offset/limit on `batch_decompile` and `list_functions`.
8. **Type normalization**: Use lowercase builtins (uint, ushort, byte) not Windows types (DWORD, USHORT).

## v5.0.0 Breaking Changes

- `batch_rename_variables` is now `rename_variables`
- `add_struct_field` uses `replaceAtOffset` (overlays undefined bytes, doesn't shift)
- `set_local_variable_type` rejects undefined→undefined no-ops
- Struct field names auto-prefixed with Hungarian notation
- New `set_variables` tool: atomic type + rename in one transaction
- New `check_tools` tool: verify if tools are callable

## HTTP Endpoints (not MCP tools)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/load_program` | POST | Load binary from disk |
| `/close_program` | POST | Close a loaded program |
| `/open_project` | POST | Open .gpr project |
| `/close_project` | POST | Close current project |
| `/create_project` | POST | Create new project |

## Tips

- No GUI tools in headless mode (`launch_codebrowser`, `goto_address` will fail)
- Binary loading is HTTP-only — use `curl` or ask Claude to do it
- Dynamic imports (`GetProcAddress`) won't appear in `list_imports` — search string list
- For data xrefs: convert address to little-endian bytes, use `search_byte_patterns`
