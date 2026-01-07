# Plex K3s Media Stack

A Kubernetes (k3s) deployment configuration for a complete media server stack with VPN routing via Gluetun.

**Note**: This repository includes Git submodules for MCP server integrations. See [Cloning with Submodules](#cloning-with-submodules) below.

## Table of Contents

- [Services](#services)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Tools](#tools)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Backup & Recovery](#backup--recovery)
- [Files Reference](#files-reference)

## Services

- **Plex**: Media server (hostNetwork, no VPN)
- **Sonarr**: TV show management (VPN routed via Gluetun)
- **Radarr**: Movie management (VPN routed via Gluetun)
- **Prowlarr**: Indexer manager (VPN routed via Gluetun)
- **Jackett**: Indexer proxy (VPN routed via Gluetun)
- **qBittorrent**: Torrent client (VPN routed via Gluetun)
- **Overseerr**: Media request management (direct access)
- **FlareSolverr**: Cloudflare bypass proxy (VPN routed via Gluetun)
- **Gluetun**: VPN container (NordVPN OpenVPN, New York)

## Quick Start

### 1. Clone with submodules

```bash
# Clone the repo with all submodules
git clone --recurse-submodules https://github.com/your-username/plex-k3.git
cd plex-k3
```

### 2. Create environment file

```bash
cat > .env.k3s << 'EOF'
OPENVPN_USER="your-nordvpn-username"
OPENVPN_PASSWORD="your-nordvpn-password"
PLEX_URL="http://localhost:32400"
PLEX_TOKEN="your-plex-token"
PLEX_CLAIM="your-plex-claim-token"
EOF
```

### 3. Deploy

```bash
./k8s.py deploy
```

### 4. Verify and access

```bash
# Check pod status
./k8s.py status

# View logs
./logs.py list

# Access services at NodePorts
# Plex: http://localhost:32400
# Overseerr: http://localhost:30055
# Sonarr: http://localhost:30989
# Radarr: http://localhost:30878
```

## Installation

### Prerequisites

- Kubernetes (k3s) cluster running
- `kubectl` configured
- Python 3.6+ (for helper scripts)
- `gettext-base` (for envsubst):
  ```bash
  sudo apt-get install -y gettext-base
  ```

### Cloning with Submodules

This repository includes Git submodules:
- [plex-mcp-server](https://github.com/vladimir-tutin/plex-mcp-server) - Plex MCP integration
- [sonarr-mcp](https://github.com/MichaelReubenDev/sonarr-mcp) - Sonarr MCP integration
- [radarr-mcp](https://github.com/MichaelReubenDev/radarr-mcp) - Radarr MCP integration

```bash
# Clone with all submodules
git clone --recurse-submodules https://github.com/your-username/plex-k3.git

# If you already cloned, initialize submodules:
git submodule update --init --recursive
```

### Updating submodules

```bash
# Update all submodules to latest
git submodule update --remote --merge

# Update specific submodule
git submodule update --remote plex-mcp-server
```

### Configure Credentials

Create `.env.k3s` with your actual credentials:

```bash
nano .env.k3s
```

**Required credentials:**
- `OPENVPN_USER`: Your NordVPN username (from [NordVPN manual config dashboard](https://my.nordvpn.com/manual-configuration))
- `OPENVPN_PASSWORD`: Your NordVPN password
- `PLEX_URL`: Plex server URL (e.g., `http://localhost:32400`)
- `PLEX_TOKEN`: Found in Plex Web App → Settings → Account → X-Plex-Token (from browser dev tools)
- `PLEX_CLAIM`: Generate fresh at https://www.plex.tv/claim/ (expires in 4 minutes)

**Optional settings:**
- `TZ`: Timezone (default: America/New_York)
- `PUID`/`PGID`: Linux user/group IDs (default: 1000)

### Deploy the stack

```bash
./k8s.py deploy
```

Verify pods are running:
```bash
kubectl get pods -n media-stack
```

## Tools

### k8s.py - Kubernetes Utility

A unified tool for deployment, pod management, and VPN troubleshooting.

**Usage:**
```bash
./k8s.py deploy              # Deploy stack with env variables from .env.k3s
./k8s.py status              # Show pod status and readiness
./k8s.py shell <pod>         # Open interactive shell into a pod
./k8s.py port-forward [service]  # Port forward service (default: qbittorrent)
./k8s.py restart <deployment>    # Restart specific deployment
./k8s.py restart-all         # Restart all deployments with config reapply
./k8s.py gluetun <pod>       # Restart gluetun sidecar container
./k8s.py gluetun <pod> --full  # Restart entire pod
./k8s.py --help              # Show help
```

**Examples:**
```bash
# Deploy the stack
./k8s.py deploy

# Check all pods
./k8s.py status

# Open shell into radarr pod
./k8s.py shell radarr

# Port forward qBittorrent WebUI to localhost:8080
./k8s.py port-forward

# Restart radarr and wait for ready
./k8s.py restart radarr

# Restart all deployments
./k8s.py restart-all

# Fix stuck VPN sidecar
./k8s.py gluetun radarr
```

### logs.py - Logging Tool

A unified tool for viewing pod and container logs with support for multi-container pods (sidecars).

**Usage:**
```bash
./logs.py list                              # List all pods and status
./logs.py <pod-name>                        # Get logs from all containers
./logs.py <pod-name> <container-name>       # Get logs from specific container
./logs.py -f <pod-name>                     # Follow all containers (live)
./logs.py -f <pod-name> <container-name>    # Follow specific container (live)
./logs.py --help                            # Show help
```

**Examples:**
```bash
# List all pods
./logs.py list

# View all logs from radarr pod (app + gluetun)
./logs.py radarr

# Follow sonarr logs in real-time
./logs.py -f sonarr

# View only VPN container logs in prowlarr
./logs.py indexer-stack gluetun

# Follow VPN logs in radarr
./logs.py -f radarr gluetun
```

## Configuration

### Service Ports (NodePort)

| Service | Port | Purpose |
|---------|------|---------|
| Plex | 32400 | Media streaming |
| Overseerr | 30055 | Media requests |
| Sonarr | 30989 | TV management |
| Radarr | 30878 | Movie management |
| Prowlarr | 30696 | Indexer manager |
| Jackett | 30670 | Indexer proxy |
| qBittorrent | 30080 | Torrent WebUI |

### VPN Setup

1. Get your NordVPN service credentials from [NordVPN's manual configuration dashboard](https://my.nordvpn.com/manual-configuration)
2. Set environment variables in `.env.k3s`:
   ```bash
   OPENVPN_USER="your-service-username"
   OPENVPN_PASSWORD="your-service-password"
   ```
3. Deploy:
   ```bash
   ./k8s.py deploy
   ```

### Firewall Configuration

Gluetun sidecars use `FIREWALL_INPUT_PORTS` to allow inbound traffic:

| Service | Ports | Notes |
|---------|-------|-------|
| Sonarr | 8989 | WebUI |
| Radarr | 7878 | WebUI |
| Prowlarr | 9696 | WebUI |
| Jackett | 9117 | WebUI |
| FlareSolverr | 8191 | Proxy |
| qBittorrent | 8080,6881 | WebUI + torrent protocol (TCP/UDP) |

### Updating Deployment

```bash
# Update environment variables
nano .env.k3s

# Reapply configuration
./k8s.py deploy

# Or just restart pods if no secret changes
./k8s.py restart-all --no-config
```

## Architecture

### Sidecar Pattern

Most services run with a Gluetun VPN sidecar in the same pod, sharing the network namespace:

```
Pod: sonarr
├── sonarr (application)
└── gluetun (VPN tunnel)
    └── NordVPN OpenVPN (New York)
```

Traffic flow: `External → Pod → Gluetun VPN → NordVPN → Application`

### Services Without VPN

- **Overseerr**: Direct access (no VPN needed)
- **Plex**: Uses hostNetwork for local discovery

### Storage

- **Config**: PersistentVolumeClaims (1Gi per service, 20Gi for Plex)
- **Media**: HostPath mounts to `/media/hobbylobby/merged/`
- **Transcode**: 10Gi PersistentVolumeClaim for Plex

Local configuration and state (`configs/` directory) is excluded from git and created on first run.

## Troubleshooting

### Services Not Connecting Through VPN

1. Check Gluetun logs:
   ```bash
   ./logs.py <pod-name> gluetun
   ```

2. Verify VPN credentials in `.env.k3s`:
   ```bash
   cat .env.k3s | grep OPENVPN
   ```

3. Check firewall configuration:
   - Verify `FIREWALL_INPUT_PORTS` in `k3s-media-stack.yaml`
   - For qBittorrent: should include `8080,6881`

4. Restart VPN sidecar:
   ```bash
   ./k8s.py gluetun <pod-name>
   ```

### Media Files Not Accessible

- Verify media directory exists:
  ```bash
  ls -la /media/hobbylobby/merged/{movies,tv,torrents}
  ```

- Check hostPath mounts in `k3s-media-stack.yaml`
- Verify file permissions

### Plex Not Accessible

- Plex needs valid `PLEX_CLAIM` token to initialize
- Generate fresh token at https://www.plex.tv/claim/ (4 minute expiry)
- For subsequent deployments, `PLEX_CLAIM` is optional if data persists

Check Plex logs:
```bash
./logs.py plex
```

### Pod Not Starting

```bash
# Check pod events and status
kubectl describe pod -n media-stack <pod-name>

# View application logs
./logs.py <pod-name>

# For VPN-routed pods, check gluetun specifically
./logs.py <pod-name> gluetun
```

### API Key Issues in Services

- Sonarr/Radarr/Prowlarr API keys are stored in `configs/` directory
- If `configs/` is deleted, services generate new API keys on startup
- Update Overseerr integration keys after config reset

### Manual kubectl Operations

```bash
# Get pod status
kubectl get pods -n media-stack

# Restart all deployments
kubectl rollout restart deployment -n media-stack

# Restart specific deployment
kubectl rollout restart deployment <deployment-name> -n media-stack

# Execute into a pod
kubectl exec -it -n media-stack <pod-name> -- /bin/bash

# Describe a pod
kubectl describe pod -n media-stack <pod-name>
```

## Backup & Recovery

### Backup Configuration

```bash
# Backup all service configurations
tar -czf ~/media-stack-backup-$(date +%Y%m%d).tar.gz \
  configs/
```

### Restore from Backup

```bash
# Restore backed up configurations
tar -xzf ~/media-stack-backup-20240101.tar.gz
```

### PersistentVolume Recovery

For Kubernetes persistent data:

```bash
# Export pod data (example for Plex)
kubectl exec -n media-stack <plex-pod-name> -- tar -czf - /config | gzip > plex-config-backup.tar.gz
```

## Security

### Environment Variables

- **NEVER commit `.env` or `.env.k3s` files to git** - They contain sensitive credentials
- `.env` files are automatically excluded by `.gitignore`
- Keep your credentials private and never share them in public repositories

### Plex Tokens

- **PLEX_CLAIM**: Generate fresh at https://www.plex.tv/claim/ each time
- **PLEX_TOKEN**: Found in Plex Web App settings, unique to your account
- These tokens grant access to your Plex server - protect them carefully

### Configuration Directory

- The `configs/` directory is excluded from git as it contains:
  - Service API keys (Sonarr, Radarr, Prowlarr, Overseerr)
  - Plex database and metadata
  - Service configuration files
- Backup `configs/` regularly if you customize service settings

## Getting Help

For configuration issues:
- Check `CLAUDE.md` for architecture overview
- Review service-specific documentation:
  - [Plex](https://support.plex.tv/)
  - [Sonarr](https://sonarr.tv/)
  - [Radarr](https://radarr.video/)
  - [Prowlarr](https://prowlarr.com/)
  - [Gluetun](https://github.com/qdm12/gluetun)
  - [qBittorrent](https://www.qbittorrent.org/)
  - [Overseerr](https://docs.overseerr.dev/)

## Files Reference

| File | Purpose |
|------|---------|
| `k3s-media-stack.yaml` | Kubernetes deployments, services, and configurations |
| `nodeport-services.yaml` | NodePort services for external access |
| `k8s.py` | Kubernetes utility (deploy, restart, shell, port-forward, gluetun) |
| `logs.py` | Logging utility for viewing pod/container logs |
| `.gitmodules` | Git submodule configuration |
| `CLAUDE.md` | Internal documentation for Claude Code |

## Next Steps

1. Set up integrations in Overseerr with Plex, Radarr, and Sonarr
2. Configure Prowlarr indexers and add to Sonarr/Radarr
3. Set up qBittorrent categories for automatic import
4. Configure notification webhooks in Overseerr
5. Test a media request end-to-end
