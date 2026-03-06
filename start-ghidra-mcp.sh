#!/bin/bash
# GhidraMCP Headless Server Startup Script (standalone, no MCP bridge)

set -e

export JAVA_HOME="${JAVA_HOME:-/opt/jdk-21.0.10+7}"
export PATH="$JAVA_HOME/bin:$PATH"
export GHIDRA_HOME="${GHIDRA_HOME:-/opt/ghidra_12.0.3_PUBLIC}"

GHIDRA_MCP_DIR="${GHIDRA_MCP_DIR:-$(dirname "$0")/ghidra-mcp}"
GHIDRA_MCP_JAR="${GHIDRA_MCP_JAR:-GhidraMCP-4.2.0.jar}"
PORT="${GHIDRA_MCP_PORT:-8089}"
BIND_ADDRESS="${GHIDRA_MCP_BIND_ADDRESS:-127.0.0.1}"
JAVA_OPTS="${JAVA_OPTS:--Xmx4g -XX:+UseG1GC}"
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

ARGS="--port ${PORT} --bind ${BIND_ADDRESS}"
[ "$#" -gt 0 ] && ARGS="${ARGS} $@"

echo "Starting GhidraMCP Headless Server on ${BIND_ADDRESS}:${PORT}..."
exec java \
    ${JAVA_OPTS} \
    -Dghidra.home=${GHIDRA_HOME} \
    -Dapplication.name=GhidraMCP \
    -classpath "${CLASSPATH}" \
    com.xebyte.headless.GhidraMCPHeadlessServer \
    ${ARGS}
