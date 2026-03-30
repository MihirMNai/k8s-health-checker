"""Main scanner — orchestrates all health checks."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

from k8s_health_checker.checks.autoscaling import AutoscalingChecker
from k8s_health_checker.checks.nodes import NodeChecker
from k8s_health_checker.checks.pods import PodChecker
from k8s_health_checker.checks.probes import ProbeChecker
from k8s_health_checker.checks.resources import ResourceChecker
from k8s_health_checker.checks.security import SecurityChecker
from k8s_health_checker.checks.workloads import WorkloadChecker
from k8s_health_checker.models import Category, ClusterSummary, HealthReport

ALL_CHECKERS = [
    PodChecker,
    NodeChecker,
    ResourceChecker,
    ProbeChecker,
    SecurityChecker,
    WorkloadChecker,
    AutoscalingChecker,
]

CATEGORY_MAP = {c.category: c for c in ALL_CHECKERS}


class Scanner:
    """Scans a Kubernetes cluster and produces a HealthReport."""

    def __init__(self) -> None:
        self._core_v1: Optional[client.CoreV1Api] = None
        self._apps_v1: Optional[client.AppsV1Api] = None
        self._autoscaling_v1: Optional[client.AutoscalingV1Api] = None
        self._networking_v1: Optional[client.NetworkingV1Api] = None
        self._rbac_v1: Optional[client.RbacAuthorizationV1Api] = None
        self._cluster_name: str = "unknown"

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Load kubeconfig and initialise API clients."""
        try:
            config.load_kube_config()
        except ConfigException:
            # Try in-cluster config (running inside a pod)
            config.load_incluster_config()

        self._core_v1 = client.CoreV1Api()
        self._apps_v1 = client.AppsV1Api()
        self._autoscaling_v1 = client.AutoscalingV1Api()
        self._networking_v1 = client.NetworkingV1Api()
        self._rbac_v1 = client.RbacAuthorizationV1Api()

        # Try to get cluster name from current context
        try:
            _, active_context = config.list_kube_config_contexts()
            self._cluster_name = active_context.get("context", {}).get(
                "cluster", active_context.get("name", "unknown")
            )
        except Exception:
            self._cluster_name = "unknown"

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan(
        self,
        namespace: Optional[str] = None,
        categories: Optional[List[Category]] = None,
    ) -> HealthReport:
        """Run health checks and return a report.

        Args:
            namespace: Limit scan to a single namespace (None = all).
            categories: Limit to specific check categories (None = all).
        """
        start = time.monotonic()

        report = HealthReport(
            cluster_name=self._cluster_name,
            timestamp=datetime.now(timezone.utc),
        )

        # Gather cluster summary
        report.summary = self._build_summary(namespace)
        report.namespaces_scanned = (
            [namespace] if namespace else self._list_namespaces()
        )

        # Determine which checkers to run
        checkers_to_run = ALL_CHECKERS
        if categories:
            cat_set = set(categories)
            checkers_to_run = [c for c in ALL_CHECKERS if c.category in cat_set]

        # Run each checker
        k8s_clients = {
            "core_v1": self._core_v1,
            "apps_v1": self._apps_v1,
            "autoscaling_v1": self._autoscaling_v1,
            "networking_v1": self._networking_v1,
            "rbac_v1": self._rbac_v1,
        }

        for checker_cls in checkers_to_run:
            checker = checker_cls(k8s_clients)
            try:
                results = checker.run(namespace=namespace)
                report.add_all(results)
            except Exception as exc:
                # Don't crash the whole scan if one checker fails
                from k8s_health_checker.models import CheckResult, Severity

                report.add(
                    CheckResult(
                        name=f"{checker_cls.category.label} check error",
                        severity=Severity.WARNING,
                        message=f"Check failed: {exc}",
                        category=checker_cls.category,
                        fix="Ensure the scanner has sufficient RBAC permissions.",
                    )
                )

        report.scan_duration_seconds = round(time.monotonic() - start, 2)
        return report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _list_namespaces(self) -> List[str]:
        try:
            ns_list = self._core_v1.list_namespace()
            return [ns.metadata.name for ns in ns_list.items]
        except Exception:
            return []

    def _build_summary(self, namespace: Optional[str] = None) -> ClusterSummary:
        summary = ClusterSummary(cluster_name=self._cluster_name)

        try:
            # Nodes
            nodes = self._core_v1.list_node()
            summary.node_count = len(nodes.items)
        except Exception:
            pass

        try:
            # Pods
            if namespace:
                pods = self._core_v1.list_namespaced_pod(namespace)
            else:
                pods = self._core_v1.list_pod_for_all_namespaces()

            summary.pod_total = len(pods.items)
            for pod in pods.items:
                phase = (pod.status.phase or "Unknown").lower()
                if phase == "running":
                    summary.pod_running += 1
                elif phase == "pending":
                    summary.pod_pending += 1
                elif phase == "failed":
                    summary.pod_failed += 1
        except Exception:
            pass

        try:
            # Namespaces
            ns_list = self._core_v1.list_namespace()
            summary.namespace_count = len(ns_list.items)
        except Exception:
            pass

        try:
            # Services
            if namespace:
                svcs = self._core_v1.list_namespaced_service(namespace)
            else:
                svcs = self._core_v1.list_service_for_all_namespaces()
            summary.service_count = len(svcs.items)
        except Exception:
            pass

        try:
            # Deployments
            if namespace:
                deps = self._apps_v1.list_namespaced_deployment(namespace)
            else:
                deps = self._apps_v1.list_deployment_for_all_namespaces()
            summary.deployment_count = len(deps.items)
        except Exception:
            pass

        return summary
