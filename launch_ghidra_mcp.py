#!/usr/bin/env python3
"""
Ghidra MCP launcher — starts headless Ghidra server + MCP bridge.
"""
import glob
import os
import signal
import subprocess
import sys


def find_java_home():
    if os.environ.get("JAVA_HOME") and os.path.isfile(
        os.path.join(os.environ["JAVA_HOME"], "bin", "java")
    ):
        return os.environ["JAVA_HOME"]
    try:
        result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
        output = result.stderr or result.stdout or ""
        import re
        match = re.search(r'version "(\d+)', output)
        if match and int(match.group(1)) >= 21:
            which = subprocess.run(["which", "java"], capture_output=True, text=True, timeout=5)
            if which.returncode == 0:
                real = os.path.realpath(which.stdout.strip())
                home = os.path.dirname(os.path.dirname(real))
                if os.path.isfile(os.path.join(home, "bin", "java")):
                    return home
    except Exception:
        pass
    return None


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_DIR = os.environ.get("GHIDRA_MCP_DIR", SCRIPT_DIR)
PORT = os.environ.get("GHIDRA_MCP_PORT", "8089")

JAVA_HOME = find_java_home()
if not JAVA_HOME:
    print("Error: JDK 21+ not found. Set JAVA_HOME or install Java 21+.", file=sys.stderr)
    sys.exit(1)

GHIDRA_HOME = os.environ.get("GHIDRA_HOME", "")
if not GHIDRA_HOME or not os.path.isdir(GHIDRA_HOME):
    print("Error: GHIDRA_HOME not set or invalid.", file=sys.stderr)
    sys.exit(1)

os.environ["JAVA_HOME"] = JAVA_HOME
os.environ["GHIDRA_HOME"] = GHIDRA_HOME
os.environ["PATH"] = os.path.join(JAVA_HOME, "bin") + ":" + os.environ.get("PATH", "")

# Build flat classpath from all Ghidra jars + extension
classpath = []
for pattern in [
    os.path.join(GHIDRA_HOME, "Ghidra", "Framework", "*", "lib", "*.jar"),
    os.path.join(GHIDRA_HOME, "Ghidra", "Features", "*", "lib", "*.jar"),
    os.path.join(GHIDRA_HOME, "Ghidra", "Processors", "*", "lib", "*.jar"),
    os.path.join(GHIDRA_HOME, "Extensions", "Ghidra", "GhidraMCP", "lib", "*.jar"),
]:
    classpath.extend(sorted(glob.glob(pattern)))

if not classpath:
    print("Error: No Ghidra JARs found. Check GHIDRA_HOME.", file=sys.stderr)
    sys.exit(1)

server_proc = None


def cleanup(*_):
    if server_proc and server_proc.poll() is None:
        server_proc.terminate()
    sys.exit(0)


signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

# Start headless Ghidra MCP server — flat classpath, no Ghidra module system
server_proc = subprocess.Popen(
    [
        os.path.join(JAVA_HOME, "bin", "java"),
        "-Xmx4g",
        "-XX:+UseG1GC",
        "-classpath",
        ":".join(classpath),
        "com.xebyte.headless.GhidraMCPHeadlessServer",
        "--port",
        PORT,
        "--bind",
        "127.0.0.1",
    ],
    stdout=open("/tmp/ghidra-mcp-server.log", "w"),
    stderr=subprocess.STDOUT,
)

# Wait for Java server to be ready (up to 30s)
import socket as _sock
import time as _time

for i in range(60):
    if server_proc.poll() is not None:
        print("Error: Ghidra server exited prematurely. Check /tmp/ghidra-mcp-server.log", file=sys.stderr)
        sys.exit(1)
    try:
        s = _sock.create_connection(("127.0.0.1", int(PORT)), timeout=0.5)
        s.close()
        break
    except (ConnectionRefusedError, OSError):
        _time.sleep(0.5)
else:
    print(f"Error: Ghidra server did not start within 30s on port {PORT}", file=sys.stderr)
    cleanup()

# Run the MCP bridge on stdio
bridge = os.path.join(MCP_DIR, "bridge_mcp_ghidra.py")
if not os.path.isfile(bridge):
    print(f"Error: bridge not found at {bridge}", file=sys.stderr)
    cleanup()

os.execvp(sys.executable, [sys.executable, bridge])
