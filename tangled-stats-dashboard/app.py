"""
Tangled Stats Dashboard - WebSocket Relay Server

Accepts stats from authenticated publisher (game runner)
Broadcasts to all connected subscriber clients (browsers)
"""

import os
import sys
from pathlib import Path

# ============================================================
# WORKSPACE VALIDATION
# ============================================================

def setup_imports():
    """Set up imports from sibling submodule."""
    repo_root = Path(__file__).parent.resolve()
    workspace_root = repo_root.parent
    main_repo = workspace_root / "snowdrop-tangled-agents"

    if not main_repo.exists():
        print("=" * 60)
        print("ERROR: Main repo not found")
        print("=" * 60)
        print()
        print(f"Expected: {main_repo}")
        print()
        print("Did you clone with --recursive?")
        print("    git clone --recursive <workspace-repo-url>")
        print()
        print("Or initialize submodules:")
        print("    git submodule update --init --recursive")
        print("=" * 60)
        sys.exit(1)

    # Check for stats module
    stats_module = main_repo / "snowdrop_tangled_agents" / "stats"
    if not stats_module.exists():
        print("=" * 60)
        print("ERROR: Stats module not found")
        print("=" * 60)
        print()
        print("The submodule may be on the wrong branch.")
        print()
        print("Fix with:")
        print(f"    cd {main_repo}")
        print("    git checkout feature/dynamic-learning")
        print("=" * 60)
        sys.exit(1)

    # Add to Python path
    sys.path.insert(0, str(main_repo))


# Run setup before other imports
setup_imports()

# ============================================================
# Application
# ============================================================

import json
import secrets
from flask import Flask, send_from_directory
from flask_sock import Sock

app = Flask(__name__, static_folder='static')
sock = Sock(app)

# Configuration
PUBLISH_API_KEY = os.environ.get('PUBLISH_API_KEY', 'dev-key-change-me')

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
    return {'status': 'ok', 'subscribers': len(subscribers)}


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

        except Exception as e:
            print(f"Publisher error: {e}")
            break


@sock.route('/ws/subscribe')
def subscribe(ws):
    """WebSocket endpoint for browser clients (subscribers)."""
    client_id = secrets.token_hex(8)
    subscribers.add(ws)

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

    subscribers.difference_update(dead_sockets)


if __name__ == '__main__':
    print()
    print("Tangled Stats Dashboard")
    print(f"Publisher API key: {PUBLISH_API_KEY[:8]}...")
    print()
    app.run(host='0.0.0.0', port=8080, debug=True)
