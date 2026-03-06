#!/bin/bash
# Starts the GhidraMCP headless server in background, then runs the MCP bridge on stdio.
# The bridge starts immediately for MCP handshake; Ghidra connection is lazy.

export JAVA_HOME="${JAVA_HOME:-/opt/jdk-21.0.10+7}"
export PATH="$JAVA_HOME/bin:$PATH"
export GHIDRA_HOME="${GHIDRA_HOME:-/opt/ghidra_12.0.3_PUBLIC}"

GHIDRA_MCP_DIR="${GHIDRA_MCP_DIR:-$(dirname "$0")/ghidra-mcp}"
GHIDRA_MCP_JAR="${GHIDRA_MCP_JAR:-GhidraMCP-4.2.0.jar}"
PORT="${GHIDRA_MCP_PORT:-8089}"
JAR_PATH="${GHIDRA_MCP_DIR}/target/${GHIDRA_MCP_JAR}"

CLASSPATH="${JAR_PATH}"
for jar in ${GHIDRA_HOME}/Ghidra/Framework/*/lib/*.jar; do
    CLASSPATH="${CLASSPATH}:${jar}"
done
for jar in ${GHIDRA_HOME}/Ghidra/Features/*/lib/*.jar; do
    CLASSPATH="${CLASSPATH}:${jar}"
done
for jar in ${GHIDRA_HOME}/Ghidra/Processors/*/lib/*.jar; do
    CLASSPATH="${CLASSPATH}:${jar}"
done

existing_pid=$(lsof -ti :${PORT} 2>/dev/null)
if [ -n "$existing_pid" ]; then
    kill $existing_pid 2>/dev/null
    sleep 1
fi

cleanup() {
    [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null
    exit 0
}
trap cleanup EXIT SIGTERM SIGINT

java -Xmx4g -XX:+UseG1GC \
    -Dghidra.home=${GHIDRA_HOME} \
    -Dapplication.name=GhidraMCP \
    -classpath "${CLASSPATH}" \
    com.xebyte.headless.GhidraMCPHeadlessServer \
    --port ${PORT} --bind 127.0.0.1 \
    >/tmp/ghidra-mcp-server.log 2>&1 &
SERVER_PID=$!

exec python3 "${GHIDRA_MCP_DIR}/bridge_mcp_ghidra.py"
