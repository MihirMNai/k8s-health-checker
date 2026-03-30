"""Resource checks — missing requests/limits on containers."""

from __future__ import annotations

from typing import List, Optional

from k8s_health_checker.checks.base import BaseChecker
from k8s_health_checker.models import Category, CheckResult, Severity


class ResourceChecker(BaseChecker):
    """Checks that containers have CPU/memory requests and limits defined."""

    category = Category.RESOURCES

    def run(self, namespace: Optional[str] = None) -> List[CheckResult]:
        results: List[CheckResult] = []

        if namespace:
            pods = self.core_v1.list_namespaced_pod(namespace)
        else:
            pods = self.core_v1.list_pod_for_all_namespaces()

        no_requests = 0
        no_limits = 0
        checked = 0

        for pod in pods.items:
            ns = pod.metadata.namespace
            pod_name = pod.metadata.name

            # Skip completed / system pods
            phase = (pod.status.phase or "").lower()
            if phase in ("succeeded", "failed"):
                continue

            for container in pod.spec.containers:
                checked += 1
                resources = container.resources

                has_requests = (
                    resources
                    and resources.requests
                    and ("cpu" in resources.requests or "memory" in resources.requests)
                )
                has_limits = (
                    resources
                    and resources.limits
                    and ("cpu" in resources.limits or "memory" in resources.limits)
                )

                if not has_requests:
                    no_requests += 1
                    results.append(
                        CheckResult(
                            name="Missing resource requests",
                            severity=Severity.WARNING,
                            message=(
                                f"Container '{container.name}' in pod "
                                f"'{pod_name}' has no CPU/memory requests. "
                                "The scheduler cannot make optimal "
                                "placement decisions."
                            ),
                            category=Category.RESOURCES,
                            namespace=ns,
                            resource=pod_name,
                            fix=(
                                "Add resources.requests to the container "
                                "spec:\n"
                                "  resources:\n"
                                "    requests:\n"
                                "      cpu: 100m\n"
                                "      memory: 128Mi"
                            ),
                        )
                    )

                if not has_limits:
                    no_limits += 1
                    results.append(
                        CheckResult(
                            name="Missing resource limits",
                            severity=Severity.WARNING,
                            message=(
                                f"Container '{container.name}' in pod "
                                f"'{pod_name}' has no CPU/memory limits. "
                                "It can consume unbounded node "
                                "resources."
                            ),
                            category=Category.RESOURCES,
                            namespace=ns,
                            resource=pod_name,
                            fix=(
                                "Add resources.limits to the container "
                                "spec:\n"
                                "  resources:\n"
                                "    limits:\n"
                                "      cpu: 500m\n"
                                "      memory: 256Mi"
                            ),
                        )
                    )

        if no_requests == 0 and no_limits == 0 and checked > 0:
            results.append(
                CheckResult(
                    name="All containers have resource definitions",
                    severity=Severity.PASS,
                    message=(
                        f"All {checked} containers have CPU/memory "
                        "requests and limits defined."
                    ),
                    category=Category.RESOURCES,
                )
            )

        return results
