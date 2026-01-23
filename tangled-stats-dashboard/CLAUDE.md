# Tangled Stats Dashboard - Claude Code Configuration

Real-time web dashboard for monitoring Tangled game sessions via WebSocket.

## Technology Stack

- **Backend**: Python 3.11, Flask, Flask-Sock (WebSocket)
- **Frontend**: Vanilla HTML/CSS/JS (zero dependencies, no build step)
- **Deployment**: Fly.io with Docker

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | Flask WebSocket server |
| `static/index.html` | Single-page frontend (HTML + CSS + JS inline) |
| `fly.toml` | Fly.io deployment config |

## Schema Source

Schemas are defined in the sibling submodule and imported via path manipulation:

```python
import sys
from pathlib import Path

workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root / "snowdrop-tangled-agents"))
from snowdrop_tangled_agents.stats.schemas import STATS_UPDATE_JSON_SCHEMA
```

**Do not duplicate schema definitions here.** Always import from the game player submodule.

## Frontend Guidelines

The frontend must be zero-dependency vanilla JS:
- No React, Vue, Angular, or any framework
- No npm, no build step
- All CSS in a single `<style>` tag
- All JS in a single `<script>` tag
- Hand-coded SVG for the Petersen graph visualization

## WebSocket Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `/ws/publish` | Game runner pushes stats | API key required |
| `/ws/subscribe` | Browsers receive stats | Public (read-only) |

## Development Commands

```bash
# Run locally
python app.py

# Deploy to Fly.io
fly deploy
```

## Implementation Plan

See `../docs/TANGLED_GAME_WEB_MONITOR.md` for the full specification.
