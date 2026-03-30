"""Pod health checks — CrashLoopBackOff, Pending, Failed, OOMKilled, high restarts."""

from __future__ import annotations

from typing import List, Optional

from k8s_health_checker.checks.base import BaseChecker
from k8s_health_checker.models import Category, CheckResult, Severity

# Restart threshold before flagging a warning / critical
RESTART_WARN = 5
RESTART_CRIT = 20


class PodChecker(BaseChecker):
    """Checks pod health across the cluster."""

    category = Category.PODS

    def run(self, namespace: Optional[str] = None) -> List[CheckResult]:
        results: List[CheckResult] = []

        if namespace:
            pods = self.core_v1.list_namespaced_pod(namespace)
        else:
            pods = self.core_v1.list_pod_for_all_namespaces()

        crash_loop = 0
        pending = 0
        failed = 0
        oom_killed = 0
        high_restarts = 0

        for pod in pods.items:
            ns = pod.metadata.namespace
            name = pod.metadata.name
            phase = (pod.status.phase or "Unknown").lower()

            # --- Failed pods ---
            if phase == "failed":
                failed += 1
                reason = ""
                if pod.status.reason:
                    reason = f" Reason: {pod.status.reason}."
                results.append(
                    CheckResult(
                        name="Pod in Failed state",
                        severity=Severity.CRITICAL,
                        message=f"Pod '{name}' has failed.{reason}",
                        category=Category.PODS,
                        namespace=ns,
                        resource=name,
                        fix="Inspect pod events: kubectl describe pod "
                        f"{name} -n {ns}",
                    )
                )

            # --- Pending pods ---
            if phase == "pending":
                pending += 1
                # Try to find reason
                reason = self._pending_reason(pod)
                results.append(
                    CheckResult(
                        name="Pod stuck in Pending",
                        severity=Severity.WARNING,
                        message=f"Pod '{name}' is Pending.{reason}",
                        category=Category.PODS,
                        namespace=ns,
                        resource=name,
                        fix="Check events: kubectl describe pod "
                        f"{name} -n {ns} — common causes: "
                        "insufficient CPU/memory, node affinity, "
                        "unbound PVC.",
                    )
                )

            # --- Container-level checks ---
            container_statuses = pod.status.container_statuses or []
            for cs in container_statuses:
                restarts = cs.restart_count or 0

                # CrashLoopBackOff
                if cs.state and cs.state.waiting:
                    reason = cs.state.waiting.reason or ""
                    if reason == "CrashLoopBackOff":
                        crash_loop += 1
                        last_msg = ""
                        if cs.last_state and cs.last_state.terminated:
                            last_msg = (
                                f" Last exit code: "
                                f"{cs.last_state.terminated.exit_code}."
                            )
                        results.append(
                            CheckResult(
                                name="CrashLoopBackOff",
                                severity=Severity.CRITICAL,
                                message=(
                                    f"Container '{cs.name}' in pod "
                                    f"'{name}' is crash-looping "
                                    f"({restarts} restarts).{last_msg}"
                                ),
                                category=Category.PODS,
                                namespace=ns,
                                resource=name,
                                fix=f"Check logs: kubectl logs {name} "
                                f"-c {cs.name} -n {ns} --previous",
                            )
                        )

                # OOMKilled
                if cs.last_state and cs.last_state.terminated:
                    if cs.last_state.terminated.reason == "OOMKilled":
                        oom_killed += 1
                        results.append(
                            CheckResult(
                                name="OOMKilled",
                                severity=Severity.CRITICAL,
                                message=(
                                    f"Container '{cs.name}' in pod "
                                    f"'{name}' was OOMKilled. The "
                                    "container exceeded its memory limit."
                                ),
                                category=Category.PODS,
                                namespace=ns,
                                resource=name,
                                fix="Increase memory limits in the pod "
                                "spec, or investigate memory leaks in "
                                "the application.",
                            )
                        )

                # High restart count (but not crash-looping right now)
                if restarts >= RESTART_CRIT:
                    high_restarts += 1
                    results.append(
                        CheckResult(
                            name="Excessive pod restarts",
                            severity=Severity.CRITICAL,
                            message=(
                                f"Container '{cs.name}' in pod "
                                f"'{name}' has restarted "
                                f"{restarts} times."
                            ),
                            category=Category.PODS,
                            namespace=ns,
                            resource=name,
                            fix="Investigate container crash reason: "
                            f"kubectl describe pod {name} -n {ns}",
                        )
                    )
                elif restarts >= RESTART_WARN:
                    high_restarts += 1
                    results.append(
                        CheckResult(
                            name="Elevated pod restarts",
                            severity=Severity.WARNING,
                            message=(
                                f"Container '{cs.name}' in pod "
                                f"'{name}' has restarted "
                                f"{restarts} times."
                            ),
                            category=Category.PODS,
                            namespace=ns,
                            resource=name,
                            fix="Monitor this pod — restarts may "
                            "indicate instability.",
                        )
                    )

        # Pass result if everything is clean
        total_issues = crash_loop + pending + failed + oom_killed + high_restarts
        if total_issues == 0:
            results.append(
                CheckResult(
                    name="All pods healthy",
                    severity=Severity.PASS,
                    message=f"All {len(pods.items)} pods are running without issues.",
                    category=Category.PODS,
                )
            )

        return results

    @staticmethod
    def _pending_reason(pod) -> str:
        """Try to extract why a pod is pending from its conditions."""
        if not pod.status.conditions:
            return ""
        for cond in pod.status.conditions:
            if cond.reason and cond.reason != "Initialized":
                return f" Reason: {cond.reason} — {cond.message or ''}"
        return ""
