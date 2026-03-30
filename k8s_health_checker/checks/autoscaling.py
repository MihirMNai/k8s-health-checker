"""Autoscaling checks — HPA status and configuration."""

from __future__ import annotations

from typing import List, Optional

from k8s_health_checker.checks.base import BaseChecker
from k8s_health_checker.models import Category, CheckResult, Severity


class AutoscalingChecker(BaseChecker):
    """Checks HorizontalPodAutoscaler health and configuration."""

    category = Category.AUTOSCALING

    def run(self, namespace: Optional[str] = None) -> List[CheckResult]:
        results: List[CheckResult] = []

        try:
            if namespace:
                hpa_list = self.autoscaling_v1.list_namespaced_horizontal_pod_autoscaler(
                    namespace
                )
            else:
                hpa_list = self.autoscaling_v1.list_horizontal_pod_autoscaler_for_all_namespaces()
        except Exception:
            return results

        if not hpa_list.items:
            results.append(
                CheckResult(
                    name="No HPAs configured",
                    severity=Severity.INFO,
                    message=(
                        "No HorizontalPodAutoscalers found. "
                        "Consider adding autoscaling for production workloads."
                    ),
                    category=Category.AUTOSCALING,
                    fix=(
                        "Create an HPA: kubectl autoscale deployment <name> "
                        "--min=2 --max=10 --cpu-percent=70"
                    ),
                )
            )
            return results

        for hpa in hpa_list.items:
            ns = hpa.metadata.namespace
            name = hpa.metadata.name
            current = hpa.status.current_replicas or 0
            max_replicas = hpa.spec.max_replicas or 0
            min_replicas = hpa.spec.min_replicas or 1

            # --- HPA at max replicas ---
            if current >= max_replicas and max_replicas > 0:
                results.append(
                    CheckResult(
                        name="HPA at maximum replicas",
                        severity=Severity.WARNING,
                        message=(
                            f"HPA '{name}' is running at maximum "
                            f"capacity ({current}/{max_replicas} "
                            "replicas). The workload may need more "
                            "capacity than the HPA allows."
                        ),
                        category=Category.AUTOSCALING,
                        namespace=ns,
                        resource=name,
                        fix=(
                            f"Consider increasing maxReplicas: "
                            f"kubectl patch hpa {name} -n {ns} "
                            f"-p '{{\"spec\":{{\"maxReplicas\":{max_replicas + 5}}}}}'"
                        ),
                    )
                )

            # --- HPA min = max (autoscaling effectively disabled) ---
            if min_replicas == max_replicas:
                results.append(
                    CheckResult(
                        name="HPA min equals max",
                        severity=Severity.INFO,
                        message=(
                            f"HPA '{name}' has minReplicas = "
                            f"maxReplicas = {min_replicas}. "
                            "Autoscaling is effectively disabled."
                        ),
                        category=Category.AUTOSCALING,
                        namespace=ns,
                        resource=name,
                        fix="Set different min and max values to "
                        "enable actual autoscaling.",
                    )
                )

        if not any(r.is_issue for r in results):
            results.append(
                CheckResult(
                    name="All HPAs healthy",
                    severity=Severity.PASS,
                    message=f"All {len(hpa_list.items)} HPAs are within configured bounds.",
                    category=Category.AUTOSCALING,
                )
            )

        return results
