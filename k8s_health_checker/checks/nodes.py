"""Node health checks — NotReady, conditions, capacity pressure."""

from __future__ import annotations

from typing import List, Optional

from k8s_health_checker.checks.base import BaseChecker
from k8s_health_checker.models import Category, CheckResult, Severity


class NodeChecker(BaseChecker):
    """Checks node health and conditions."""

    category = Category.NODES

    def run(self, namespace: Optional[str] = None) -> List[CheckResult]:
        results: List[CheckResult] = []

        nodes = self.core_v1.list_node()
        not_ready = 0

        for node in nodes.items:
            name = node.metadata.name
            conditions = {c.type: c for c in (node.status.conditions or [])}

            # --- Node NotReady ---
            ready_cond = conditions.get("Ready")
            if ready_cond and ready_cond.status != "True":
                not_ready += 1
                results.append(
                    CheckResult(
                        name="Node NotReady",
                        severity=Severity.CRITICAL,
                        message=(
                            f"Node '{name}' is not in Ready state. "
                            f"Reason: {ready_cond.reason or 'Unknown'}. "
                            f"Message: {ready_cond.message or 'N/A'}"
                        ),
                        category=Category.NODES,
                        resource=name,
                        fix="Check kubelet status on the node: "
                        f"kubectl describe node {name}",
                    )
                )

            # --- DiskPressure ---
            disk = conditions.get("DiskPressure")
            if disk and disk.status == "True":
                results.append(
                    CheckResult(
                        name="Node DiskPressure",
                        severity=Severity.CRITICAL,
                        message=(
                            f"Node '{name}' is under disk pressure. "
                            "Pods may be evicted."
                        ),
                        category=Category.NODES,
                        resource=name,
                        fix="Free disk space on the node — clean up "
                        "container images, logs, and temp files.",
                    )
                )

            # --- MemoryPressure ---
            mem = conditions.get("MemoryPressure")
            if mem and mem.status == "True":
                results.append(
                    CheckResult(
                        name="Node MemoryPressure",
                        severity=Severity.CRITICAL,
                        message=(
                            f"Node '{name}' is under memory pressure. "
                            "Pods may be OOMKilled."
                        ),
                        category=Category.NODES,
                        resource=name,
                        fix="Investigate top memory consumers: "
                        "kubectl top pods --sort-by=memory",
                    )
                )

            # --- PIDPressure ---
            pid = conditions.get("PIDPressure")
            if pid and pid.status == "True":
                results.append(
                    CheckResult(
                        name="Node PIDPressure",
                        severity=Severity.WARNING,
                        message=(
                            f"Node '{name}' is under PID pressure. "
                            "Too many processes running."
                        ),
                        category=Category.NODES,
                        resource=name,
                        fix="Identify pods spawning excessive "
                        "processes on this node.",
                    )
                )

            # --- Unschedulable (cordoned) ---
            if node.spec.unschedulable:
                results.append(
                    CheckResult(
                        name="Node cordoned",
                        severity=Severity.INFO,
                        message=(
                            f"Node '{name}' is cordoned "
                            "(unschedulable). No new pods will "
                            "be scheduled here."
                        ),
                        category=Category.NODES,
                        resource=name,
                        fix=f"Uncordon when ready: kubectl uncordon {name}",
                    )
                )

        # Pass result
        if not_ready == 0 and len(nodes.items) > 0:
            results.append(
                CheckResult(
                    name="All nodes Ready",
                    severity=Severity.PASS,
                    message=f"All {len(nodes.items)} nodes are in Ready state.",
                    category=Category.NODES,
                )
            )

        return results
