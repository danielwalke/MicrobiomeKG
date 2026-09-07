#!/bin/bash
set -e

WORKSPACE="workspaces/test_workspace"

# --- One-time workspace setup — not needed for now: a pre-built workspace is supplied via the mounted volume ---
# java -jar BioDWH2-v0.6.8d.jar --create "$WORKSPACE"
# <add data source configuration to "$WORKSPACE" here, before --update>
# java -jar BioDWH2-v0.6.8d.jar --update "$WORKSPACE" --skip-update
# java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --create "$WORKSPACE"

# --- Start the Neo4j server from the pre-existing workspace ---
exec java -jar BioDWH2-Neo4j-Server-v1.3.2.jar --start "$WORKSPACE" --port 7474 --bolt-port 7687 
