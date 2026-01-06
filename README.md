# Plex K3s Media Stack

A Kubernetes (k3s) deployment configuration for a complete media server stack with VPN routing via Gluetun.

**Note**: This repository includes Git submodules for MCP server integrations. See [Cloning with Submodules](#cloning-with-submodules) below.

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

## Cloning with Submodules

This repository includes Git submodules for MCP server integrations:
- [plex-mcp-server](https://github.com/vladimir-tutin/plex-mcp-server) - Plex server MCP integration
- [sonarr-mcp](https://github.com/MichaelReubenDev/sonarr-mcp) - Sonarr MCP integration
- [radarr-mcp](https://github.com/MichaelReubenDev/radarr-mcp) - Radarr MCP integration

### Clone with submodules:

```bash
# Clone the repo with all submodules
git clone --recurse-submodules https://github.com/your-username/plex-k3.git

# Or if you already cloned, initialize submodules:
git submodule update --init --recursive
```

### Updating submodules:

```bash
# Update all submodules to latest versions
git submodule update --remote --merge

# Update specific submodule
git submodule update --remote plex-mcp-server
```

## Quick Start

### Deploy the stack

Create `.env.k3s` with your credentials:
```bash
OPENVPN_USER="your-nordvpn-username"
OPENVPN_PASSWORD="your-nordvpn-password"
PLEX_URL="http://localhost:32400"
PLEX_TOKEN="your-plex-token"
PLEX_CLAIM="your-plex-claim-token"  # from https://www.plex.tv/claim/
```

Then deploy:
```bash
./k8s.py deploy
```

### Check pod status

```bash
./k8s.py status
```

### View logs

```bash
./logs.py <pod-name>              # View all containers in pod
./logs.py <pod-name> <container>  # View specific container
./logs.py -f <pod-name>           # Follow all containers live
./logs.py -f <pod-name> <container>  # Follow specific container live
```

## Kubernetes Utility: `k8s.py`

A unified Python tool for common Kubernetes operations (deployment, pod management, restarts, etc.)

### Usage

```bash
./k8s.py deploy              # Deploy stack with environment variables from .env.k3s
./k8s.py status              # Show pod status and readiness
./k8s.py shell <pod>         # Open interactive shell into a pod
./k8s.py port-forward [service]  # Port forward service (default: qbittorrent)
./k8s.py restart <deployment>    # Restart specific deployment and wait for ready
./k8s.py restart-all         # Restart all deployments
./k8s.py gluetun <pod>       # Restart gluetun sidecar container
./k8s.py gluetun <pod> --full  # Restart entire pod
./k8s.py --help              # Show help
```

### Examples

```bash
# Deploy the stack
./k8s.py deploy

# Check all pods
./k8s.py status

# Open shell into radarr pod
./k8s.py shell radarr

# Port forward qBittorrent WebUI to localhost:8080
./k8s.py port-forward

# Restart radarr and wait for it to be ready
./k8s.py restart radarr

# Restart all deployments and reapply configs
./k8s.py restart-all

# Restart just the VPN sidecar in radarr
./k8s.py gluetun radarr

# Restart entire radarr pod if VPN is stuck
./k8s.py gluetun radarr --full
```

## Logging Tool: `logs.py`

A unified Python tool for viewing Kubernetes pod logs with support for multi-container pods.

### Usage

```bash
./logs.py list                              # List all pods and status
./logs.py <pod-name>                        # Get logs from all containers
./logs.py <pod-name> <container-name>       # Get logs from specific container
./logs.py -f <pod-name>                     # Follow all containers (live)
./logs.py -f <pod-name> <container-name>    # Follow specific container (live)
./logs.py --help                            # Show help
```

### Examples

```bash
# List all pods and their status
./logs.py list

# View all logs from radarr pod (app + gluetun)
./logs.py radarr

# Follow sonarr logs in real-time
./logs.py -f sonarr

# View only the VPN container logs in prowlarr pod
./logs.py indexer-stack gluetun

# Follow VPN container logs in radarr
./logs.py -f radarr gluetun
```

### Output Format

```
=== All Pods and Containers in media-stack ===

POD                                      STATUS       CONTAINERS
────────────────────────────────────────────────────────────────────
sonarr-559b7fff89-nvfbt                  Running      sonarr, gluetun
radarr-6bc575977-2jfgx                   Running      radarr, gluetun
indexer-stack-6fc9b9bc55-279mr           Running      prowlarr, jackett, flaresolverr, gluetun
qbittorrent-6f6fcd7454-x9cfk             Running      qbittorrent, gluetun
overseerr-5c85464869-xs7xg               Running      overseerr
plex-fd656f49b-xzhmd                     Running      plex, plex-mcp-server
```

## Common Commands

### Pod Management

```bash
# Get pod status
kubectl get pods -n media-stack

# Restart all deployments
kubectl rollout restart deployment -n media-stack

# Restart specific deployment
kubectl rollout restart deployment <pod-name> -n media-stack

# Execute into a pod
kubectl exec -it -n media-stack <pod-name> -- /bin/bash
```

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

## Configuration

### VPN Setup

1. Get your NordVPN service credentials from [NordVPN's manual configuration dashboard](https://my.nordvpn.com/manual-configuration)
2. Set environment variables before deploying:
   ```bash
   export OPENVPN_USER="your-service-username"
   export OPENVPN_PASSWORD="your-service-password"
   ```
3. Apply the configuration:
   ```bash
   kubectl apply -f k3s-media-stack.yaml
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
| qBittorrent | 8080,6881 | WebUI + torrent protocol |

## Architecture

### Sidecar Pattern

Most services run with a Gluetun VPN sidecar in the same pod, sharing the network namespace:

```
Pod: sonarr
├── sonarr (application)
└── gluetun (VPN tunnel)
    └── NordVPN OpenVPN (New York)
```

Traffic flow: `External → Gluetun VPN → NordVPN → Application`

### Services Without VPN

- **Overseerr**: Direct access (no VPN needed)
- **Plex**: Uses hostNetwork for local discovery

## Storage

- **Config**: PersistentVolumeClaims (1Gi per service, 20Gi for Plex)
- **Media**: HostPath mounts to `/media/hobbylobby/merged/`
- **Transcode**: 10Gi PersistentVolumeClaim for Plex

## Troubleshooting

### Check VPN Status

```bash
# View Gluetun logs in any VPN-routed pod
./logs.py <pod-name> gluetun

# Follow VPN logs
./logs.py -f <pod-name> gluetun
```

### Service Can't Connect Through VPN

1. Check Gluetun logs: `./logs.py <pod-name> gluetun`
2. Verify `FIREWALL_INPUT_PORTS` in pod configuration
3. Ensure NordVPN credentials are set correctly

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod -n media-stack <pod-name>

# View application logs
./logs.py <pod-name>
```

## Files

| File | Purpose |
|------|---------|
| `k3s-media-stack.yaml` | Kubernetes deployments and configurations |
| `nodeport-services.yaml` | NodePort services for external access |
| `k8s.py` | Kubernetes utility (deploy, restart, shell, port-forward, gluetun) |
| `logs.py` | Logging utility for viewing pod/container logs |
| `CLAUDE.md` | Internal documentation for Claude Code |

## Additional Documentation

See `CLAUDE.md` for additional development and architectural notes.
