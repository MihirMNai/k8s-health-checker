"""Data models for health check results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Severity(Enum):
    """Issue severity levels, ordered by urgency."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    PASS = "pass"

    @property
    def icon(self) -> str:
        return {
            Severity.CRITICAL: "🔴",
            Severity.WARNING: "🟡",
            Severity.INFO: "🔵",
            Severity.PASS: "🟢",
        }[self]

    @property
    def label(self) -> str:
        return self.value.upper()

    @property
    def weight(self) -> int:
        """Deduction points for health score calculation."""
        return {
            Severity.CRITICAL: 8,
            Severity.WARNING: 3,
            Severity.INFO: 1,
            Severity.PASS: 0,
        }[self]


class Category(Enum):
    """Check categories."""

    PODS = "pods"
    NODES = "nodes"
    RESOURCES = "resources"
    PROBES = "probes"
    SECURITY = "security"
    WORKLOADS = "workloads"
    AUTOSCALING = "autoscaling"

    @property
    def icon(self) -> str:
        return {
            Category.PODS: "🫛",
            Category.NODES: "🖥️",
            Category.RESOURCES: "📊",
            Category.PROBES: "🩺",
            Category.SECURITY: "🔒",
            Category.WORKLOADS: "⚙️",
            Category.AUTOSCALING: "📈",
        }[self]

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


@dataclass
class CheckResult:
    """A single health check finding."""

    name: str
    severity: Severity
    message: str
    category: Category
    namespace: Optional[str] = None
    resource: Optional[str] = None
    fix: Optional[str] = None
    details: Optional[str] = None

    @property
    def is_issue(self) -> bool:
        return self.severity != Severity.PASS


@dataclass
class ClusterSummary:
    """High-level cluster statistics."""

    cluster_name: str = "unknown"
    node_count: int = 0
    pod_total: int = 0
    pod_running: int = 0
    pod_pending: int = 0
    pod_failed: int = 0
    namespace_count: int = 0
    service_count: int = 0
    deployment_count: int = 0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0


@dataclass
class HealthReport:
    """Complete cluster health report."""

    cluster_name: str
    timestamp: datetime
    results: List[CheckResult] = field(default_factory=list)
    summary: ClusterSummary = field(default_factory=ClusterSummary)
    scan_duration_seconds: float = 0.0
    namespaces_scanned: List[str] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    def add_all(self, results: List[CheckResult]) -> None:
        self.results.extend(results)

    # --- Filtering helpers ---

    @property
    def critical(self) -> List[CheckResult]:
        return [r for r in self.results if r.severity == Severity.CRITICAL]

    @property
    def warnings(self) -> List[CheckResult]:
        return [r for r in self.results if r.severity == Severity.WARNING]

    @property
    def info(self) -> List[CheckResult]:
        return [r for r in self.results if r.severity == Severity.INFO]

    @property
    def passed(self) -> List[CheckResult]:
        return [r for r in self.results if r.severity == Severity.PASS]

    @property
    def issues(self) -> List[CheckResult]:
        return [r for r in self.results if r.is_issue]

    def by_category(self, category: Category) -> List[CheckResult]:
        return [r for r in self.results if r.category == category]

    # --- Health score ---

    @property
    def score(self) -> int:
        """Calculate health score from 0-100.

        Starts at 100, deducts points per issue:
          CRITICAL = -8 points
          WARNING  = -3 points
          INFO     = -1 point
        Minimum score is 0.
        """
        total = 100
        for result in self.results:
            total -= result.severity.weight
        return max(0, total)

    @property
    def grade(self) -> str:
        s = self.score
        if s >= 90:
            return "A"
        if s >= 75:
            return "B"
        if s >= 60:
            return "C"
        if s >= 40:
            return "D"
        return "F"

    @property
    def grade_color(self) -> str:
        return {
            "A": "green",
            "B": "yellow",
            "C": "orange3",
            "D": "red",
            "F": "bold red",
        }[self.grade]
