"""
Tangled Stats Dashboard - WebSocket Relay Server

Accepts stats from authenticated publishers (game runners)
Broadcasts to all connected subscriber clients (browsers)
Supports multiple concurrent game sessions tracked by run_id.
"""

import os
import sys
import json
import secrets
import requests
from datetime import datetime
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

# Disable WebSocket compression and server-initiated pings
# The client pushes data when it has updates - no need for server pings
app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': None}

sock = Sock(app)

# Configuration from environment
PUBLISH_API_KEY = os.environ.get('PUBLISH_API_KEY', 'dev-key-change-me')
TANGLED_GAME_SLACK_WEBHOOK_URL = os.environ.get('TANGLED_GAME_SLACK_WEBHOOK_URL', None)
SESSION_TIMEOUT = 600  # Remove sessions with no update for 10 minutes

# Warn if using default key in production
if os.environ.get('FLY_APP_NAME') and PUBLISH_API_KEY == 'dev-key-change-me':
    print("WARNING: Using default API key in production!")

# State - per-session tracking
subscribers = set()
sessions = {}  # {run_id: {'data': full_state, 'last_win_count': int, 'last_seen': datetime}}


def cleanup_stale_sessions():
    """Remove sessions that haven't sent an update within SESSION_TIMEOUT."""
    now = datetime.utcnow()
    stale = [
        rid for rid, s in sessions.items()
        if (now - s['last_seen']).total_seconds() > SESSION_TIMEOUT
    ]
    for rid in stale:
        del sessions[rid]
        print(f"Session {rid} timed out and removed")


def build_multi_state():
    """Build a multi_state message from all active sessions."""
    cleanup_stale_sessions()
    return {
        'type': 'multi_state',
        'server_timestamp': datetime.utcnow().isoformat() + 'Z',
        'active_sessions': len(sessions),
        'sessions': {str(rid): s['data'] for rid, s in sessions.items()},
    }


@app.route('/')
def index():
    """Serve the single-page dashboard."""
    return send_from_directory('static', 'index.html')


@app.route('/health')
def health():
    """Health check for Fly.io."""
    cleanup_stale_sessions()
    return {
        'status': 'ok',
        'subscribers': len(subscribers),
        'active_sessions': len(sessions),
        'has_data': len(sessions) > 0
    }


@app.route('/api/stats')
def api_stats():
    """REST endpoint to fetch current stats (fallback for WebSocket)."""
    state = build_multi_state()
    if state['active_sessions'] == 0:
        return {'type': 'no_data', 'message': 'No stats available yet'}
    return state


@sock.route('/ws/publish')
def publish(ws):
    """WebSocket endpoint for the game runner (publisher)."""

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

            if data.get('type') == 'full_state':
                # Extract run_id for session tracking
                session_info = data.get('session', {})
                run_id = session_info.get('run_id', 'unknown')

                # Update per-session state
                if run_id not in sessions:
                    sessions[run_id] = {'data': data, 'last_win_count': 0, 'last_seen': datetime.utcnow()}
                    print(f"New session registered: run {run_id}")
                else:
                    sessions[run_id]['data'] = data
                    sessions[run_id]['last_seen'] = datetime.utcnow()

                # Check for new wins (per-session)
                if data.get('results'):
                    check_for_win(data, run_id)

                # Broadcast multi_state to all subscribers
                multi = build_multi_state()
                broadcast_to_subscribers(multi)

                # Log compactly
                move = data.get('move', {})
                board = data.get('board_state', '')
                edges = data.get('edges_colored', 0)
                if move:
                    print(f"[run {run_id}] Edge {edges}/15: E{move.get('edge')}{move.get('color')} board={board}")
                else:
                    print(f"[run {run_id}] Stats update ({len(sessions)} sessions, {len(subscribers)} subs)")

            if data.get('type') == 'move_update':
                # Legacy support - treat as unknown session
                broadcast_to_subscribers(data)
                move = data.get('move', {})
                print(f"Move {move.get('number')}: E{move.get('edge')}{move.get('color')} -> {move.get('score', 0):+.3f}")

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

        # Send current multi-session state to new subscriber
        if sessions:
            ws.send(json.dumps(build_multi_state()))

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


def send_slack_notification(title, message, color='#36a64f', details=None):
    """Send a message to Slack via webhook."""
    if not TANGLED_GAME_SLACK_WEBHOOK_URL:
        return

    try:
        payload = {
            'attachments': [{
                'color': color,
                'title': title,
                'text': message,
            }]
        }

        if details:
            payload['attachments'][0]['fields'] = [
                {
                    'title': k,
                    'value': str(v),
                    'short': True
                }
                for k, v in details.items()
            ]

        requests.post(TANGLED_GAME_SLACK_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Slack notification failed: {e}")


def check_for_win(data, run_id):
    """Check if new wins were recorded for a session and send notification."""
    if run_id not in sessions:
        return

    session_state = sessions[run_id]
    results = data.get('results', {})
    current_wins = results.get('wins', 0)

    if current_wins > session_state['last_win_count']:
        new_wins = current_wins - session_state['last_win_count']
        session_state['last_win_count'] = current_wins

        # Get additional context
        session = data.get('session', {})

        details = {
            'Run': session.get('run_id', '-'),
            'Game': f"{session.get('current_game', '?')}/{session.get('planned_games', '?')}",
            'Total Wins': current_wins,
            'Strategy': session.get('strategy', '-'),
            'Opponent': session.get('opponent', '-'),
        }

        message = f"Won {new_wins} game{'s' if new_wins > 1 else ''}!"
        send_slack_notification(
            title='Tangled Win Alert',
            message=message,
            color='#36a64f',
            details=details
        )


def broadcast_to_subscribers(data):
    """Send data to all connected subscribers."""
    # Add server timestamp if not already present
    if 'server_timestamp' not in data:
        data['server_timestamp'] = datetime.utcnow().isoformat() + 'Z'

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
    print(f"Session timeout: {SESSION_TIMEOUT}s")
    print(f"Schema validation: {'enabled' if STATS_UPDATE_JSON_SCHEMA else 'disabled'}")
    print(f"Slack notifications: {'enabled' if TANGLED_GAME_SLACK_WEBHOOK_URL else 'disabled'}")
    print("=" * 50)
    print()

    app.run(host='0.0.0.0', port=port, debug=debug)
