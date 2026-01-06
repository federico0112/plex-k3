# Media Stack (Kubernetes) Setup Guide

## Initial Setup

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd plex-dockers
```

### 2. Configure Secrets

#### For Kubernetes (k3s):
```bash
cp .env.k3s.example .env.k3s
```

Edit `.env.k3s` with your actual credentials:
```bash
nano .env.k3s
```

**Required credentials:**
- `OPENVPN_USER`: Your NordVPN username (from account settings)
- `OPENVPN_PASSWORD`: Your NordVPN password (from account settings)
- `PLEX_TOKEN`: Find in Plex Web App → Settings → Account → Copy X-Plex-Token from browser dev tools
- `PLEX_CLAIM`: Generate a fresh token at https://www.plex.tv/claim/ (expires in 4 minutes)

**Other settings:**
- `TZ`: Timezone (default: America/New_York)
- `PUID`/`PGID`: Linux user/group IDs (default: 1000)
- `SERVER_COUNTRIES`: VPN country preference
- `FIREWALL_*`: VPN firewall settings

### 3. Deploy

```bash
# First, ensure gettext-base is installed for envsubst
sudo apt-get install -y gettext-base

# Deploy the stack
./deploy-k3s.sh
```

Verify pods are running:
```bash
kubectl get pods -n media-stack
```

View logs for a pod:
```bash
kubectl logs -n media-stack <pod-name>
```

View logs for a sidecar container (e.g., Gluetun VPN):
```bash
kubectl logs -n media-stack <pod-name> -c gluetun
```

### 4. Access Services

#### Service Ports (Kubernetes NodePorts)
- **Overseerr**: localhost:30055
- **Sonarr**: localhost:30989
- **Radarr**: localhost:30878
- **Prowlarr**: localhost:30696
- **Jackett**: localhost:30670
- **qBittorrent**: localhost:30080
- **Plex**: localhost:32400

## Important Notes

### Security
- **NEVER commit .env or .env.k3s files to git** - They contain sensitive credentials
- .env files are automatically excluded by .gitignore
- Keep your credentials private and never share them in public repositories

### Plex Tokens
- **PLEX_CLAIM**: Generate fresh at https://www.plex.tv/claim/ each time you set up
- **PLEX_TOKEN**: Found in Plex Web App settings, unique to your account
- These tokens grant access to your Plex server - protect them carefully

### Configuration Directory
- The `configs/` directory is excluded from git as it contains:
  - Service API keys (Sonarr, Radarr, Prowlarr, Overseerr)
  - Plex database and metadata
  - Service configuration files
- This directory is created automatically on first run
- Backup `configs/` regularly if you customize service settings

### VPN Configuration
- Gluetun (sidecar container) handles VPN routing for most services
- Plex and Overseerr do NOT route through VPN (use direct network)
- VPN credentials are essential for Sonarr, Radarr, Prowlarr, and qBittorrent to function
- If VPN connection fails, check credentials in `.env.k3s`

## Updating Deployment

```bash
# Update environment variables in .env.k3s
nano .env.k3s

# Apply changes
./deploy-k3s.sh

# Or just restart pods if no secret changes
./restart_pods.sh
```

## Troubleshooting

### Services Not Connecting Through VPN
- Verify VPN credentials are correct in `.env.k3s`
- Check Gluetun logs: `kubectl logs <pod-name> -c gluetun`
- Ensure `OPENVPN_USER` and `OPENVPN_PASSWORD` are set
- Verify `FIREWALL_INPUT_PORTS` includes service ports in k3s-media-stack.yaml

### Media Files Not Accessible
- Verify `/media/hobbylobby/Flex1/data/{movies,tv,torrents}` directories exist
- Check directory permissions: `ls -la /media/hobbylobby/Flex1/data/`
- Ensure hostPath mounts in k3s-media-stack.yaml point to correct paths

### Plex Not Accessible
- Plex needs valid PLEX_CLAIM token to initialize
- Generate fresh token at https://www.plex.tv/claim/ (4 minute expiry)
- For subsequent deployments, PLEX_CLAIM is optional if data persists
- Check Plex logs: `kubectl logs <pod-name> -c plex`
- Verify pod is in Running state: `kubectl get pods -n media-stack`

### API Key Issues in Services
- Sonarr/Radarr/Prowlarr API keys are stored in configs/ directory
- If configs/ is deleted, services will generate new API keys on startup
- Update Overseerr integration keys after config reset
- Update any external integrations with new API keys

## Backup & Recovery

### Backup Configuration
```bash
# Backup all service configurations
tar -czf ~/media-stack-backup-$(date +%Y%m%d).tar.gz \
  /home/hobbylobby/plex-dockers/configs \
  /home/hobbylobby/plex-dockers/.env.k3s
```

### Restore from Backup
```bash
# Restore backed up configurations
tar -xzf ~/media-stack-backup-20241230.tar.gz -C /home/hobbylobby/plex-dockers/
```

### PersistentVolume Recovery
For Kubernetes, persistent data is stored in PersistentVolumeClaims. To backup:
```bash
# Export pod data (example for Plex)
kubectl exec -n media-stack <plex-pod-name> -- tar -czf - /config | gzip > plex-config-backup.tar.gz
```

## Getting Help

For configuration issues:
- Check CLAUDE.md for architecture overview
- Review service-specific documentation:
  - [Plex](https://support.plex.tv/)
  - [Sonarr](https://sonarr.tv/)
  - [Radarr](https://radarr.video/)
  - [Prowlarr](https://prowlarr.com/)
  - [Gluetun](https://github.com/qdm12/gluetun)
  - [qBittorrent](https://www.qbittorrent.org/)
  - [Overseerr](https://docs.overseerr.dev/)

## Next Steps

1. Set up integrations in Overseerr with Plex, Radarr, and Sonarr
2. Configure Prowlarr indexers and add to Sonarr/Radarr
3. Set up qBittorrent categories for automatic import
4. Configure notification webhooks in Overseerr
5. Test a media request end-to-end
