"""Workload checks — Deployments, StatefulSets, DaemonSets health."""

from __future__ import annotations

from typing import List, Optional

from k8s_health_checker.checks.base import BaseChecker
from k8s_health_checker.models import Category, CheckResult, Severity


class WorkloadChecker(BaseChecker):
    """Checks workload controllers for misconfigurations and failures."""

    category = Category.WORKLOADS

    def run(self, namespace: Optional[str] = None) -> List[CheckResult]:
        results: List[CheckResult] = []

        results.extend(self._check_deployments(namespace))
        results.extend(self._check_statefulsets(namespace))
        results.extend(self._check_daemonsets(namespace))

        if not any(r.is_issue for r in results):
            results.append(
                CheckResult(
                    name="All workloads healthy",
                    severity=Severity.PASS,
                    message=(
                        "All Deployments, StatefulSets, and DaemonSets "
                        "are running as expected."
                    ),
                    category=Category.WORKLOADS,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Deployments
    # ------------------------------------------------------------------

    def _check_deployments(
        self, namespace: Optional[str] = None
    ) -> List[CheckResult]:
        results: List[CheckResult] = []

        if namespace:
            deployments = self.apps_v1.list_namespaced_deployment(namespace)
        else:
            deployments = self.apps_v1.list_deployment_for_all_namespaces()

        for dep in deployments.items:
            ns = dep.metadata.namespace
            name = dep.metadata.name
            desired = dep.spec.replicas or 0
            ready = dep.status.ready_replicas or 0
            available = dep.status.available_replicas or 0
            updated = dep.status.updated_replicas or 0

            # --- Zero replicas (intentionally scaled down?) ---
            if desired == 0:
                results.append(
                    CheckResult(
                        name="Deployment scaled to zero",
                        severity=Severity.INFO,
                        message=(
                            f"Deployment '{name}' is scaled to 0 replicas."
                        ),
                        category=Category.WORKLOADS,
                        namespace=ns,
                        resource=name,
                        fix="If intentional, ignore. Otherwise: "
                        f"kubectl scale deployment {name} "
                        f"--replicas=1 -n {ns}",
                    )
                )
                continue

            # --- Not enough ready replicas ---
            if ready < desired:
                severity = Severity.CRITICAL if ready == 0 else Severity.WARNING
                results.append(
                    CheckResult(
                        name="Deployment replicas not ready",
                        severity=severity,
                        message=(
                            f"Deployment '{name}' has {ready}/{desired} "
                            f"replicas ready."
                        ),
                        category=Category.WORKLOADS,
                        namespace=ns,
                        resource=name,
                        fix=f"Check pod status: kubectl get pods -l "
                        f"app={name} -n {ns}",
                    )
                )

            # --- Single replica (no HA) ---
            if desired == 1 and ns not in ("kube-system", "kube-public"):
                results.append(
                    CheckResult(
                        name="Single replica deployment",
                        severity=Severity.INFO,
                        message=(
                            f"Deployment '{name}' runs only 1 replica. "
                            "A pod restart will cause downtime."
                        ),
                        category=Category.WORKLOADS,
                        namespace=ns,
                        resource=name,
                        fix="Consider running at least 2 replicas "
                        "with a PodDisruptionBudget for "
                        "high-availability.",
                    )
                )

            # --- Rollout stuck ---
            if updated < desired and available >= desired:
                results.append(
                    CheckResult(
                        name="Rollout possibly stuck",
                        severity=Severity.WARNING,
                        message=(
                            f"Deployment '{name}' has "
                            f"{updated}/{desired} updated replicas. "
                            "A rollout may be stuck."
                        ),
                        category=Category.WORKLOADS,
                        namespace=ns,
                        resource=name,
                        fix=f"Check rollout status: kubectl rollout "
                        f"status deployment/{name} -n {ns}",
                    )
                )

        return results

    # ------------------------------------------------------------------
    # StatefulSets
    # ------------------------------------------------------------------

    def _check_statefulsets(
        self, namespace: Optional[str] = None
    ) -> List[CheckResult]:
        results: List[CheckResult] = []

        if namespace:
            sts_list = self.apps_v1.list_namespaced_stateful_set(namespace)
        else:
            sts_list = self.apps_v1.list_stateful_set_for_all_namespaces()

        for sts in sts_list.items:
            ns = sts.metadata.namespace
            name = sts.metadata.name
            desired = sts.spec.replicas or 0
            ready = sts.status.ready_replicas or 0

            if ready < desired and desired > 0:
                severity = Severity.CRITICAL if ready == 0 else Severity.WARNING
                results.append(
                    CheckResult(
                        name="StatefulSet replicas not ready",
                        severity=severity,
                        message=(
                            f"StatefulSet '{name}' has {ready}/{desired} "
                            f"replicas ready."
                        ),
                        category=Category.WORKLOADS,
                        namespace=ns,
                        resource=name,
                        fix=f"Check pods: kubectl get pods -l "
                        f"app={name} -n {ns}",
                    )
                )

        return results

    # ------------------------------------------------------------------
    # DaemonSets
    # ------------------------------------------------------------------

    def _check_daemonsets(
        self, namespace: Optional[str] = None
    ) -> List[CheckResult]:
        results: List[CheckResult] = []

        if namespace:
            ds_list = self.apps_v1.list_namespaced_daemon_set(namespace)
        else:
            ds_list = self.apps_v1.list_daemon_set_for_all_namespaces()

        for ds in ds_list.items:
            ns = ds.metadata.namespace
            name = ds.metadata.name
            desired = ds.status.desired_number_scheduled or 0
            ready = ds.status.number_ready or 0

            if ready < desired and desired > 0:
                results.append(
                    CheckResult(
                        name="DaemonSet pods not ready",
                        severity=Severity.WARNING,
                        message=(
                            f"DaemonSet '{name}' has {ready}/{desired} "
                            f"pods ready (expected one per node)."
                        ),
                        category=Category.WORKLOADS,
                        namespace=ns,
                        resource=name,
                        fix=f"Check DaemonSet: kubectl describe "
                        f"daemonset {name} -n {ns}",
                    )
                )

        return results
