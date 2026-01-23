# Tangled Workspace - Claude Code Guide

This workspace contains two related projects for the Tangled game.

## Repository Structure

```
tangled-workspace/              (this repo)
├── docs/
│   └── TANGLED_GAME_WEB_MONITOR.md  # Dashboard implementation plan
├── snowdrop-tangled-agents/    (submodule - game player)
└── tangled-stats-dashboard/    (dashboard)
```

## Ownership

| Component | Location | Key Files |
|-----------|----------|-----------|
| Game player | snowdrop-tangled-agents | `play_tangled.py` |
| Stats collection | snowdrop-tangled-agents | `snowdrop_tangled_agents/stats/` |
| Schema definitions | snowdrop-tangled-agents | `snowdrop_tangled_agents/stats/schemas.py` |
| WebSocket publisher | snowdrop-tangled-agents | `snowdrop_tangled_agents/stats/websocket_publisher.py` |
| Dashboard server | tangled-stats-dashboard | `app.py` |
| Dashboard frontend | tangled-stats-dashboard | `static/index.html` |

## Cross-Project Imports

The dashboard imports from the game player (sibling directory):

```python
# In tangled-stats-dashboard/app.py
sys.path.insert(0, str(workspace_root / "snowdrop-tangled-agents"))
from snowdrop_tangled_agents.stats.schemas import STATS_UPDATE_JSON_SCHEMA
```

## Schema Changes

When modifying WebSocket message schemas:

1. Edit `snowdrop-tangled-agents/snowdrop_tangled_agents/stats/schemas.py`
2. Update publisher in game player
3. Update receiver in dashboard
4. Both see changes immediately (sibling import)

## Submodule Workflow

The game player is a submodule. After changes:

```bash
# In snowdrop-tangled-agents
git add . && git commit -m "message" && git push

# In workspace root
git add snowdrop-tangled-agents
git commit -m "Update submodule"
```

## Implementation Plan

The detailed implementation plan for the live stats dashboard is at:
- `docs/TANGLED_GAME_WEB_MONITOR.md` - Architecture, schemas, deployment steps

## Project-Specific Guidance

See individual CLAUDE.md files:
- `snowdrop-tangled-agents/CLAUDE.md` - Game strategies, stats, MATLAB integration
- `tangled-stats-dashboard/CLAUDE.md` - Dashboard server, vanilla JS frontend
