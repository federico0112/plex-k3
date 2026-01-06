#!/usr/bin/env python3
"""
Consolidated Kubernetes logging utility for media-stack
Replaces: logs.sh, logs-follow.sh, logs-list.sh, logs-container.sh
"""

import subprocess
import sys
import json
import argparse
from typing import Optional, List
from pathlib import Path

NAMESPACE = "media-stack"


class KubernetesLogs:
    """Helper class for Kubernetes log operations"""

    def __init__(self, namespace: str = NAMESPACE):
        self.namespace = namespace

    def get_pods(self) -> dict:
        """Get all pods and their containers"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, "-o", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error getting pods: {e.stderr}")
            sys.exit(1)

    def resolve_pod_name(self, service_or_pod: str) -> Optional[str]:
        """Resolve service name or partial pod name to full pod name"""
        # Try service label lookup first
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pod",
                    "-n",
                    self.namespace,
                    f"-l=app={service_or_pod}",
                    "-o",
                    "jsonpath={.items[0].metadata.name}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # Try as full pod name
        try:
            subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pod",
                    "-n",
                    self.namespace,
                    service_or_pod,
                ],
                capture_output=True,
                check=True,
            )
            return service_or_pod
        except subprocess.CalledProcessError:
            pass

        return None

    def get_containers(self, pod_name: str) -> Optional[List[str]]:
        """Get list of containers in a pod"""
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pod",
                    "-n",
                    self.namespace,
                    pod_name,
                    "-o",
                    "jsonpath={.spec.containers[*].name}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            containers = result.stdout.strip().split()
            return containers if containers else None
        except subprocess.CalledProcessError:
            return None

    def get_logs(
        self, pod_name: str, container_name: Optional[str] = None, follow: bool = False
    ) -> None:
        """Get logs from a pod or specific container"""
        cmd = ["kubectl", "logs", "-n", self.namespace, pod_name]

        if container_name:
            cmd.extend(["-c", container_name])

        if follow:
            cmd.append("-f")

        subprocess.run(cmd)

    def list_pods_with_containers(self) -> None:
        """List all pods, their containers, and status"""
        pods = self.get_pods()

        print(f"=== All Pods and Containers in {self.namespace} ===\n")
        print(f"{'POD':<40} {'STATUS':<12} {'CONTAINERS':<40}")
        print("─" * 95)

        for item in pods["items"]:
            pod_name = item["metadata"]["name"]
            pod_status = item["status"]["phase"]
            containers = [c["name"] for c in item["spec"]["containers"]]
            container_str = ", ".join(containers)
            print(f"{pod_name:<40} {pod_status:<12} {container_str:<40}")

        print()

    def logs_all_containers(self, service_or_pod: str, follow: bool = False) -> None:
        """Get logs from all containers in a pod"""
        pod_name = self.resolve_pod_name(service_or_pod)

        if not pod_name:
            self._print_error_and_available_services(service_or_pod)
            sys.exit(1)

        containers = self.get_containers(pod_name)

        if not containers:
            print(f"Error: Pod '{pod_name}' not found or has no containers")
            sys.exit(1)

        print(f"=== Containers in pod: {pod_name} ===")
        for container in containers:
            print(f"  - {container}")
        print()

        for container in containers:
            separator = "━" * 60
            print(separator)
            print(f"Container: {container}")
            print(separator)
            self.get_logs(pod_name, container, follow)
            print()

    def logs_specific_container(
        self, service_or_pod: str, container_name: str, follow: bool = False
    ) -> None:
        """Get logs from a specific container"""
        pod_name = self.resolve_pod_name(service_or_pod)

        if not pod_name:
            self._print_error_and_available_services(service_or_pod)
            sys.exit(1)

        print(f"=== Service: {service_or_pod} | Container: {container_name} ===")
        self.get_logs(pod_name, container_name, follow)

    def _print_error_and_available_services(self, service_or_pod: str) -> None:
        """Print error and list available services"""
        print(f"Error: Service or pod '{service_or_pod}' not found in namespace '{self.namespace}'")
        print()
        print("Available services:")

        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pods",
                    "-n",
                    self.namespace,
                    "-o",
                    "jsonpath={range .items[*]}{.metadata.labels.app}{\"\\n\"}{end}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            services = sorted(set(result.stdout.strip().split("\n")))
            for service in services:
                if service:
                    print(f"  - {service}")
        except subprocess.CalledProcessError:
            print("  (Unable to retrieve available services)")


def main():
    parser = argparse.ArgumentParser(
        description="Kubernetes Logging Tool for media-stack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                      # List all pods and containers
  %(prog)s radarr                    # Get logs from all containers in radarr pod
  %(prog)s -f sonarr                 # Follow sonarr logs in real-time
  %(prog)s prowlarr gluetun          # Get logs from gluetun container in prowlarr pod
  %(prog)s -f radarr gluetun         # Follow gluetun logs in radarr pod

Sidecar Pattern Note:
  Many pods have multiple containers (app + gluetun VPN sidecar)
  Pass 1 argument to see all containers, or 2 arguments to view specific container logs.
        """,
    )

    parser.add_argument(
        "target",
        nargs="*",
        help="'list' to list all pods, or pod name (+ optional container name)",
    )
    parser.add_argument(
        "-f",
        "--follow",
        action="store_true",
        help="Follow logs in real-time",
    )

    args = parser.parse_args()

    # No arguments: show help
    if not args.target:
        parser.print_help()
        sys.exit(0)

    logs = KubernetesLogs(NAMESPACE)

    # Handle 'list' command
    if args.target[0] == "list":
        logs.list_pods_with_containers()
    # Handle pod/container logs
    elif len(args.target) == 1:
        # One argument: get all containers in pod
        logs.logs_all_containers(args.target[0], follow=args.follow)
    elif len(args.target) == 2:
        # Two arguments: get specific container
        logs.logs_specific_container(args.target[0], args.target[1], follow=args.follow)
    else:
        print("Error: Too many arguments")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
