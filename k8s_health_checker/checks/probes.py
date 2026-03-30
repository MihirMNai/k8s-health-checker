"""Probe checks — missing readiness/liveness probes."""

from __future__ import annotations

from typing import List, Optional

from k8s_health_checker.checks.base import BaseChecker
from k8s_health_checker.models import Category, CheckResult, Severity


class ProbeChecker(BaseChecker):
    """Checks that containers have readiness and liveness probes."""

    category = Category.PROBES

    def run(self, namespace: Optional[str] = None) -> List[CheckResult]:
        results: List[CheckResult] = []

        if namespace:
            pods = self.core_v1.list_namespaced_pod(namespace)
        else:
            pods = self.core_v1.list_pod_for_all_namespaces()

        no_readiness = 0
        no_liveness = 0
        checked = 0

        for pod in pods.items:
            ns = pod.metadata.namespace
            pod_name = pod.metadata.name

            phase = (pod.status.phase or "").lower()
            if phase in ("succeeded", "failed"):
                continue

            for container in pod.spec.containers:
                checked += 1

                if not container.readiness_probe:
                    no_readiness += 1
                    results.append(
                        CheckResult(
                            name="Missing readiness probe",
                            severity=Severity.WARNING,
                            message=(
                                f"Container '{container.name}' in pod "
                                f"'{pod_name}' has no readiness probe. "
                                "Traffic may be sent to the container "
                                "before it's ready to serve."
                            ),
                            category=Category.PROBES,
                            namespace=ns,
                            resource=pod_name,
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

                if not container.liveness_probe:
                    no_liveness += 1
                    results.append(
                        CheckResult(
                            name="Missing liveness probe",
                            severity=Severity.INFO,
                            message=(
                                f"Container '{container.name}' in pod "
                                f"'{pod_name}' has no liveness probe. "
                                "Kubernetes cannot detect and restart "
                                "the container if it hangs."
                            ),
                            category=Category.PROBES,
                            namespace=ns,
                            resource=pod_name,
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

        if no_readiness == 0 and no_liveness == 0 and checked > 0:
            results.append(
                CheckResult(
                    name="All containers have probes",
                    severity=Severity.PASS,
                    message=(
                        f"All {checked} containers have readiness "
                        "and liveness probes configured."
                    ),
                    category=Category.PROBES,
                )
            )

        return results
