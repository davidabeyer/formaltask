#!/bin/bash
# cleanup-orphans.sh - Kill orphaned Claude processes and their MCP gateways
#
# Detects:
# 1. Claude processes with PPID=1 (direct orphans)
# 2. Shells (zsh/bash) with PPID=1 that have claude children (orphaned subagent trees)
# 3. MCP gateway processes whose parent is orphaned
#
# Usage:
#   cleanup-orphans.sh           # Dry run - show what would be killed
#   cleanup-orphans.sh --kill    # Actually kill orphaned processes
#   cleanup-orphans.sh --force   # Kill with SIGKILL instead of SIGTERM

set -euo pipefail

DRY_RUN=true
SIGNAL="-TERM"

while [[ $# -gt 0 ]]; do
    case $1 in
        --kill) DRY_RUN=false; shift ;;
        --force) SIGNAL="-9"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

orphan_pids=()
orphan_shells=()

echo -e "${YELLOW}=== Scanning for orphaned Claude processes ===${NC}"

# 1. Find direct orphaned claude processes
while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $1}')
    if [[ -n "$pid" ]]; then
        orphan_pids+=("$pid")
        echo -e "  ${RED}Orphan claude:${NC} PID $pid"
    fi
done < <(/bin/ps -eo pid,ppid,comm 2>/dev/null | awk '$2 == 1 && $3 == "claude" {print $1}')

# 2. Find orphaned shells with claude children
while IFS= read -r shell_pid; do
    if [[ -z "$shell_pid" ]]; then continue; fi

    # Check if this shell has any claude children
    has_claude=$(/bin/ps -eo pid,ppid,comm 2>/dev/null | awk -v p="$shell_pid" '$2 == p && $3 == "claude" {print $1; exit}')

    if [[ -n "$has_claude" ]]; then
        orphan_shells+=("$shell_pid")
        echo -e "  ${RED}Orphan shell tree:${NC} Shell PID $shell_pid with claude children"

        # List all children of this shell
        /bin/ps -eo pid,ppid,comm 2>/dev/null | awk -v p="$shell_pid" '$2 == p {printf "    └─ PID %s (%s)\n", $1, $3}'
    fi
done < <(/bin/ps -eo pid,ppid,comm 2>/dev/null | awk '$2 == 1 && ($3 ~ /zsh/ || $3 ~ /bash/ || $3 == "-/bin/zsh") {print $1}')

# 3. Find MCP gateways whose parent claude is orphaned
echo ""
echo -e "${YELLOW}=== Scanning for orphaned MCP gateways ===${NC}"
mcp_orphans=()

while IFS= read -r line; do
    mcp_pid=$(echo "$line" | awk '{print $1}')
    mcp_ppid=$(echo "$line" | awk '{print $2}')

    if [[ -z "$mcp_pid" ]]; then continue; fi

    # Check if parent is orphaned or dead
    parent_ppid=$(/bin/ps -p "$mcp_ppid" -o ppid= 2>/dev/null | tr -d ' ' || echo "1")

    if [[ "$parent_ppid" == "1" ]]; then
        mcp_orphans+=("$mcp_pid")
        echo -e "  ${RED}Orphan MCP:${NC} PID $mcp_pid (parent $mcp_ppid is orphaned)"
    fi
done < <(/bin/ps -eo pid,ppid,comm 2>/dev/null | grep "dcl_wrapper\|mcp-server" | grep -v grep)

# Summary
total=$((${#orphan_pids[@]} + ${#orphan_shells[@]} + ${#mcp_orphans[@]}))
echo ""
echo -e "${YELLOW}=== Summary ===${NC}"
echo "  Direct orphaned claude: ${#orphan_pids[@]}"
echo "  Orphaned shell trees:   ${#orphan_shells[@]}"
echo "  Orphaned MCP gateways:  ${#mcp_orphans[@]}"
echo "  Total to kill:          $total"

if [[ $total -eq 0 ]]; then
    echo -e "\n${GREEN}No orphaned processes found.${NC}"
    exit 0
fi

if $DRY_RUN; then
    echo -e "\n${YELLOW}Dry run - use --kill to actually terminate processes${NC}"
    exit 0
fi

# Kill processes
echo -e "\n${RED}Killing orphaned processes...${NC}"

# Kill shells first (will cascade to children)
for pid in "${orphan_shells[@]}"; do
    echo "  Killing shell tree PID $pid"
    kill $SIGNAL "$pid" 2>/dev/null || true
done

# Then direct orphans
for pid in "${orphan_pids[@]}"; do
    echo "  Killing claude PID $pid"
    kill $SIGNAL "$pid" 2>/dev/null || true
done

# Then MCP gateways
for pid in "${mcp_orphans[@]}"; do
    echo "  Killing MCP PID $pid"
    kill $SIGNAL "$pid" 2>/dev/null || true
done

sleep 1

# Verify
remaining=$(/bin/ps -eo pid,ppid,comm 2>/dev/null | awk '$2 == 1 && $3 == "claude" {count++} END {print count+0}')
echo -e "\n${GREEN}Done. Remaining orphaned claude processes: $remaining${NC}"
