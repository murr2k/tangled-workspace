"""
Tangled Stats Dashboard - WebSocket Relay Server

Accepts stats from authenticated publisher (game runner)
Broadcasts to all connected subscriber clients (browsers)
"""

import os
import sys
import json
import secrets
from pathlib import Path
from flask import Flask, send_from_directory
from flask_sock import Sock

# ============================================================
# Optional Schema Import (for validation in development)
# ============================================================

STATS_UPDATE_JSON_SCHEMA = None

def try_import_schemas():
    """Try to import schemas from sibling submodule (development only)."""
    global STATS_UPDATE_JSON_SCHEMA

    repo_root = Path(__file__).parent.resolve()
    workspace_root = repo_root.parent
    main_repo = workspace_root / "snowdrop-tangled-agents"

    if main_repo.exists():
        stats_module = main_repo / "snowdrop_tangled_agents" / "stats"
        if stats_module.exists():
            sys.path.insert(0, str(main_repo))
            try:
                from snowdrop_tangled_agents.stats.schemas import STATS_UPDATE_JSON_SCHEMA as schema
                STATS_UPDATE_JSON_SCHEMA = schema
                print(f"Loaded schemas from {main_repo}")
            except ImportError as e:
                print(f"Schema import failed: {e}")

# Try to load schemas (optional - server works without them)
try_import_schemas()

# ============================================================
# Application
# ============================================================

app = Flask(__name__, static_folder='static')
sock = Sock(app)

# Configuration from environment
PUBLISH_API_KEY = os.environ.get('PUBLISH_API_KEY', 'dev-key-change-me')

# Warn if using default key in production
if os.environ.get('FLY_APP_NAME') and PUBLISH_API_KEY == 'dev-key-change-me':
    print("WARNING: Using default API key in production!")

# State
subscribers = set()
last_stats = None


@app.route('/')
def index():
    """Serve the single-page dashboard."""
    return send_from_directory('static', 'index.html')


@app.route('/health')
def health():
    """Health check for Fly.io."""
    return {
        'status': 'ok',
        'subscribers': len(subscribers),
        'has_data': last_stats is not None
    }


@sock.route('/ws/publish')
def publish(ws):
    """WebSocket endpoint for the game runner (publisher)."""
    global last_stats

    # Authenticate
    try:
        auth_msg = json.loads(ws.receive(timeout=10))
        if auth_msg.get('api_key') != PUBLISH_API_KEY:
            ws.send(json.dumps({'type': 'error', 'message': 'Invalid API key'}))
            return
        ws.send(json.dumps({'type': 'authenticated'}))
        print("Publisher authenticated")
    except Exception as e:
        ws.send(json.dumps({'type': 'error', 'message': str(e)}))
        return

    # Receive and broadcast
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
                print(f"Stats update broadcast to {len(subscribers)} subscribers")

        except Exception as e:
            print(f"Publisher error: {e}")
            break

    print("Publisher disconnected")


@sock.route('/ws/subscribe')
def subscribe(ws):
    """WebSocket endpoint for browser clients (subscribers)."""
    client_id = secrets.token_hex(8)
    subscribers.add(ws)
    print(f"Subscriber {client_id} connected ({len(subscribers)} total)")

    try:
        ws.send(json.dumps({
            'type': 'connected',
            'role': 'subscriber',
            'client_id': client_id
        }))

        if last_stats:
            ws.send(json.dumps(last_stats))

        while True:
            message = ws.receive()
            if message is None:
                break

            data = json.loads(message)
            if data.get('type') == 'ping':
                ws.send(json.dumps({'type': 'pong'}))

    except Exception as e:
        print(f"Subscriber {client_id} error: {e}")
    finally:
        subscribers.discard(ws)
        print(f"Subscriber {client_id} disconnected ({len(subscribers)} remaining)")


def broadcast_to_subscribers(data):
    """Send data to all connected subscribers."""
    message = json.dumps(data)
    dead_sockets = set()

    for ws in subscribers:
        try:
            ws.send(message)
        except Exception:
            dead_sockets.add(ws)

    subscribers.difference_update(dead_sockets)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

    print()
    print("=" * 50)
    print("Tangled Stats Dashboard")
    print("=" * 50)
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"API key: {PUBLISH_API_KEY[:8]}...")
    print(f"Schema validation: {'enabled' if STATS_UPDATE_JSON_SCHEMA else 'disabled'}")
    print("=" * 50)
    print()

    app.run(host='0.0.0.0', port=port, debug=debug)
