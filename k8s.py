#!/usr/bin/env python3
"""
Kubernetes utility for media-stack deployment
Consolidates: deploy-k3s.sh, pod-shell.sh, portforward-qbittorrent.sh, restart-pod.sh, restart_pods.sh, restart_gluetun_sidecar.sh
"""

import subprocess
import sys
import os
import time
import argparse
from typing import Optional, List
from pathlib import Path

NAMESPACE = "media-stack"
ENV_FILE = ".env.k3s"


class K8sUtil:
    """Kubernetes utility helper"""

    def __init__(self, namespace: str = NAMESPACE):
        self.namespace = namespace

    def run_kubectl(self, *args, check=True, capture=False):
        """Run kubectl command"""
        cmd = ["kubectl"] + list(args)
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.stdout.strip()
        else:
            return subprocess.run(cmd, check=check)

    def get_deployments(self) -> List[str]:
        """Get list of deployments"""
        output = self.run_kubectl(
            "get", "deployments", "-n", self.namespace, "--no-headers", capture=True
        )
        return [line.split()[0] for line in output.split("\n") if line.strip()]

    def get_pods_for_deployment(self, deployment: str) -> List[str]:
        """Get pods for a deployment"""
        output = self.run_kubectl(
            "get",
            "pods",
            "-n",
            self.namespace,
            f"-l=app={deployment}",
            "-o",
            "jsonpath={.items[*].metadata.name}",
            capture=True,
        )
        return output.split() if output else []

    def get_pod_by_pattern(self, pattern: str) -> Optional[str]:
        """Find pod matching pattern"""
        output = self.run_kubectl(
            "get", "pods", "-n", self.namespace, "-o", "name", capture=True
        )
        for line in output.split("\n"):
            pod_name = line.replace("pod/", "").strip()
            if pattern in pod_name and pod_name:
                return pod_name
        return None

    def pod_has_container(self, pod_name: str, container: str) -> bool:
        """Check if pod has a container"""
        output = self.run_kubectl(
            "get",
            "pod",
            "-n",
            self.namespace,
            pod_name,
            "-o",
            "jsonpath={.spec.containers[*].name}",
            capture=True,
        )
        return container in output.split()

    def wait_for_ready(self, deployment: str, timeout: int = 60) -> bool:
        """Wait for deployment to be ready"""
        for i in range(timeout):
            pods = self.get_pods_for_deployment(deployment)
            if not pods:
                print(f"  ({i+1}/{timeout}) No pods found yet")
                time.sleep(1)
                continue

            output = self.run_kubectl(
                "get",
                "pods",
                "-n",
                self.namespace,
                f"-l=app={deployment}",
                "-o",
                "jsonpath={.items[*].status.conditions[?(@.type==\"Ready\")].status}",
                capture=True,
            )
            ready_count = output.count("True")
            total_count = len(pods)

            if ready_count == total_count and total_count > 0:
                return True

            print(f"  ({i+1}/{timeout}) Ready: {ready_count}/{total_count}")
            time.sleep(1)

        return False


def deploy_command(args):
    """Deploy k3s stack with environment substitution"""
    print("=" * 60)
    print("Deploying Media Stack to Kubernetes")
    print("=" * 60)
    print()

    # Check if .env.k3s exists
    if not Path(ENV_FILE).exists():
        print(f"ERROR: {ENV_FILE} file not found!")
        print(f"Please create {ENV_FILE} with your VPN and Plex credentials.")
        print()
        print("Required variables:")
        print("  OPENVPN_USER=<nordvpn-username>")
        print("  OPENVPN_PASSWORD=<nordvpn-password>")
        print("  PLEX_URL=<plex-server-url>")
        print("  PLEX_TOKEN=<plex-token>")
        print("  PLEX_CLAIM=<plex-claim-token>  # from https://www.plex.tv/claim/")
        sys.exit(1)

    # Load and validate environment variables
    env_vars = {}
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key] = value
    except Exception as e:
        print(f"ERROR: Failed to read {ENV_FILE}: {e}")
        sys.exit(1)

    required_vars = ["OPENVPN_USER", "OPENVPN_PASSWORD", "PLEX_TOKEN", "PLEX_CLAIM"]
    missing = [v for v in required_vars if not env_vars.get(v)]

    if missing:
        print(f"ERROR: Missing required variables in {ENV_FILE}:")
        for var in missing:
            print(f"  - {var}")
        sys.exit(1)

    print(f"✓ Loaded environment variables from {ENV_FILE}")
    print()

    # Apply with envsubst
    print("Applying k3s-media-stack.yaml with variable substitution...")
    cmd = f"envsubst < k3s-media-stack.yaml | kubectl apply -f -"
    result = subprocess.run(
        cmd, shell=True, env={**os.environ, **env_vars}, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR: Failed to apply k3s-media-stack.yaml")
        print(result.stderr)
        sys.exit(1)

    print("Applying nodeport-services.yaml...")
    subprocess.run(["kubectl", "apply", "-f", "nodeport-services.yaml"], check=True)

    print()
    print("=" * 60)
    print("Deployment Complete!")
    print("=" * 60)
    print()
    print("Check pod status with:")
    print("  ./k8s.py status")
    print()


def shell_command(args):
    """Open a shell into a pod"""
    k8s = K8sUtil(NAMESPACE)

    # If no argument, list pods
    if not args.pod:
        print(f"Available pods in namespace '{NAMESPACE}':")
        k8s.run_kubectl("get", "pods", "-n", NAMESPACE, "-o", "wide")
        print()
        print("Usage: ./k8s.py shell <pod-name-or-partial-match>")
        print("Example: ./k8s.py shell sonarr")
        return

    # Find pod
    pod_name = k8s.get_pod_by_pattern(args.pod)
    if not pod_name:
        print(f"Error: No pod found matching '{args.pod}'")
        print("Available pods:")
        output = k8s.run_kubectl("get", "pods", "-n", NAMESPACE, "-o", "name", capture=True)
        for line in output.split("\n"):
            if line.strip():
                print(f"  - {line.replace('pod/', '')}")
        sys.exit(1)

    print(f"Connecting to pod: {pod_name}")
    print("Type 'exit' to disconnect")
    print()

    k8s.run_kubectl("exec", "-it", "-n", NAMESPACE, pod_name, "--", "/bin/sh")


def port_forward_command(args):
    """Port forward a service"""
    k8s = K8sUtil(NAMESPACE)

    # Determine service
    if args.service:
        pod_name = k8s.get_pod_by_pattern(args.service)
        if not pod_name:
            print(f"Error: No pod found for service '{args.service}'")
            sys.exit(1)
        ports = args.ports or "8080:8080"
        display_port = ports.split(":")[0]
    else:
        # Default to qBittorrent
        pod_name = k8s.get_pod_by_pattern("qbittorrent")
        if not pod_name:
            print("Error: qBittorrent pod not found")
            sys.exit(1)
        ports = "8080:8080"
        display_port = "8080"

    print(f"Port forwarding {args.service or 'qBittorrent'}...")
    print(f"Pod: {pod_name}")
    print(f"Access at: http://localhost:{display_port}")
    print()
    print("Press Ctrl+C to stop port forwarding")
    print()

    k8s.run_kubectl("port-forward", "-n", NAMESPACE, pod_name, ports)


def restart_command(args):
    """Restart deployment(s)"""
    k8s = K8sUtil(NAMESPACE)

    if not args.deployment:
        print("Usage: ./k8s.py restart <deployment-name>")
        print()
        print("Available deployments:")
        for dep in k8s.get_deployments():
            print(f"  - {dep}")
        return

    deployment = args.deployment

    # Check if deployment exists
    try:
        k8s.run_kubectl("get", "deployment", deployment, "-n", NAMESPACE)
    except subprocess.CalledProcessError:
        print(f"Error: Deployment '{deployment}' not found in namespace '{NAMESPACE}'")
        sys.exit(1)

    print(f"Restarting deployment: {deployment}")
    k8s.run_kubectl("rollout", "restart", "deployment", deployment, "-n", NAMESPACE)

    print("Waiting for pods to be ready...")
    if k8s.wait_for_ready(deployment):
        print()
        print("✓ Deployment restarted successfully!")
        k8s.run_kubectl("get", "pods", "-n", NAMESPACE, "-l", f"app={deployment}")
    else:
        print()
        print("⚠ Timeout waiting for pods to become ready")
        k8s.run_kubectl("get", "pods", "-n", NAMESPACE, "-l", f"app={deployment}")
        sys.exit(1)


def restart_all_command(args):
    """Restart all deployments"""
    k8s = K8sUtil(NAMESPACE)

    # Check if .env.k3s exists
    if Path(ENV_FILE).exists() and not args.no_config:
        print("Applying configurations...")
        env_vars = {}
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value

        cmd = f"envsubst < k3s-media-stack.yaml | kubectl apply -f -"
        subprocess.run(
            cmd, shell=True, env={**os.environ, **env_vars}, check=True
        )
        subprocess.run(["kubectl", "apply", "-f", "nodeport-services.yaml"], check=True)
        print()

    print("Restarting all deployments...")
    k8s.run_kubectl("rollout", "restart", "deployment", "-n", NAMESPACE)

    time.sleep(2)
    print("Watching pod status (Ctrl+C to exit)...")
    k8s.run_kubectl("get", "pods", "-n", NAMESPACE, "-w")


def gluetun_restart_command(args):
    """Restart Gluetun sidecar"""
    k8s = K8sUtil(NAMESPACE)

    if not args.pod:
        print("Usage: ./k8s.py gluetun <pod-name|service-name> [--full]")
        print()
        print("Available pods:")
        output = k8s.run_kubectl("get", "pods", "-n", NAMESPACE, "-o", "name", capture=True)
        for line in output.split("\n"):
            if line.strip():
                print(f"  - {line.replace('pod/', '')}")
        return

    # Resolve service/pod name
    pod_name = args.pod
    if not k8s.run_kubectl("get", "pod", "-n", NAMESPACE, pod_name, check=False).returncode == 0:
        # Try to find pods for this service
        pods = k8s.get_pods_for_deployment(args.pod)
        if not pods:
            print(f"Error: Pod or service '{args.pod}' not found")
            sys.exit(1)

        if len(pods) > 1:
            print(f"Multiple pods found for service '{args.pod}':")
            for p in pods:
                print(f"  - {p}")
            print()
            pod_name = input("Enter pod name (or 'all' to restart all): ").strip()

            if pod_name == "all":
                for p in pods:
                    restart_gluetun_in_pod(k8s, p, args.full)
                return
        else:
            pod_name = pods[0]

    restart_gluetun_in_pod(k8s, pod_name, args.full)


def restart_gluetun_in_pod(k8s: K8sUtil, pod_name: str, full_restart: bool = False):
    """Restart gluetun in a specific pod"""
    # Verify pod exists
    try:
        k8s.run_kubectl("get", "pod", "-n", NAMESPACE, pod_name)
    except subprocess.CalledProcessError:
        print(f"Error: Pod '{pod_name}' not found")
        return

    # Check if gluetun container exists
    if not k8s.pod_has_container(pod_name, "gluetun"):
        print(f"Error: Pod '{pod_name}' does not have a gluetun sidecar")
        return

    if full_restart:
        print(f"Restarting entire pod '{pod_name}'...")
        k8s.run_kubectl("delete", "pod", "-n", NAMESPACE, pod_name)
        print("Pod deleted. Kubernetes will recreate it automatically.")
    else:
        print(f"Restarting gluetun sidecar in pod '{pod_name}'...")
        k8s.run_kubectl(
            "exec", "-n", NAMESPACE, pod_name, "-c", "gluetun", "--", "killall", "gluetun",
            check=False
        )
        print("Gluetun process killed. Container will restart automatically.")


def status_command(args):
    """Show cluster status"""
    k8s = K8sUtil(NAMESPACE)
    print(f"=== Pod Status for {NAMESPACE} ===\n")
    k8s.run_kubectl("get", "pods", "-n", NAMESPACE, "-o", "wide")


def main():
    parser = argparse.ArgumentParser(
        description="Kubernetes utility for media-stack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s deploy              # Deploy stack with env variables from .env.k3s
  %(prog)s status              # Show pod status
  %(prog)s shell sonarr        # Open shell into sonarr pod
  %(prog)s port-forward qbittorrent  # Port forward qBittorrent WebUI
  %(prog)s restart radarr      # Restart radarr deployment
  %(prog)s restart-all         # Restart all deployments
  %(prog)s gluetun sonarr      # Restart gluetun sidecar in sonarr
  %(prog)s gluetun sonarr --full  # Restart entire sonarr pod
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="command to run")

    # Deploy
    subparsers.add_parser("deploy", help="Deploy stack with environment variables")

    # Status
    subparsers.add_parser("status", help="Show pod status")

    # Shell
    shell_parser = subparsers.add_parser("shell", help="Open shell into a pod")
    shell_parser.add_argument("pod", nargs="?", help="Pod name or partial match")

    # Port forward
    pf_parser = subparsers.add_parser("port-forward", help="Port forward a service")
    pf_parser.add_argument("service", nargs="?", default="qbittorrent", help="Service name (default: qbittorrent)")
    pf_parser.add_argument("--ports", help="Ports to forward (e.g., 8080:8080)")

    # Restart
    restart_parser = subparsers.add_parser("restart", help="Restart a deployment")
    restart_parser.add_argument("deployment", nargs="?", help="Deployment name")

    # Restart all
    restart_all_parser = subparsers.add_parser("restart-all", help="Restart all deployments")
    restart_all_parser.add_argument("--no-config", action="store_true", help="Skip config reapply")

    # Gluetun
    gluetun_parser = subparsers.add_parser("gluetun", help="Restart gluetun sidecar")
    gluetun_parser.add_argument("pod", nargs="?", help="Pod name or service name")
    gluetun_parser.add_argument("--full", action="store_true", help="Restart entire pod instead of just gluetun")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "deploy":
        deploy_command(args)
    elif args.command == "status":
        status_command(args)
    elif args.command == "shell":
        shell_command(args)
    elif args.command == "port-forward":
        port_forward_command(args)
    elif args.command == "restart":
        restart_command(args)
    elif args.command == "restart-all":
        restart_all_command(args)
    elif args.command == "gluetun":
        gluetun_restart_command(args)


if __name__ == "__main__":
    main()
