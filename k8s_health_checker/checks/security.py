"""Security checks — NetworkPolicies, privileged containers, service accounts."""

from __future__ import annotations

from typing import List, Optional

from k8s_health_checker.checks.base import BaseChecker
from k8s_health_checker.models import Category, CheckResult, Severity


class SecurityChecker(BaseChecker):
    """Checks Kubernetes security best practices."""

    category = Category.SECURITY

    def run(self, namespace: Optional[str] = None) -> List[CheckResult]:
        results: List[CheckResult] = []

        results.extend(self._check_network_policies(namespace))
        results.extend(self._check_privileged_containers(namespace))
        results.extend(self._check_service_accounts(namespace))

        # If no issues, add pass
        if not any(r.is_issue for r in results):
            results.append(
                CheckResult(
                    name="Security checks passed",
                    severity=Severity.PASS,
                    message="No security misconfigurations detected.",
                    category=Category.SECURITY,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Network Policies
    # ------------------------------------------------------------------

    def _check_network_policies(
        self, namespace: Optional[str] = None
    ) -> List[CheckResult]:
        results: List[CheckResult] = []

        # Get all namespaces to check
        if namespace:
            namespaces = [namespace]
        else:
            ns_list = self.core_v1.list_namespace()
            # Skip kube-system and kube-public
            namespaces = [
                ns.metadata.name
                for ns in ns_list.items
                if ns.metadata.name not in ("kube-system", "kube-public", "kube-node-lease")
            ]

        for ns in namespaces:
            try:
                policies = self.networking_v1.list_namespaced_network_policy(ns)
                if len(policies.items) == 0:
                    results.append(
                        CheckResult(
                            name="No NetworkPolicies",
                            severity=Severity.WARNING,
                            message=(
                                f"Namespace '{ns}' has no NetworkPolicies. "
                                "All pods can communicate freely with "
                                "all other pods in the cluster."
                            ),
                            category=Category.SECURITY,
                            namespace=ns,
                            fix=(
                                "Apply a default-deny NetworkPolicy:\n"
                                "  apiVersion: networking.k8s.io/v1\n"
                                "  kind: NetworkPolicy\n"
                                "  metadata:\n"
                                f"    name: default-deny\n"
                                f"    namespace: {ns}\n"
                                "  spec:\n"
                                "    podSelector: {}\n"
                                "    policyTypes:\n"
                                "      - Ingress\n"
                                "      - Egress"
                            ),
                        )
                    )
            except Exception:
                pass

        return results

    # ------------------------------------------------------------------
    # Privileged containers
    # ------------------------------------------------------------------

    def _check_privileged_containers(
        self, namespace: Optional[str] = None
    ) -> List[CheckResult]:
        results: List[CheckResult] = []

        if namespace:
            pods = self.core_v1.list_namespaced_pod(namespace)
        else:
            pods = self.core_v1.list_pod_for_all_namespaces()

        for pod in pods.items:
            ns = pod.metadata.namespace
            pod_name = pod.metadata.name

            # Skip kube-system (many system pods need privileged)
            if ns == "kube-system":
                continue

            for container in pod.spec.containers:
                sc = container.security_context
                if sc and sc.privileged:
                    results.append(
                        CheckResult(
                            name="Privileged container",
                            severity=Severity.CRITICAL,
                            message=(
                                f"Container '{container.name}' in pod "
                                f"'{pod_name}' runs in privileged mode. "
                                "It has full access to the host."
                            ),
                            category=Category.SECURITY,
                            namespace=ns,
                            resource=pod_name,
                            fix=(
                                "Remove privileged: true from the "
                                "container's securityContext unless "
                                "absolutely required."
                            ),
                        )
                    )

                if sc and sc.run_as_user == 0:
                    results.append(
                        CheckResult(
                            name="Container running as root",
                            severity=Severity.WARNING,
                            message=(
                                f"Container '{container.name}' in pod "
                                f"'{pod_name}' is explicitly set to "
                                "run as root (UID 0)."
                            ),
                            category=Category.SECURITY,
                            namespace=ns,
                            resource=pod_name,
                            fix=(
                                "Set runAsNonRoot: true and "
                                "runAsUser: 1000 in securityContext."
                            ),
                        )
                    )

        return results

    # ------------------------------------------------------------------
    # Service accounts
    # ------------------------------------------------------------------

    def _check_service_accounts(
        self, namespace: Optional[str] = None
    ) -> List[CheckResult]:
        results: List[CheckResult] = []

        if namespace:
            pods = self.core_v1.list_namespaced_pod(namespace)
        else:
            pods = self.core_v1.list_pod_for_all_namespaces()

        default_sa_count = 0

        for pod in pods.items:
            ns = pod.metadata.namespace
            if ns in ("kube-system", "kube-public", "kube-node-lease"):
                continue

            sa = pod.spec.service_account_name or "default"

            if sa == "default":
                default_sa_count += 1

            # Check automounting of SA token
            if pod.spec.automount_service_account_token is not False:
                # Only flag if the pod doesn't actually need the API
                pass  # This is informational

        if default_sa_count > 5:
            results.append(
                CheckResult(
                    name="Pods using default ServiceAccount",
                    severity=Severity.INFO,
                    message=(
                        f"{default_sa_count} pods are using the "
                        "'default' ServiceAccount. Consider creating "
                        "dedicated ServiceAccounts with least-privilege "
                        "RBAC."
                    ),
                    category=Category.SECURITY,
                    fix=(
                        "Create a dedicated ServiceAccount for each "
                        "application and bind only the required roles."
                    ),
                )
            )

        return results
