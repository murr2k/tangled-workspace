# Tangled Stats Dashboard

Real-time web dashboard for monitoring Tangled game sessions.

## Quick Start

This dashboard is part of the `tangled-workspace` repo. Clone the workspace (not this directory alone):

```bash
git clone --recursive https://github.com/murr2k/tangled-workspace.git
cd tangled-workspace/tangled-stats-dashboard
```

If you already cloned without `--recursive`:
```bash
git submodule update --init --recursive
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
python app.py
```

Open http://localhost:8080

## Architecture

```
tangled-workspace/                    (this repo)
├── snowdrop-tangled-agents/          (submodule - game player)
│   └── snowdrop_tangled_agents/
│       └── stats/                    ← schemas imported from here
└── tangled-stats-dashboard/          (dashboard)
    └── app.py                        ← imports from sibling
```

The dashboard imports schema definitions directly from the sibling `snowdrop-tangled-agents` submodule. No symlinks needed.

## Validate Setup

```bash
python scripts/validate.py
```

## Deploy to Fly.io

```bash
fly auth login
fly launch
fly secrets set PUBLISH_API_KEY="$(openssl rand -hex 32)"
fly deploy
```

## Development

For the best experience, run Claude Code from the workspace root:

```bash
cd tangled-workspace
claude
```

This gives visibility into both the game player and dashboard codebases.
