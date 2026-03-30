"""Demo mode — generates a realistic HealthReport without connecting to a cluster.

This lets users try the tool instantly, and is also used for screenshots/demos.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from k8s_health_checker.models import (
    Category,
    CheckResult,
    ClusterSummary,
    HealthReport,
    Severity,
)


def generate_demo_report() -> HealthReport:
    """Create a realistic demo health report.

    Simulates a mid-sized production AKS cluster with a mix of
    healthy and problematic resources — representative of what
    you'd actually see in a real-world scan.
    """
    start = time.monotonic()

    report = HealthReport(
        cluster_name="aks-prod-eastus",
        timestamp=datetime.now(timezone.utc),
        namespaces_scanned=[
            "default",
            "production",
            "staging",
            "monitoring",
            "ingress-nginx",
            "cert-manager",
            "kube-system",
        ],
    )

    report.summary = ClusterSummary(
        cluster_name="aks-prod-eastus",
        node_count=6,
        pod_total=87,
        pod_running=82,
        pod_pending=3,
        pod_failed=2,
        namespace_count=7,
        service_count=34,
        deployment_count=18,
    )

    # === CRITICAL issues ===

    report.add(
        CheckResult(
            name="CrashLoopBackOff",
            severity=Severity.CRITICAL,
            message=(
                "Container 'api' in pod 'payment-api-7d8f9c6b4-x2k9p' "
                "is crash-looping (47 restarts). "
                "Last exit code: 1."
            ),
            category=Category.PODS,
            namespace="production",
            resource="payment-api-7d8f9c6b4-x2k9p",
            fix=(
                "Check logs: kubectl logs payment-api-7d8f9c6b4-x2k9p "
                "-c api -n production --previous"
            ),
        )
    )

    report.add(
        CheckResult(
            name="Node DiskPressure",
            severity=Severity.CRITICAL,
            message=(
                "Node 'aks-apps-23456789-vmss000003' is under "
                "disk pressure. Pods may be evicted."
            ),
            category=Category.NODES,
            resource="aks-apps-23456789-vmss000003",
            fix=(
                "Free disk space on the node — clean up "
                "container images, logs, and temp files."
            ),
        )
    )

    report.add(
        CheckResult(
            name="Deployment replicas not ready",
            severity=Severity.CRITICAL,
            message="Deployment 'payment-api' has 0/3 replicas ready.",
            category=Category.WORKLOADS,
            namespace="production",
            resource="payment-api",
            fix="Check pod status: kubectl get pods -l app=payment-api -n production",
        )
    )

    report.add(
        CheckResult(
            name="Privileged container",
            severity=Severity.CRITICAL,
            message=(
                "Container 'debug-tools' in pod 'debug-pod-manual' "
                "runs in privileged mode. It has full access to the host."
            ),
            category=Category.SECURITY,
            namespace="staging",
            resource="debug-pod-manual",
            fix="Remove privileged: true from the container's securityContext.",
        )
    )

    # === WARNING issues ===

    report.add(
        CheckResult(
            name="Pod stuck in Pending",
            severity=Severity.WARNING,
            message=(
                "Pod 'ml-training-job-4a8b2' is Pending. "
                "Reason: Insufficient cpu — "
                "0/6 nodes are available: 6 Insufficient cpu."
            ),
            category=Category.PODS,
            namespace="staging",
            resource="ml-training-job-4a8b2",
            fix=(
                "Check events: kubectl describe pod "
                "ml-training-job-4a8b2 -n staging — "
                "common causes: insufficient CPU/memory, node affinity, unbound PVC."
            ),
        )
    )

    report.add(
        CheckResult(
            name="Missing resource requests",
            severity=Severity.WARNING,
            message=(
                "Container 'web' in pod 'frontend-b4d7f8-lm2n9' "
                "has no CPU/memory requests. The scheduler cannot "
                "make optimal placement decisions."
            ),
            category=Category.RESOURCES,
            namespace="production",
            resource="frontend-b4d7f8-lm2n9",
            fix=(
                "Add resources.requests to the container spec:\n"
                "  resources:\n"
                "    requests:\n"
                "      cpu: 100m\n"
                "      memory: 128Mi"
            ),
        )
    )

    report.add(
        CheckResult(
            name="Missing resource limits",
            severity=Severity.WARNING,
            message=(
                "Container 'worker' in pod 'queue-processor-6c9d8-abc12' "
                "has no CPU/memory limits. It can consume unbounded "
                "node resources."
            ),
            category=Category.RESOURCES,
            namespace="production",
            resource="queue-processor-6c9d8-abc12",
            fix=(
                "Add resources.limits to the container spec:\n"
                "  resources:\n"
                "    limits:\n"
                "      cpu: 500m\n"
                "      memory: 256Mi"
            ),
        )
    )

    report.add(
        CheckResult(
            name="Missing readiness probe",
            severity=Severity.WARNING,
            message=(
                "Container 'web' in pod 'frontend-b4d7f8-lm2n9' "
                "has no readiness probe. Traffic may be sent to "
                "the container before it's ready to serve."
            ),
            category=Category.PROBES,
            namespace="production",
            resource="frontend-b4d7f8-lm2n9",
            fix=(
                "Add a readinessProbe:\n"
                "  readinessProbe:\n"
                "    httpGet:\n"
                "      path: /ready\n"
                "      port: 8080\n"
                "    initialDelaySeconds: 5\n"
                "    periodSeconds: 5"
            ),
        )
    )

    report.add(
        CheckResult(
            name="No NetworkPolicies",
            severity=Severity.WARNING,
            message=(
                "Namespace 'production' has no NetworkPolicies. "
                "All pods can communicate freely with all other "
                "pods in the cluster."
            ),
            category=Category.SECURITY,
            namespace="production",
            fix=(
                "Apply a default-deny NetworkPolicy:\n"
                "  apiVersion: networking.k8s.io/v1\n"
                "  kind: NetworkPolicy\n"
                "  metadata:\n"
                "    name: default-deny\n"
                "    namespace: production\n"
                "  spec:\n"
                "    podSelector: {}\n"
                "    policyTypes:\n"
                "      - Ingress\n"
                "      - Egress"
            ),
        )
    )

    report.add(
        CheckResult(
            name="No NetworkPolicies",
            severity=Severity.WARNING,
            message=(
                "Namespace 'staging' has no NetworkPolicies. "
                "All pods can communicate freely with all other "
                "pods in the cluster."
            ),
            category=Category.SECURITY,
            namespace="staging",
            fix=(
                "Apply a default-deny NetworkPolicy for "
                "the staging namespace."
            ),
        )
    )

    report.add(
        CheckResult(
            name="HPA at maximum replicas",
            severity=Severity.WARNING,
            message=(
                "HPA 'user-service' is running at maximum "
                "capacity (10/10 replicas). The workload may need "
                "more capacity than the HPA allows."
            ),
            category=Category.AUTOSCALING,
            namespace="production",
            resource="user-service",
            fix="Consider increasing maxReplicas for this HPA.",
        )
    )

    report.add(
        CheckResult(
            name="Elevated pod restarts",
            severity=Severity.WARNING,
            message=(
                "Container 'app' in pod 'notification-svc-5f8d7-mn3k4' "
                "has restarted 12 times."
            ),
            category=Category.PODS,
            namespace="production",
            resource="notification-svc-5f8d7-mn3k4",
            fix="Monitor this pod — restarts may indicate instability.",
        )
    )

    # === INFO issues ===

    report.add(
        CheckResult(
            name="Single replica deployment",
            severity=Severity.INFO,
            message=(
                "Deployment 'admin-dashboard' runs only 1 replica. "
                "A pod restart will cause downtime."
            ),
            category=Category.WORKLOADS,
            namespace="production",
            resource="admin-dashboard",
            fix="Consider running at least 2 replicas with a "
            "PodDisruptionBudget for high-availability.",
        )
    )

    report.add(
        CheckResult(
            name="Missing liveness probe",
            severity=Severity.INFO,
            message=(
                "Container 'worker' in pod 'queue-processor-6c9d8-abc12' "
                "has no liveness probe. Kubernetes cannot detect "
                "and restart the container if it hangs."
            ),
            category=Category.PROBES,
            namespace="production",
            resource="queue-processor-6c9d8-abc12",
            fix=(
                "Add a livenessProbe:\n"
                "  livenessProbe:\n"
                "    httpGet:\n"
                "      path: /health\n"
                "      port: 8080\n"
                "    initialDelaySeconds: 15\n"
                "    periodSeconds: 10"
            ),
        )
    )

    report.add(
        CheckResult(
            name="Pods using default ServiceAccount",
            severity=Severity.INFO,
            message=(
                "14 pods are using the 'default' ServiceAccount. "
                "Consider creating dedicated ServiceAccounts with "
                "least-privilege RBAC."
            ),
            category=Category.SECURITY,
            fix="Create a dedicated ServiceAccount for each "
            "application and bind only the required roles.",
        )
    )

    # === PASS results ===

    report.add(
        CheckResult(
            name="All nodes Ready",
            severity=Severity.PASS,
            message="5 of 6 nodes are in Ready state (1 has DiskPressure but is Ready).",
            category=Category.NODES,
        )
    )

    report.add(
        CheckResult(
            name="All DaemonSets healthy",
            severity=Severity.PASS,
            message="All DaemonSets have the expected number of pods.",
            category=Category.WORKLOADS,
        )
    )

    report.add(
        CheckResult(
            name="All StatefulSets healthy",
            severity=Severity.PASS,
            message="All StatefulSets have the expected number of ready replicas.",
            category=Category.WORKLOADS,
        )
    )

    report.scan_duration_seconds = round(time.monotonic() - start, 2)
    return report
