# Tangled Stats Dashboard

Real-time web dashboard for monitoring Tangled game sessions via WebSocket.

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
tangled-workspace/
├── snowdrop-tangled-agents/      (submodule - game player)
│   └── snowdrop_tangled_agents/
│       └── stats/                (schemas imported from here)
└── tangled-stats-dashboard/      (this directory)
    ├── app.py                    (WebSocket relay server)
    └── static/index.html         (dashboard frontend)
```

The dashboard imports schema definitions from the sibling submodule during development.
In production (Fly.io), the server runs standalone as a simple JSON relay.

## Deployment

### Initial Setup (One Time)

1. **Create Fly.io App**
   ```bash
   cd tangled-stats-dashboard
   fly apps create tangled-stats
   ```

2. **Set Publisher API Key**
   ```bash
   # Generate a secure random key
   fly secrets set PUBLISH_API_KEY="$(openssl rand -hex 32)"

   # Save this key - you'll need it for the game runner
   fly secrets list
   ```

3. **Add GitHub Secret for CI/CD**
   ```bash
   # Create a deploy token
   fly tokens create deploy -x 999999h

   # Add to GitHub: Settings > Secrets > Actions > New repository secret
   # Name: FLY_API_TOKEN
   # Value: <the token from above>
   ```

### Automatic Deployment

Pushing to `main` with changes in `tangled-stats-dashboard/` triggers automatic deployment via GitHub Actions.

### Manual Deployment

```bash
cd tangled-stats-dashboard
fly deploy
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PUBLISH_API_KEY` | API key for game runner auth | `dev-key-change-me` |
| `PORT` | Server port | `8080` |
| `FLASK_DEBUG` | Enable debug mode | `true` (local) / `false` (prod) |

### Fly.io Secrets

Set via `fly secrets set KEY=value`:

- `PUBLISH_API_KEY` - Required for production

## WebSocket Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `/ws/publish` | Game runner pushes stats | API key in first message |
| `/ws/subscribe` | Browsers receive stats | Public (read-only) |

## Development

For the best experience, run Claude Code from the workspace root:

```bash
cd tangled-workspace
claude
```

This gives visibility into both the game player and dashboard codebases.

## Testing the Dashboard

Send a test stats update:

```python
import websocket
import json

ws = websocket.create_connection("ws://localhost:8080/ws/publish")
ws.send(json.dumps({"api_key": "dev-key-change-me"}))
print(ws.recv())  # authenticated

ws.send(json.dumps({
    "type": "stats_update",
    "session": {"run_id": 1, "completed_games": 50, "planned_games": 100},
    "results": {"wins": 20, "draws": 15, "losses": 15},
    "scores": {"avg": 0.5, "median": 0.3, "min": -1.0, "max": 2.0}
}))
```
