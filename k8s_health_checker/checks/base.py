"""Base class for all health checkers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from k8s_health_checker.models import Category, CheckResult


class BaseChecker(ABC):
    """Every health checker inherits from this class.

    Subclasses must define:
      - category  (class-level Category enum)
      - run()     (returns a list of CheckResult)
    """

    category: Category  # set by each subclass

    def __init__(self, k8s_clients: Dict[str, Any]) -> None:
        self.core_v1 = k8s_clients.get("core_v1")
        self.apps_v1 = k8s_clients.get("apps_v1")
        self.autoscaling_v1 = k8s_clients.get("autoscaling_v1")
        self.networking_v1 = k8s_clients.get("networking_v1")
        self.rbac_v1 = k8s_clients.get("rbac_v1")

    @abstractmethod
    def run(self, namespace: Optional[str] = None) -> List[CheckResult]:
        """Execute the check and return findings."""
        ...
