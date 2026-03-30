"""Test fixtures and shared mock objects."""

from __future__ import annotations

from unittest.mock import MagicMock


def make_pod(
    name: str = "test-pod",
    namespace: str = "default",
    phase: str = "Running",
    restart_count: int = 0,
    waiting_reason: str | None = None,
    terminated_reason: str | None = None,
    has_requests: bool = True,
    has_limits: bool = True,
    has_readiness_probe: bool = True,
    has_liveness_probe: bool = True,
    privileged: bool = False,
    run_as_user: int | None = None,
    service_account: str = "my-app-sa",
    container_name: str = "app",
) -> MagicMock:
    """Build a mock Pod object matching the kubernetes client shape."""
    pod = MagicMock()
    pod.metadata.name = name
    pod.metadata.namespace = namespace
    pod.status.phase = phase
    pod.status.reason = None
    pod.status.conditions = []
    pod.spec.service_account_name = service_account
    pod.spec.automount_service_account_token = True

    # Container spec
    container = MagicMock()
    container.name = container_name
    container.readiness_probe = MagicMock() if has_readiness_probe else None
    container.liveness_probe = MagicMock() if has_liveness_probe else None

    if has_requests:
        container.resources.requests = {"cpu": "100m", "memory": "128Mi"}
    else:
        container.resources.requests = None
        container.resources = MagicMock(
            requests=None,
            limits=None if not has_limits else {"cpu": "500m"},
        )

    if has_limits:
        container.resources.limits = {"cpu": "500m", "memory": "256Mi"}
    else:
        if has_requests:
            container.resources.limits = None

    # Security context
    sc = MagicMock()
    sc.privileged = privileged
    sc.run_as_user = run_as_user
    container.security_context = sc

    pod.spec.containers = [container]

    # Container status
    cs = MagicMock()
    cs.name = container_name
    cs.restart_count = restart_count
    cs.ready = phase == "Running"

    # Waiting state
    if waiting_reason:
        cs.state.waiting.reason = waiting_reason
    else:
        cs.state.waiting = None

    # Terminated state
    if terminated_reason:
        cs.last_state.terminated.reason = terminated_reason
        cs.last_state.terminated.exit_code = 1
    else:
        cs.last_state.terminated = None

    pod.status.container_statuses = [cs]
    return pod


def make_node(
    name: str = "node-1",
    ready: bool = True,
    disk_pressure: bool = False,
    memory_pressure: bool = False,
    pid_pressure: bool = False,
    unschedulable: bool = False,
) -> MagicMock:
    """Build a mock Node object."""
    node = MagicMock()
    node.metadata.name = name
    node.spec.unschedulable = unschedulable

    conditions = []
    conditions.append(_make_condition("Ready", "True" if ready else "False", "KubeletReady"))
    conditions.append(
        _make_condition("DiskPressure", "True" if disk_pressure else "False", "NoDiskPressure")
    )
    conditions.append(
        _make_condition(
            "MemoryPressure",
            "True" if memory_pressure else "False",
            "NoMemoryPressure",
        )
    )
    conditions.append(
        _make_condition("PIDPressure", "True" if pid_pressure else "False", "NoPIDPressure")
    )
    node.status.conditions = conditions
    return node


def make_deployment(
    name: str = "my-deploy",
    namespace: str = "default",
    replicas: int = 3,
    ready_replicas: int = 3,
    available_replicas: int = 3,
    updated_replicas: int = 3,
) -> MagicMock:
    dep = MagicMock()
    dep.metadata.name = name
    dep.metadata.namespace = namespace
    dep.spec.replicas = replicas
    dep.status.ready_replicas = ready_replicas
    dep.status.available_replicas = available_replicas
    dep.status.updated_replicas = updated_replicas
    return dep


def make_hpa(
    name: str = "my-hpa",
    namespace: str = "default",
    min_replicas: int = 2,
    max_replicas: int = 10,
    current_replicas: int = 5,
) -> MagicMock:
    hpa = MagicMock()
    hpa.metadata.name = name
    hpa.metadata.namespace = namespace
    hpa.spec.min_replicas = min_replicas
    hpa.spec.max_replicas = max_replicas
    hpa.status.current_replicas = current_replicas
    return hpa


def make_k8s_clients(**overrides) -> dict:
    """Return a dict of mocked K8s API clients."""
    return {
        "core_v1": overrides.get("core_v1", MagicMock()),
        "apps_v1": overrides.get("apps_v1", MagicMock()),
        "autoscaling_v1": overrides.get("autoscaling_v1", MagicMock()),
        "networking_v1": overrides.get("networking_v1", MagicMock()),
        "rbac_v1": overrides.get("rbac_v1", MagicMock()),
    }


def _make_condition(ctype: str, status: str, reason: str) -> MagicMock:
    cond = MagicMock()
    cond.type = ctype
    cond.status = status
    cond.reason = reason
    cond.message = ""
    return cond
