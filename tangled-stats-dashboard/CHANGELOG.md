# Changelog

All notable changes to the Tangled Stats Dashboard.

## [2026-01-24]

### Changed
- Display "Game X/Y" showing current game number instead of completed count
- Game counter now shows "1/500" when first game starts, not "0/500"

### Added
- REST fallback endpoint `/api/stats` for polling when WebSocket is delayed
- Refresh button for manual stats polling
- Move display showing edge, color, score, and thinking time
- Vertex coloring from live game state (red/blue ownership)
- Game legend (FM/AFM/Unplayed)

### Fixed
- Disabled server-initiated pings (client pushes data when available)
- New subscribers receive last known state immediately on connect
