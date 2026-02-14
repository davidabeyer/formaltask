---
name: connection-suggester
description: Automatic background agent that suggests and creates connections between memory-keeper context items using semantic search
---

# Connection Suggester Agent

Automatic background agent that suggests and creates connections between memory-keeper context items using semantic search.

## How It Works

1. **Trigger**: PostToolUse hook fires after every `context_save`
2. **Agent Launch**: Hook spawns `connection-suggester.py` in background
3. **Semantic Search**: Agent searches for related items (similarity > 0.5)
4. **Auto-Link**: High confidence matches (>0.8) are automatically linked
5. **Suggest**: Medium confidence (0.6-0.8) saved for user review

## Installation

### 1. Install MCP Client Library

```bash
pip3 install mcp
```

### 2. Configure Hook

Add to your Claude Code config (`~/.config/claude/config.json`):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "mcp__memory-keeper__context_save",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/agents/connection-suggester.py &",
            "description": "Auto-suggest connections for newly saved items"
          }
        ]
      }
    ]
  }
}
```

**Or** use the pre-configured hook file:

```bash
# Merge with existing config
jq -s '.[0] * .[1]' ~/.config/claude/config.json ~/.claude/agents/connection-suggester-hook.json > /tmp/merged-config.json
mv /tmp/merged-config.json ~/.config/claude/config.json
```

### 3. Test

```bash
# Save a test item
mcp__memory-keeper__context_save(
    key="test-connection-suggester",
    value="This is about memory-keeper hooks and automation",
    category="note"
)

# Check logs
tail -f ~/.claude/hooks/logs/connection-suggester-$(date +%Y%m%d).log
```

## Configuration

Edit `connection-suggester.py` to adjust:

- **minSimilarity**: Currently 0.5 (lower = more connections)
- **topK**: Currently 10 (max connections to consider)
- **Auto-link threshold**: Currently 0.8 (higher = fewer auto-links)

## Logs

Logs are written to: `~/.claude/hooks/logs/connection-suggester-YYYYMMDD.log`

Each run logs:
- Hook data received
- Items found via semantic search
- Connections created
- Any errors

## Architecture

```
context_save
    ↓
PostToolUse Hook
    ↓
Spawn Background Agent (async, non-blocking)
    ↓
Connect to memory-keeper as MCP client
    ↓
Semantic Search (via MCP)
    ↓
Create Links (via MCP)
    ↓
Exit (Claude continues without waiting)
```

## Benefits

- **Automatic**: No manual connection creation
- **Non-blocking**: Runs in background, doesn't slow Claude
- **Intelligent**: Uses semantic similarity, not keywords
- **Configurable**: Thresholds and behavior fully customizable

## Limitations

- Requires `mcp` Python library
- May create duplicate links if run multiple times (no deduplication yet)
- Regex parsing of MCP response may need adjustment based on actual format
- No configurable exclusion patterns yet

## Features Completed

- ✅ Parse semantic search results
- ✅ Auto-link high confidence matches (>0.8 similarity)
- ✅ Save medium confidence suggestions (0.6-0.8) for user review
- ✅ Comprehensive logging
- ✅ Error handling
- ✅ Skip meta items (session summaries, session-start notes)

## TODO

- [ ] Check for existing links before creating duplicates
- [ ] Add configurable exclusion patterns (don't link summaries, etc.)
- [ ] Batch processing mode for backfilling old items
- [ ] User command to review and approve saved suggestions
