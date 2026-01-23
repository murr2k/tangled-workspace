# Tangled Workspace

Development workspace for [Tangled](https://tangled-game.com), a quantum-inspired strategy game where two players compete by coloring edges on graph structures. The game's outcomes are determined by quantum annealing simulation, making optimal play computationally intractable—and strategically fascinating.

This workspace contains:

- **snowdrop-tangled-agents** - Game player, strategies, and stats collection
- **tangled-stats-dashboard** - Real-time web dashboard for monitoring games

## Quick Start

```bash
# Clone with submodules
git clone --recursive https://github.com/murr2k/tangled-workspace.git
cd tangled-workspace
```

The submodule is configured to track the `feature/dynamic-learning` branch automatically.

## Structure

```
tangled-workspace/
├── snowdrop-tangled-agents/    (submodule)
│   ├── play_tangled.py         # Game runner
│   └── snowdrop_tangled_agents/
│       └── stats/              # Stats collection & schemas
└── tangled-stats-dashboard/    (tracked directory)
    ├── app.py                  # WebSocket server
    └── static/index.html       # Dashboard frontend
```

## Development with Claude Code

Run Claude Code from the workspace root for visibility into both projects:

```bash
cd tangled-workspace
claude
```

## Working with Submodules

```bash
# Pull latest changes (workspace + submodules)
git pull
git submodule update --remote

# After making changes in a submodule
cd snowdrop-tangled-agents
git add . && git commit -m "changes"
git push
cd ..
git add snowdrop-tangled-agents
git commit -m "Update submodule reference"
```

## Individual Projects

If you only need the game player:
```bash
git clone https://github.com/murr2k/snowdrop-tangled-agents.git
```

The dashboard requires the workspace (for schema imports from the game player).
