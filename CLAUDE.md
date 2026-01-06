# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains deployment configurations for a media server stack using both Docker Compose and Kubernetes (k3s). It also includes Git submodules for MCP server integrations (plex-mcp-server, sonarr-mcp, radarr-mcp).

**Important**: Clone with `git clone --recurse-submodules` to get all submodules.

The stack includes:
- **Plex**: Media server
- **Sonarr**: TV show management
- **Radarr**: Movie management
- **Prowlarr**: Indexer manager
- **Jackett**: Indexer proxy (k3s only)
- **qBittorrent**: Torrent client
- **Overseerr**: Media request management
- **FlareSolverr**: Cloudflare bypass proxy
- **Gluetun**: VPN container for routing traffic

## Key Architecture Concepts

### VPN Routing Strategy

**Docker Compose**: Uses `network_mode: "service:gluetun"` to route all services (except Plex) through the Gluetun VPN container. All ports are exposed via Gluetun.

**Kubernetes**: Uses Gluetun as a sidecar container in each deployment. Each pod contains both the application container and a Gluetun container sharing the network namespace. The `FIREWALL_INPUT_PORTS` environment variable must be configured per-service to allow incoming connections to application ports.

### Storage Architecture

**Docker Compose**:
- Application configs: `/home/hobbylobby/plex-dockers/configs/{service}`
- Media storage: `/media/hobbylobby/Flex1/data/{movies,tv,torrents}`
- Plex transcode: `/home/hobbylobby/plex-dockers/transcode`

**Kubernetes**:
- Application configs: PersistentVolumeClaims (1Gi for most services, 20Gi for Plex config)
- Media storage: hostPath mounts to `/media/hobbylobby/Flex1/data/{movies,tv,torrents}`
- Plex transcode: 10Gi PersistentVolumeClaim

### Networking Differences

**Plex**: Runs with host networking in both environments (Docker: `network_mode: host`, k3s: `hostNetwork: true`) for local network discovery and direct connections.

**Other Services**:
- Docker Compose exposes ports through Gluetun container
- Kubernetes exposes via NodePort services defined in `nodeport-services.yaml`

## Common Commands

### Docker Compose

Start the stack:
```bash
docker-compose up -d
```

Stop the stack:
```bash
docker-compose down
```

View logs for a specific service:
```bash
docker-compose logs -f <service-name>
```

Restart a specific service:
```bash
docker-compose restart <service-name>
```

### Kubernetes (k3s)

**Deploy the stack (use the helper script):**
```bash
./k8s.py deploy
```

**Manage deployments (use the helper script):**
```bash
./k8s.py status                      # Show pod status
./k8s.py restart <deployment>        # Restart specific deployment
./k8s.py restart-all                 # Restart all deployments
./k8s.py gluetun <pod>               # Restart VPN sidecar
./k8s.py shell <pod>                 # Open shell into pod
./k8s.py port-forward [service]      # Port forward service
```

**View logs (using the logging tool):**
```bash
./logs.py list                       # List all pods and containers
./logs.py <pod-name>                 # Get logs from all containers
./logs.py -f <pod-name>              # Follow logs in real-time
./logs.py <pod-name> <container>     # Get logs from specific container
./logs.py -f <pod-name> <container>  # Follow specific container logs
```

Examples:
```bash
./k8s.py status                      # Check all pods
./k8s.py restart radarr              # Restart radarr deployment
./logs.py radarr                     # View all radarr logs
./logs.py -f sonarr                  # Follow sonarr logs live
./logs.py prowlarr gluetun           # View VPN logs in prowlarr
./k8s.py shell sonarr                # Open shell in sonarr pod
./k8s.py gluetun radarr --full       # Restart entire radarr pod
```

Manual kubectl operations:
```bash
# Get pod status
kubectl get pods -n media-stack

# Describe a pod
kubectl describe pod -n media-stack <pod-name>

# Delete and recreate entire stack
kubectl delete namespace media-stack
kubectl apply -f k3s-media-stack.yaml
kubectl apply -f nodeport-services.yaml
```

## Service Ports

### Docker Compose (via Gluetun)
- Overseerr: 5055
- Sonarr: 8989
- Radarr: 7878
- FlareSolverr: 8191
- Prowlarr: 9696
- qBittorrent: 8080 (WebUI), 6881 (torrenting)
- Plex: 32400 (via host network)

### Kubernetes NodePorts
- Overseerr: 30055
- Sonarr: 30989
- Radarr: 30878
- Prowlarr: 30696
- Jackett: 30670
- qBittorrent: 30080
- Plex: 32400 (via hostNetwork)

## Configuration Notes

### VPN Credentials
- **Docker Compose**: Hardcoded in `docker-compose.yml`
- **Kubernetes**: Stored in Secret `vpn-credentials` in namespace `media-stack`
- Provider: NordVPN using OpenVPN

### Environment Variables
All services use:
- `TZ=America/New_York`
- `PUID=1000` and `PGID=1000` (LinuxServer.io images)

### Gluetun Firewall Configuration
When adding services to k3s, ensure `FIREWALL_INPUT_PORTS` includes all application ports. Multiple ports are comma-separated (e.g., `"9696,8191"`).

## Important File Locations

- `docker-compose.yml`: Docker Compose configuration
- `k3s-media-stack.yaml`: Kubernetes deployments, services, and configurations
- `nodeport-services.yaml`: Kubernetes NodePort services for external access
- `k8s.py`: Consolidated Kubernetes utility (deploy, restart, shell, port-forward, gluetun management)
- `logs.py`: Consolidated logging tool for viewing pod and container logs
- `configs/`: Persistent configuration directories for Docker Compose services
- `transcode/`: Plex transcoding directory

## Troubleshooting

### VPN Connection Issues
Check Gluetun logs:
- Docker: `docker-compose logs -f gluetun`
- k3s: `kubectl logs -n media-stack <pod-name> -c gluetun`

### Service Cannot Connect Through VPN
Verify `FIREWALL_INPUT_PORTS` includes the service port in the Gluetun configuration.

### Media Files Not Accessible
Verify hostPath mounts point to `/media/hobbylobby/Flex1/data` and subdirectories exist.
