# K3s Logging Scripts

Quick reference for logging scripts to inspect containers in your media-stack.

## Scripts

### `logs.sh` - Get logs from all containers in a pod
Get logs from **all containers** in a specific pod (handles sidecar containers like gluetun). Accepts service name or full pod name.

```bash
./logs.sh <service-name>          # Get logs once (e.g., ./logs.sh radarr)
./logs.sh <service-name> f        # Follow logs in real-time
./logs.sh <pod-name>              # Also works with full pod name (e.g., radarr-abc123)
```

**Examples:**
```bash
./logs.sh radarr
./logs.sh sonarr f
./logs.sh prowlarr follow
./logs.sh qbittorrent-xyz789      # Full pod name also works
```

### `logs-follow.sh` - Follow logs from a pod
Convenience wrapper to automatically follow logs from all containers.

```bash
./logs-follow.sh <service-name>   # e.g., ./logs-follow.sh radarr
```

**Examples:**
```bash
./logs-follow.sh radarr
./logs-follow.sh sonarr
./logs-follow.sh qbittorrent
```

### `logs-container.sh` - Get logs from a specific container
Get logs from just one container when a pod has multiple containers (app + gluetun sidecar).

```bash
./logs-container.sh <service-name> <container-name>
./logs-container.sh <service-name> <container-name> f    # Follow logs
```

**Examples:**
```bash
./logs-container.sh radarr radarr              # radarr app logs
./logs-container.sh radarr gluetun             # radarr VPN sidecar logs
./logs-container.sh prowlarr gluetun f         # Follow prowlarr's gluetun logs
```

### `logs-list.sh` - List all pods and containers
Show all available services and their containers in the media-stack namespace.

```bash
./logs-list.sh
```

## Quick Start

**Get logs from a service by name:**
```bash
./logs.sh radarr
./logs.sh sonarr
./logs.sh prowlarr
./logs.sh qbittorrent
./logs.sh overseerr
./logs.sh flaresolverr
./logs.sh plex
```

**Follow logs in real-time:**
```bash
./logs-follow.sh radarr
./logs-follow.sh sonarr
```

**Get logs from a specific container (useful for debugging VPN):**
```bash
./logs-container.sh radarr gluetun
./logs-container.sh sonarr gluetun f
```

## Service Names

All available services:
- `radarr` - Movie management
- `sonarr` - TV show management
- `prowlarr` - Indexer manager
- `qbittorrent` - Torrent client
- `overseerr` - Media request management
- `flaresolverr` - Cloudflare bypass
- `plex` - Media server
- `jackett` - Indexer proxy (k3s only)

## Container Names in Each Pod

Each pod typically has:
- **App container**: Named after the service (e.g., `radarr`, `sonarr`, `qbittorrent`)
- **Gluetun sidecar**: `gluetun` (VPN routing - present in all pods except Plex)
