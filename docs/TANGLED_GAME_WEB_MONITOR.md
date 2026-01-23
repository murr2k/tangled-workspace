# Live Tangled Stats Dashboard - Implementation Plan

## Overview

A zero-dependency single-page website hosted on Fly.io that displays real-time statistics from Tangled game sessions. Data flows from the local game runner to the server via secure WebSocket (wss:), then broadcasts to connected browser clients.

---

## Repository Strategy

Both projects live in a unified **workspace repository** (`tangled-workspace`) with the game player as a git submodule. This keeps schema synchronization simple—the dashboard imports directly from its sibling directory.

### Repository Structure

```
github.com/murr2k/tangled-workspace/
├── docs/
│   └── TANGLED_GAME_WEB_MONITOR.md   # This plan (workspace-level)
│
├── snowdrop-tangled-agents/          # Submodule - game player
│   └── snowdrop_tangled_agents/
│       └── stats/
│           ├── schemas.py            # Canonical schema definitions
│           └── websocket_publisher.py
│
└── tangled-stats-dashboard/          # Dashboard (tracked directory)
    ├── app.py
    ├── static/index.html
    └── fly.toml
```

### Schema Synchronization

The dashboard imports schemas directly from the sibling submodule:

```python
# tangled-stats-dashboard/app.py
import sys
from pathlib import Path

workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root / "snowdrop-tangled-agents"))
from snowdrop_tangled_agents.stats.schemas import STATS_UPDATE_JSON_SCHEMA
```

**Advantages:**
- Single source of truth for schemas
- No extra sync step—changes visible immediately during development
- Clone with `--recursive` gets everything

### Shared Schema Definition

Create `snowdrop_tangled_agents/stats/schemas.py` in the main repo:

```python
"""
Shared schema definitions for stats WebSocket messages.

This file is the canonical source - the web dashboard syncs from here.
"""

from dataclasses import dataclass
from typing import Optional, List
import json

@dataclass
class SessionInfo:
    session_start: str
    in_progress: bool
    run_id: Optional[int]
    planned_games: int
    completed_games: int

@dataclass
class ResultsInfo:
    wins: int
    draws: int
    losses: int
    abandoned: int

@dataclass
class ScoresInfo:
    avg: float
    median: float
    min: float
    max: float
    std: Optional[float]

@dataclass
class TrendsInfo:
    score_trend: float
    winrate_trend: float
    recent_5: str  # e.g., "WDLLL"

@dataclass
class ModelMetrics:
    avg_entropy: Optional[float]
    avg_top3_hit: Optional[float]
    avg_pred_accuracy: Optional[float]

@dataclass
class CurrentGame:
    game_number: int
    move_number: int
    score: float
    state: str  # 15-char board state, e.g., "GGPP-G--P-GG-P-"

@dataclass
class ETAInfo:
    estimated_end: Optional[str]
    avg_game_duration_sec: Optional[float]

@dataclass
class StatsUpdate:
    """Complete stats update message schema."""
    type: str  # Always "stats_update"
    timestamp: str
    session: SessionInfo
    results: ResultsInfo
    scores: ScoresInfo
    trends: TrendsInfo
    model: ModelMetrics
    current_game: Optional[CurrentGame]
    eta: ETAInfo

# JSON Schema for validation (used by both Python and JavaScript)
STATS_UPDATE_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["type", "timestamp", "session", "results", "scores", "trends"],
    "properties": {
        "type": {"const": "stats_update"},
        "timestamp": {"type": "string", "format": "date-time"},
        "session": {
            "type": "object",
            "required": ["session_start", "in_progress", "planned_games", "completed_games"],
            "properties": {
                "session_start": {"type": "string"},
                "in_progress": {"type": "boolean"},
                "run_id": {"type": ["integer", "null"]},
                "planned_games": {"type": "integer"},
                "completed_games": {"type": "integer"}
            }
        },
        "results": {
            "type": "object",
            "required": ["wins", "draws", "losses", "abandoned"],
            "properties": {
                "wins": {"type": "integer"},
                "draws": {"type": "integer"},
                "losses": {"type": "integer"},
                "abandoned": {"type": "integer"}
            }
        },
        "scores": {
            "type": "object",
            "properties": {
                "avg": {"type": "number"},
                "median": {"type": "number"},
                "min": {"type": "number"},
                "max": {"type": "number"},
                "std": {"type": ["number", "null"]}
            }
        },
        "trends": {
            "type": "object",
            "properties": {
                "score_trend": {"type": "number"},
                "winrate_trend": {"type": "number"},
                "recent_5": {"type": "string", "pattern": "^[WDL]{1,5}$"}
            }
        },
        "model": {
            "type": "object",
            "properties": {
                "avg_entropy": {"type": ["number", "null"]},
                "avg_top3_hit": {"type": ["number", "null"]},
                "avg_pred_accuracy": {"type": ["number", "null"]}
            }
        },
        "current_game": {
            "type": ["object", "null"],
            "properties": {
                "game_number": {"type": "integer"},
                "move_number": {"type": "integer"},
                "score": {"type": "number"},
                "state": {"type": "string", "pattern": "^[GPB-]{15}$"}
            }
        },
        "eta": {
            "type": "object",
            "properties": {
                "estimated_end": {"type": ["string", "null"]},
                "avg_game_duration_sec": {"type": ["number", "null"]}
            }
        }
    }
}

def export_json_schema(path: str = "stats_schema.json"):
    """Export JSON schema for use in other languages/repos."""
    with open(path, 'w') as f:
        json.dump(STATS_UPDATE_JSON_SCHEMA, f, indent=2)
```

---

## Architecture

```
┌─────────────────────┐         wss://tangled-stats.fly.dev/ws/publish
│  Local Game Runner  │ ────────────────────────────────────────────────┐
│  (play_tangled.py)  │         (authenticated publisher)               │
└─────────────────────┘                                                 │
                                                                        ▼
                                                        ┌───────────────────────────┐
                                                        │     Fly.io Server         │
                                                        │  ┌─────────────────────┐  │
                                                        │  │  WebSocket Server   │  │
                                                        │  │  (Python + Flask)   │  │
                                                        │  └─────────────────────┘  │
                                                        └───────────────────────────┘
                                                                        │
                        wss://tangled-stats.fly.dev/ws/subscribe        │
┌─────────────────────┐         (public read-only)                      │
│   Browser Client    │ ◄───────────────────────────────────────────────┘
│   (Vanilla JS)      │
└─────────────────────┘
```

---

## Technology Stack

### Backend (Fly.io Server)
- **Python 3.11** - Backend runtime
- **Flask 3.x** - Lightweight web framework
- **Flask-Sock** - WebSocket support for Flask (uses native `websockets`)
- **No database** - Stateless relay server (last state kept in memory)

### Frontend (Zero Dependencies)
- **HTML5** - Semantic markup
- **CSS3** - Grid, Flexbox, animations, glassmorphism
- **Vanilla ES6+ JavaScript** - WebSocket API, DOM manipulation
- **No build step** - Direct HTML/CSS/JS served as static files

### Infrastructure
- **Fly.io** - Hosting platform with WebSocket support
- **Docker** - Alpine-based container
- **Cloudflare** (optional) - CDN and DDoS protection

---

## Data Schema

### Publisher → Server Message (from game runner)

```json
{
  "type": "stats_update",
  "timestamp": "2026-01-23T09:45:00Z",
  "session": {
    "session_start": "2026-01-23T08:14:00Z",
    "in_progress": true,
    "run_id": 2,
    "planned_games": 750,
    "completed_games": 127
  },
  "results": {
    "wins": 21,
    "losses": 52,
    "draws": 54,
    "abandoned": 0
  },
  "scores": {
    "avg": 0.547,
    "median": 0.329,
    "min": -0.340,
    "max": 4.306,
    "std": 0.781
  },
  "trends": {
    "score_trend": 0.049,
    "winrate_trend": 0.0,
    "recent_5": "LLWLL"
  },
  "model": {
    "avg_entropy": 3.797,
    "avg_top3_hit": 0.284,
    "avg_pred_accuracy": 0.070
  },
  "current_game": {
    "game_number": 128,
    "move_number": 5,
    "score": 0.412,
    "state": "GGPP-G--P-GG-P-"
  },
  "eta": {
    "estimated_end": "2026-01-24T10:23:00Z",
    "avg_game_duration_sec": 120
  }
}
```

### Server → Browser Message (broadcast to subscribers)

Same schema as above, relayed directly.

### Control Messages

```json
{"type": "ping"}
{"type": "pong"}
{"type": "connected", "role": "subscriber", "client_id": "abc123"}
{"type": "error", "message": "Invalid API key"}
```

---

## File Structure

```
tangled-stats-dashboard/
├── Dockerfile
├── fly.toml
├── requirements.txt
├── app.py                    # Flask server with WebSocket handling
├── static/
│   └── index.html            # Single-page frontend (HTML + CSS + JS inline)
└── README.md
```

---

## Backend Implementation Details

### `app.py` - Flask WebSocket Server

```python
"""
Tangled Stats Dashboard - WebSocket Relay Server

Accepts stats from authenticated publisher (game runner)
Broadcasts to all connected subscriber clients (browsers)
"""

import os
import json
import secrets
from datetime import datetime
from flask import Flask, send_from_directory, request
from flask_sock import Sock

app = Flask(__name__, static_folder='static')
sock = Sock(app)

# Configuration
PUBLISH_API_KEY = os.environ.get('PUBLISH_API_KEY', 'dev-key-change-me')

# State
subscribers = set()  # Connected browser WebSocket clients
last_stats = None    # Most recent stats (sent to new subscribers)

@app.route('/')
def index():
    """Serve the single-page dashboard."""
    return send_from_directory('static', 'index.html')

@app.route('/health')
def health():
    """Health check for Fly.io."""
    return {'status': 'ok', 'subscribers': len(subscribers)}

@sock.route('/ws/publish')
def publish(ws):
    """
    WebSocket endpoint for the game runner (publisher).
    Requires API key in first message.
    """
    # First message must be authentication
    try:
        auth_msg = json.loads(ws.receive(timeout=10))
        if auth_msg.get('api_key') != PUBLISH_API_KEY:
            ws.send(json.dumps({'type': 'error', 'message': 'Invalid API key'}))
            return
        ws.send(json.dumps({'type': 'authenticated'}))
    except Exception as e:
        ws.send(json.dumps({'type': 'error', 'message': str(e)}))
        return

    # Receive and broadcast stats
    global last_stats
    while True:
        try:
            message = ws.receive()
            if message is None:
                break

            data = json.loads(message)

            if data.get('type') == 'ping':
                ws.send(json.dumps({'type': 'pong'}))
                continue

            if data.get('type') == 'stats_update':
                last_stats = data
                broadcast_to_subscribers(data)

        except Exception as e:
            print(f"Publisher error: {e}")
            break

@sock.route('/ws/subscribe')
def subscribe(ws):
    """
    WebSocket endpoint for browser clients (subscribers).
    Public read-only access.
    """
    client_id = secrets.token_hex(8)
    subscribers.add(ws)

    try:
        # Send connection confirmation
        ws.send(json.dumps({
            'type': 'connected',
            'role': 'subscriber',
            'client_id': client_id
        }))

        # Send last known stats if available
        if last_stats:
            ws.send(json.dumps(last_stats))

        # Keep connection alive, handle pings
        while True:
            message = ws.receive()
            if message is None:
                break

            data = json.loads(message)
            if data.get('type') == 'ping':
                ws.send(json.dumps({'type': 'pong'}))

    except Exception as e:
        print(f"Subscriber {client_id} disconnected: {e}")
    finally:
        subscribers.discard(ws)

def broadcast_to_subscribers(data):
    """Send data to all connected subscribers."""
    message = json.dumps(data)
    dead_sockets = set()

    for ws in subscribers:
        try:
            ws.send(message)
        except Exception:
            dead_sockets.add(ws)

    # Clean up dead connections
    subscribers.difference_update(dead_sockets)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
```

### `requirements.txt`

```
flask==3.0.0
flask-sock==0.7.0
gunicorn==22.0.0
gevent==24.2.1
gevent-websocket==0.10.1
```

### `Dockerfile`

```dockerfile
FROM python:3.11-alpine

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY static/ static/

# Run with gunicorn for production
EXPOSE 8080
CMD ["gunicorn", "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "--bind", "0.0.0.0:8080", "app:app"]
```

### `fly.toml`

```toml
app = "tangled-stats"
primary_region = "sea"  # Seattle, close to user

[build]

[env]
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = false   # Keep alive for WebSocket
  auto_start_machines = true
  min_machines_running = 1

[[services]]
  protocol = "tcp"
  internal_port = 8080

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [services.concurrency]
    type = "connections"
    hard_limit = 1000
    soft_limit = 500

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

---

## Frontend Implementation Details

### `static/index.html` - Complete Single-Page Dashboard

The frontend should include these visual elements:

#### Layout Structure

```
┌────────────────────────────────────────────────────────────┐
│  TANGLED LIVE STATS                    ● Connected (ws)    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   RUN #2    │  │   127/750   │  │  ETA 14:23  │         │
│  │   Active    │  │   Games     │  │  Tomorrow   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              WIN/DRAW/LOSS BAR                      │   │
│  │  ████████░░░░░░░░░░░░░░░░░░░░░████████████████████   │   │
│  │   21W (16%)      54D (43%)        52L (41%)         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │     CURRENT GAME     │  │      SCORE STATS         │    │
│  │  ┌─────────────────┐ │  │  Avg:    +0.547          │    │
│  │  │   [Petersen     │ │  │  Median: +0.329          │    │
│  │  │    Graph SVG    │ │  │  Min:    -0.340          │    │
│  │  │    with edge    │ │  │  Max:    +4.306          │    │
│  │  │    colors]      │ │  │  StdDev:  0.781          │    │
│  │  └─────────────────┘ │  │                          │    │
│  │  Move 5/8  Score: +0.41│  │  Trend: ↑ +0.049       │    │
│  │  Game 128/750        │  │  Recent: L L W L L       │    │
│  └──────────────────────┘  └──────────────────────────┘    │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              OPPONENT MODEL METRICS                 │   │
│  │  Entropy: 3.80    Top3 Hit: 28.4%    Accuracy: 7%   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                            │
│  Last update: 2 seconds ago                                │
└────────────────────────────────────────────────────────────┘
```

#### Key Frontend Features

1. **Connection Status Indicator**
   - Green dot when connected
   - Red dot when disconnected
   - Auto-reconnect with exponential backoff

2. **Progress Cards**
   - Run ID and status
   - Games completed / planned with progress bar
   - ETA with relative time ("in 14 hours")

3. **Win/Draw/Loss Stacked Bar**
   - Order: Win (green) → Draw (gray) → Loss (red)
   - Rationale: Wins + Draws > 50% means net positive leaderboard progress
   - Percentage labels for each segment
   - Animated transitions on update

4. **Live Petersen Graph Visualization**
   - SVG of the 10-vertex Petersen graph
   - Edges colored based on current game state:
     - Gray: unplayed (-)
     - Green: ferromagnetic (G)
     - Purple: antiferromagnetic (P)
   - Vertex labels (0-9)
   - Edge labels (E0-E14) on hover

5. **Score Statistics Panel**
   - Average, median, min, max, std deviation
   - Trend arrow (↑/↓) with value
   - Recent 5 results as colored badges (W=green, L=red, D=gray)

6. **Opponent Model Metrics**
   - Entropy (lower = more predictable)
   - Top-3 hit rate
   - Prediction accuracy

7. **Time Display**
   - Last update timestamp with "X seconds ago"
   - Session start time
   - Estimated end time

#### CSS Styling Guidelines

```css
/* Color Palette */
:root {
  --bg-dark: #0f0f1a;
  --bg-card: rgba(255, 255, 255, 0.05);
  --accent-green: #10b981;
  --accent-red: #ef4444;
  --accent-purple: #a855f7;
  --accent-blue: #3b82f6;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --glass-border: rgba(255, 255, 255, 0.1);
}

/* Glassmorphism Cards */
.card {
  background: var(--bg-card);
  backdrop-filter: blur(10px);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  padding: 24px;
}

/* Animated Background */
body {
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0f0f1a 100%);
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}
```

#### JavaScript WebSocket Handler

```javascript
class StatsConnection {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.updateConnectionStatus(true);
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'stats_update') {
        this.updateDashboard(data);
      }
    };

    this.ws.onclose = () => {
      this.updateConnectionStatus(false);
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws.close();
    };
  }

  scheduleReconnect() {
    setTimeout(() => {
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay
      );
      this.connect();
    }, this.reconnectDelay);
  }

  updateConnectionStatus(connected) {
    // Update UI indicator
  }

  updateDashboard(stats) {
    // Update all dashboard elements
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const wsUrl = `wss://${window.location.host}/ws/subscribe`;
  new StatsConnection(wsUrl);
});
```

---

## Publisher Client (Local Game Runner Integration)

Add to `snowdrop_tangled_agents/stats/websocket_publisher.py`:

```python
"""
WebSocket publisher for live stats dashboard.

Connects to the Fly.io server and pushes stats updates in real-time.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional
import websocket  # pip install websocket-client

class StatsPublisher:
    """Publishes game stats to the live dashboard."""

    def __init__(
        self,
        server_url: str = None,
        api_key: str = None,
        auto_reconnect: bool = True
    ):
        self.server_url = server_url or os.environ.get(
            'TANGLED_STATS_WS_URL',
            'wss://tangled-stats.fly.dev/ws/publish'
        )
        self.api_key = api_key or os.environ.get('TANGLED_STATS_API_KEY')
        self.auto_reconnect = auto_reconnect
        self.ws = None
        self.connected = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Establish WebSocket connection and authenticate."""
        if not self.api_key:
            print("Warning: No API key configured for stats publisher")
            return False

        try:
            self.ws = websocket.create_connection(
                self.server_url,
                timeout=10
            )

            # Authenticate
            self.ws.send(json.dumps({'api_key': self.api_key}))
            response = json.loads(self.ws.recv())

            if response.get('type') == 'authenticated':
                self.connected = True
                return True
            else:
                print(f"Auth failed: {response}")
                return False

        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def publish(self, stats: dict):
        """Publish stats update to dashboard."""
        if not self.connected:
            if self.auto_reconnect:
                self.connect()
            if not self.connected:
                return

        try:
            message = {
                'type': 'stats_update',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                **stats
            }
            with self._lock:
                self.ws.send(json.dumps(message))
        except Exception as e:
            print(f"Publish failed: {e}")
            self.connected = False

    def close(self):
        """Close the connection."""
        if self.ws:
            self.ws.close()
            self.connected = False
```

### Integration with `play_tangled.py`

Add publishing to the game loop:

```python
# At start of main()
publisher = None
if os.environ.get('TANGLED_STATS_API_KEY'):
    from snowdrop_tangled_agents.stats.websocket_publisher import StatsPublisher
    publisher = StatsPublisher()
    publisher.connect()

# After each game completes, publish stats
if publisher:
    stats = get_session_stats()
    publisher.publish({
        'session': {
            'session_start': stats.session_start,
            'in_progress': stats.in_progress,
            'run_id': run_id,
            'planned_games': total_planned,
            'completed_games': stats.completed_games
        },
        'results': {
            'wins': stats.wins,
            'losses': stats.losses,
            'draws': stats.draws,
            'abandoned': abandoned_count
        },
        # ... etc
    })
```

---

## Deployment Steps

### 1. Initial Fly.io Setup

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app
fly apps create tangled-stats

# Set secrets
fly secrets set PUBLISH_API_KEY="$(openssl rand -hex 32)"
```

### 2. Deploy

```bash
# From the tangled-stats-dashboard directory
fly deploy
```

### 3. Configure Local Publisher

```bash
# Add to .env file
TANGLED_STATS_WS_URL=wss://tangled-stats.fly.dev/ws/publish
TANGLED_STATS_API_KEY=<the key from fly secrets>
```

---

## Security Considerations

1. **Publisher Authentication**
   - API key required for publishing
   - Key stored in Fly.io secrets (not in code)
   - Key transmitted only on initial WebSocket connection

2. **Subscriber Access**
   - Public read-only (no auth required)
   - No sensitive data exposed (just game stats)

3. **Transport Security**
   - WSS (WebSocket Secure) only
   - TLS 1.3 via Fly.io edge

4. **Rate Limiting**
   - Fly.io handles connection limits
   - Publisher sends at most 1 update per second

---

## Testing Checklist

- [ ] Server starts and serves index.html
- [ ] Health endpoint returns OK
- [ ] Publisher can authenticate with valid key
- [ ] Publisher rejected with invalid key
- [ ] Subscriber receives last_stats on connect
- [ ] Stats broadcast to all subscribers
- [ ] Subscriber auto-reconnects on disconnect
- [ ] Petersen graph SVG renders correctly
- [ ] All stats fields update in UI
- [ ] Mobile responsive layout works
- [ ] Connection status indicator accurate

---

## Petersen Graph SVG Reference

The Petersen graph has 10 vertices and 15 edges:

```
Vertices:
  Inner (0-4): Form a pentagram (star pattern)
  Outer (5-9): Form a pentagon

  V5 = left outer (our vertex - red)
  V6 = top outer (hub)
  V7 = right outer (opponent vertex - blue)

Edges (sorted pairs):
  E0: (0,2)   E5: (1,7)   E10: (5,6)
  E1: (0,3)   E6: (2,4)   E11: (5,9)
  E2: (0,6)   E7: (2,8)   E12: (6,7)
  E3: (1,3)   E8: (3,9)   E13: (7,8)
  E4: (1,4)   E9: (4,5)   E14: (8,9)
```

SVG coordinates (matching website layout):

```javascript
const VERTICES = {
  0: {x: 451, y: 213},  // inner top
  1: {x: 619, y: 289},  // inner right
  2: {x: 553, y: 412},  // inner bottom-right
  3: {x: 347, y: 412},  // inner bottom-left
  4: {x: 281, y: 289},  // inner left
  5: {x: 80,  y: 248},  // outer left (US)
  6: {x: 451, y: 80},   // outer top (HUB)
  7: {x: 820, y: 248},  // outer right (OPP)
  8: {x: 679, y: 520},  // outer bottom-right
  9: {x: 221, y: 520},  // outer bottom-left
};
```

---

## Future Enhancements (Out of Scope for v1)

- Historical game replay
- Multiple concurrent sessions
- User authentication for private dashboards
- Grafana embedding for long-term trends
- Mobile push notifications on milestones
- Sound effects for wins/losses
