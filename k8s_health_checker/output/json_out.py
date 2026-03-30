"""JSON output formatter."""

from __future__ import annotations

import json
from typing import TextIO

from k8s_health_checker.models import HealthReport


def write_json(report: HealthReport, output: TextIO | None = None) -> str:
    """Serialize the report to JSON.

    If *output* is provided, writes to the file handle and returns the path.
    Otherwise returns the JSON string.
    """
    data = {
        "cluster": report.cluster_name,
        "timestamp": report.timestamp.isoformat(),
        "score": report.score,
        "grade": report.grade,
        "scan_duration_seconds": report.scan_duration_seconds,
        "summary": {
            "nodes": report.summary.node_count,
            "pods_total": report.summary.pod_total,
            "pods_running": report.summary.pod_running,
            "pods_pending": report.summary.pod_pending,
            "pods_failed": report.summary.pod_failed,
            "namespaces": report.summary.namespace_count,
            "services": report.summary.service_count,
            "deployments": report.summary.deployment_count,
        },
        "issues": [
            {
                "name": r.name,
                "severity": r.severity.value,
                "message": r.message,
                "category": r.category.value,
                "namespace": r.namespace,
                "resource": r.resource,
                "fix": r.fix,
            }
            for r in report.results
            if r.is_issue
        ],
        "passed": [
            {
                "name": r.name,
                "message": r.message,
                "category": r.category.value,
            }
            for r in report.passed
        ],
        "counts": {
            "critical": len(report.critical),
            "warning": len(report.warnings),
            "info": len(report.info),
            "passed": len(report.passed),
        },
    }

    json_str = json.dumps(data, indent=2, default=str)

    if output:
        output.write(json_str)
        return json_str

    return json_str
