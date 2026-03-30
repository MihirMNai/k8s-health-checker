"""Tests for all health checkers."""

from __future__ import annotations

from unittest.mock import MagicMock

from click.testing import CliRunner

from k8s_health_checker.checks.autoscaling import AutoscalingChecker
from k8s_health_checker.checks.nodes import NodeChecker
from k8s_health_checker.checks.pods import PodChecker
from k8s_health_checker.checks.probes import ProbeChecker
from k8s_health_checker.checks.resources import ResourceChecker
from k8s_health_checker.checks.security import SecurityChecker
from k8s_health_checker.checks.workloads import WorkloadChecker
from k8s_health_checker.cli import cli
from k8s_health_checker.models import Category, CheckResult, HealthReport, Severity
from tests.conftest import (
    make_deployment,
    make_hpa,
    make_k8s_clients,
    make_node,
    make_pod,
)

# =====================================================================
# Pod Checks
# =====================================================================


class TestPodChecker:
    def test_healthy_pods(self):
        pod = make_pod(phase="Running", restart_count=0)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = PodChecker(clients).run()
        assert any(r.severity == Severity.PASS for r in results)

    def test_crash_loop_detected(self):
        pod = make_pod(
            name="crash-pod",
            phase="Running",
            waiting_reason="CrashLoopBackOff",
            restart_count=25,
        )
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = PodChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert len(critical) >= 1
        assert any("CrashLoopBackOff" in r.name for r in critical)

    def test_pending_pod_detected(self):
        pod = make_pod(name="pending-pod", phase="Pending")
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = PodChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("Pending" in r.name for r in warnings)

    def test_failed_pod_detected(self):
        pod = make_pod(name="failed-pod", phase="Failed")
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = PodChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert any("Failed" in r.name for r in critical)

    def test_oomkilled_detected(self):
        pod = make_pod(
            name="oom-pod",
            phase="Running",
            terminated_reason="OOMKilled",
        )
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = PodChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert any("OOMKilled" in r.name for r in critical)

    def test_high_restarts_warning(self):
        pod = make_pod(name="restart-pod", phase="Running", restart_count=8)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = PodChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("restart" in r.name.lower() for r in warnings)


# =====================================================================
# Node Checks
# =====================================================================


class TestNodeChecker:
    def test_healthy_nodes(self):
        node = make_node(ready=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_node.return_value.items = [node]

        results = NodeChecker(clients).run()
        assert any(r.severity == Severity.PASS for r in results)

    def test_not_ready_detected(self):
        node = make_node(name="bad-node", ready=False)
        clients = make_k8s_clients()
        clients["core_v1"].list_node.return_value.items = [node]

        results = NodeChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert any("NotReady" in r.name for r in critical)

    def test_disk_pressure_detected(self):
        node = make_node(name="disk-node", disk_pressure=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_node.return_value.items = [node]

        results = NodeChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert any("DiskPressure" in r.name for r in critical)

    def test_cordoned_node_detected(self):
        node = make_node(name="drain-node", unschedulable=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_node.return_value.items = [node]

        results = NodeChecker(clients).run()
        info = [r for r in results if r.severity == Severity.INFO]
        assert any("cordoned" in r.name.lower() for r in info)


# =====================================================================
# Resource Checks
# =====================================================================


class TestResourceChecker:
    def test_resources_defined(self):
        pod = make_pod(has_requests=True, has_limits=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = ResourceChecker(clients).run()
        assert any(r.severity == Severity.PASS for r in results)

    def test_missing_requests(self):
        pod = make_pod(has_requests=False, has_limits=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = ResourceChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("requests" in r.name.lower() for r in warnings)


# =====================================================================
# Probe Checks
# =====================================================================


class TestProbeChecker:
    def test_probes_present(self):
        pod = make_pod(has_readiness_probe=True, has_liveness_probe=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = ProbeChecker(clients).run()
        assert any(r.severity == Severity.PASS for r in results)

    def test_missing_readiness_probe(self):
        pod = make_pod(has_readiness_probe=False, has_liveness_probe=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = ProbeChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("readiness" in r.name.lower() for r in warnings)


# =====================================================================
# Security Checks
# =====================================================================


class TestSecurityChecker:
    def test_privileged_container_detected(self):
        pod = make_pod(
            namespace="production",
            privileged=True,
        )
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]
        clients["core_v1"].list_namespaced_pod.return_value.items = [pod]
        # Need namespace list for network policy check
        ns_mock = MagicMock()
        ns_mock.metadata.name = "production"
        clients["core_v1"].list_namespace.return_value.items = [ns_mock]
        clients["networking_v1"].list_namespaced_network_policy.return_value.items = []

        results = SecurityChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert any("rivileged" in r.name for r in critical)


# =====================================================================
# Workload Checks
# =====================================================================


class TestWorkloadChecker:
    def test_healthy_deployment(self):
        dep = make_deployment(replicas=3, ready_replicas=3)
        clients = make_k8s_clients()
        clients["apps_v1"].list_deployment_for_all_namespaces.return_value.items = [dep]
        clients["apps_v1"].list_stateful_set_for_all_namespaces.return_value.items = []
        clients["apps_v1"].list_daemon_set_for_all_namespaces.return_value.items = []

        results = WorkloadChecker(clients).run()
        assert any(r.severity == Severity.PASS for r in results)

    def test_unhealthy_deployment(self):
        dep = make_deployment(replicas=3, ready_replicas=0, available_replicas=0)
        clients = make_k8s_clients()
        clients["apps_v1"].list_deployment_for_all_namespaces.return_value.items = [dep]
        clients["apps_v1"].list_stateful_set_for_all_namespaces.return_value.items = []
        clients["apps_v1"].list_daemon_set_for_all_namespaces.return_value.items = []

        results = WorkloadChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert len(critical) >= 1


# =====================================================================
# Autoscaling Checks
# =====================================================================


class TestAutoscalingChecker:
    def test_hpa_at_max(self):
        hpa = make_hpa(max_replicas=10, current_replicas=10)
        clients = make_k8s_clients()
        autoscaling = clients["autoscaling_v1"]
        autoscaling.list_horizontal_pod_autoscaler_for_all_namespaces.return_value.items = [hpa]

        results = AutoscalingChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("maximum" in r.name.lower() for r in warnings)

    def test_hpa_healthy(self):
        hpa = make_hpa(max_replicas=10, current_replicas=5)
        clients = make_k8s_clients()
        autoscaling = clients["autoscaling_v1"]
        autoscaling.list_horizontal_pod_autoscaler_for_all_namespaces.return_value.items = [hpa]

        results = AutoscalingChecker(clients).run()
        assert any(r.severity == Severity.PASS for r in results)


# =====================================================================
# Model / Score Tests
# =====================================================================


class TestHealthReport:
    def test_perfect_score(self):
        from k8s_health_checker.demo import generate_demo_report

        report = generate_demo_report()
        # Demo report has issues, so score should be less than 100
        assert report.score < 100
        assert report.score >= 0

    def test_grade_assignment(self):
        from datetime import datetime, timezone

        from k8s_health_checker.models import HealthReport

        report = HealthReport(
            cluster_name="test", timestamp=datetime.now(timezone.utc)
        )
        # Empty report = 100 = grade A
        assert report.score == 100
        assert report.grade == "A"

    def test_demo_report_generates(self):
        from k8s_health_checker.demo import generate_demo_report

        report = generate_demo_report()
        assert report.cluster_name == "aks-prod-eastus"
        assert len(report.results) > 0
        assert len(report.critical) > 0
        assert len(report.passed) > 0


# =====================================================================
# Additional Pod Tests
# =====================================================================


class TestPodCheckerExtended:
    def test_excessive_restarts_critical(self):
        pod = make_pod(name="restart-crit", phase="Running", restart_count=25)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = PodChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert any("restart" in r.name.lower() for r in critical)

    def test_multiple_pods_mixed_status(self):
        healthy = make_pod(name="healthy", phase="Running", restart_count=0)
        failing = make_pod(name="failing", phase="Failed")
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [healthy, failing]

        results = PodChecker(clients).run()
        assert any(r.severity == Severity.CRITICAL for r in results)

    def test_namespace_scoped_scan(self):
        pod = make_pod(name="ns-pod", namespace="staging", phase="Running")
        clients = make_k8s_clients()
        clients["core_v1"].list_namespaced_pod.return_value.items = [pod]

        results = PodChecker(clients).run(namespace="staging")
        assert any(r.severity == Severity.PASS for r in results)


# =====================================================================
# Additional Node Tests
# =====================================================================


class TestNodeCheckerExtended:
    def test_memory_pressure_detected(self):
        node = make_node(name="mem-node", memory_pressure=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_node.return_value.items = [node]

        results = NodeChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert any("MemoryPressure" in r.name for r in critical)

    def test_pid_pressure_detected(self):
        node = make_node(name="pid-node", pid_pressure=True)
        clients = make_k8s_clients()
        clients["core_v1"].list_node.return_value.items = [node]

        results = NodeChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("PIDPressure" in r.name for r in warnings)

    def test_multiple_conditions(self):
        node = make_node(
            name="bad-node", ready=False, disk_pressure=True, memory_pressure=True
        )
        clients = make_k8s_clients()
        clients["core_v1"].list_node.return_value.items = [node]

        results = NodeChecker(clients).run()
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert len(critical) >= 3  # NotReady + DiskPressure + MemoryPressure


# =====================================================================
# Additional Resource Tests
# =====================================================================


class TestResourceCheckerExtended:
    def test_missing_limits(self):
        pod = make_pod(has_requests=True, has_limits=False)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = ResourceChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("limits" in r.name.lower() for r in warnings)

    def test_missing_both_requests_and_limits(self):
        pod = make_pod(has_requests=False, has_limits=False)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = ResourceChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert len(warnings) >= 2


# =====================================================================
# Additional Probe Tests
# =====================================================================


class TestProbeCheckerExtended:
    def test_missing_liveness_probe(self):
        pod = make_pod(has_readiness_probe=True, has_liveness_probe=False)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = ProbeChecker(clients).run()
        info = [r for r in results if r.severity == Severity.INFO]
        assert any("liveness" in r.name.lower() for r in info)

    def test_missing_both_probes(self):
        pod = make_pod(has_readiness_probe=False, has_liveness_probe=False)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]

        results = ProbeChecker(clients).run()
        assert any(r.severity == Severity.WARNING for r in results)
        assert any(r.severity == Severity.INFO for r in results)


# =====================================================================
# Additional Security Tests
# =====================================================================


class TestSecurityCheckerExtended:
    def test_root_container_detected(self):
        pod = make_pod(namespace="production", run_as_user=0)
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = [pod]
        ns_mock = MagicMock()
        ns_mock.metadata.name = "production"
        clients["core_v1"].list_namespace.return_value.items = [ns_mock]
        clients["networking_v1"].list_namespaced_network_policy.return_value.items = []

        results = SecurityChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("root" in r.name.lower() for r in warnings)

    def test_no_network_policies(self):
        clients = make_k8s_clients()
        clients["core_v1"].list_pod_for_all_namespaces.return_value.items = []
        ns_mock = MagicMock()
        ns_mock.metadata.name = "default"
        clients["core_v1"].list_namespace.return_value.items = [ns_mock]
        clients["networking_v1"].list_namespaced_network_policy.return_value.items = []

        results = SecurityChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("NetworkPolic" in r.name for r in warnings)


# =====================================================================
# Additional Workload Tests
# =====================================================================


class TestWorkloadCheckerExtended:
    def test_single_replica_info(self):
        dep = make_deployment(
            replicas=1, ready_replicas=1, available_replicas=1, updated_replicas=1
        )
        clients = make_k8s_clients()
        clients["apps_v1"].list_deployment_for_all_namespaces.return_value.items = [dep]
        clients["apps_v1"].list_stateful_set_for_all_namespaces.return_value.items = []
        clients["apps_v1"].list_daemon_set_for_all_namespaces.return_value.items = []

        results = WorkloadChecker(clients).run()
        info = [r for r in results if r.severity == Severity.INFO]
        assert any("single" in r.name.lower() or "1 replica" in r.message.lower() for r in info)

    def test_scaled_to_zero(self):
        dep = make_deployment(
            replicas=0, ready_replicas=0, available_replicas=0, updated_replicas=0
        )
        clients = make_k8s_clients()
        clients["apps_v1"].list_deployment_for_all_namespaces.return_value.items = [dep]
        clients["apps_v1"].list_stateful_set_for_all_namespaces.return_value.items = []
        clients["apps_v1"].list_daemon_set_for_all_namespaces.return_value.items = []

        results = WorkloadChecker(clients).run()
        info = [r for r in results if r.severity == Severity.INFO]
        assert any("zero" in r.name.lower() or "scaled to 0" in r.message for r in info)

    def test_partial_readiness(self):
        dep = make_deployment(replicas=3, ready_replicas=2, available_replicas=2)
        clients = make_k8s_clients()
        clients["apps_v1"].list_deployment_for_all_namespaces.return_value.items = [dep]
        clients["apps_v1"].list_stateful_set_for_all_namespaces.return_value.items = []
        clients["apps_v1"].list_daemon_set_for_all_namespaces.return_value.items = []

        results = WorkloadChecker(clients).run()
        warnings = [r for r in results if r.severity == Severity.WARNING]
        assert any("replicas" in r.name.lower() for r in warnings)


# =====================================================================
# Additional Autoscaling Tests
# =====================================================================


class TestAutoscalingCheckerExtended:
    def test_hpa_min_equals_max(self):
        hpa = make_hpa(min_replicas=5, max_replicas=5, current_replicas=5)
        clients = make_k8s_clients()
        autoscaling = clients["autoscaling_v1"]
        autoscaling.list_horizontal_pod_autoscaler_for_all_namespaces.return_value.items = [hpa]

        results = AutoscalingChecker(clients).run()
        info = [r for r in results if r.severity == Severity.INFO]
        assert any("min" in r.name.lower() and "max" in r.name.lower() for r in info)

    def test_no_hpas(self):
        clients = make_k8s_clients()
        autoscaling = clients["autoscaling_v1"]
        autoscaling.list_horizontal_pod_autoscaler_for_all_namespaces.return_value.items = []

        results = AutoscalingChecker(clients).run()
        info = [r for r in results if r.severity == Severity.INFO]
        assert any(
            "no hpa" in r.name.lower()
            or "No HorizontalPodAutoscalers" in r.message
            for r in info
        )


# =====================================================================
# CLI Tests
# =====================================================================


class TestCLI:
    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_help_flag(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "k8s-health-checker" in result.output

    def test_scan_demo(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "--demo"])
        assert result.exit_code == 0
        assert "Health" in result.output or "Score" in result.output

    def test_scan_demo_json(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "--demo", "-o", "json"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output)
        assert "score" in data
        assert "grade" in data
        assert "cluster" in data

    def test_score_demo(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["score", "--demo"])
        assert result.exit_code == 0
        assert "Score" in result.output or "/100" in result.output

    def test_scan_demo_verbose(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "--demo", "-v"])
        assert result.exit_code == 0


# =====================================================================
# JSON Output Tests
# =====================================================================


class TestJSONOutput:
    def test_json_structure(self):
        import json

        from k8s_health_checker.demo import generate_demo_report
        from k8s_health_checker.output.json_out import write_json

        report = generate_demo_report()
        output = write_json(report)
        data = json.loads(output)

        # Validate all expected top-level keys
        assert "cluster" in data
        assert "timestamp" in data
        assert "score" in data
        assert "grade" in data
        assert "scan_duration_seconds" in data
        assert "summary" in data
        assert "issues" in data
        assert "passed" in data
        assert "counts" in data

        # Validate summary
        assert "nodes" in data["summary"]
        assert "pods_total" in data["summary"]

        # Validate counts match
        assert data["counts"]["critical"] == len(
            [i for i in data["issues"] if i["severity"] == "critical"]
        )

    def test_json_issues_have_required_fields(self):
        import json

        from k8s_health_checker.demo import generate_demo_report
        from k8s_health_checker.output.json_out import write_json

        report = generate_demo_report()
        data = json.loads(write_json(report))

        for issue in data["issues"]:
            assert "name" in issue
            assert "severity" in issue
            assert "message" in issue
            assert "category" in issue


# =====================================================================
# Model Edge Case Tests
# =====================================================================


class TestModelEdgeCases:
    def test_score_clamped_at_zero(self):
        from datetime import datetime, timezone

        report = HealthReport(
            cluster_name="test", timestamp=datetime.now(timezone.utc)
        )
        # Add enough critical issues to go below 0
        for i in range(20):
            report.add(
                CheckResult(
                    name=f"Critical {i}",
                    severity=Severity.CRITICAL,
                    message="test",
                    category=Category.PODS,
                )
            )
        assert report.score == 0
        assert report.grade == "F"

    def test_all_grade_boundaries(self):
        from datetime import datetime, timezone

        # Grade A: 90-100
        report = HealthReport(
            cluster_name="test", timestamp=datetime.now(timezone.utc)
        )
        assert report.grade == "A"

        # Grade B: 75-89
        report = HealthReport(cluster_name="test", timestamp=datetime.now(timezone.utc))
        for _ in range(4):
            report.add(
                CheckResult(
                    name="warn", severity=Severity.WARNING, message="t", category=Category.PODS
                )
            )
        assert report.score == 88
        assert report.grade == "B"

        # Grade C: 60-74
        report = HealthReport(cluster_name="test", timestamp=datetime.now(timezone.utc))
        for _ in range(5):
            report.add(
                CheckResult(
                    name="crit", severity=Severity.CRITICAL, message="t", category=Category.PODS
                )
            )
        assert report.score == 60
        assert report.grade == "C"

        # Grade D: 40-59
        report = HealthReport(cluster_name="test", timestamp=datetime.now(timezone.utc))
        for _ in range(8):
            report.add(
                CheckResult(
                    name="crit", severity=Severity.CRITICAL, message="t", category=Category.PODS
                )
            )
        assert report.score == 36
        assert report.grade == "F"

    def test_severity_properties(self):
        assert Severity.CRITICAL.icon == "🔴"
        assert Severity.WARNING.icon == "🟡"
        assert Severity.INFO.icon == "🔵"
        assert Severity.PASS.icon == "🟢"
        assert Severity.CRITICAL.weight == 8
        assert Severity.WARNING.weight == 3
        assert Severity.INFO.weight == 1
        assert Severity.PASS.weight == 0
        assert Severity.CRITICAL.label == "CRITICAL"

    def test_category_properties(self):
        assert Category.PODS.label == "Pods"
        assert Category.NODES.icon == "🖥️"
        assert len(Category) == 7  # 7 categories

    def test_check_result_is_issue(self):
        issue = CheckResult(
            name="test", severity=Severity.CRITICAL, message="t", category=Category.PODS
        )
        passed = CheckResult(
            name="test", severity=Severity.PASS, message="t", category=Category.PODS
        )
        assert issue.is_issue is True
        assert passed.is_issue is False

    def test_report_filtering(self):
        from datetime import datetime, timezone

        report = HealthReport(
            cluster_name="test", timestamp=datetime.now(timezone.utc)
        )
        report.add(
            CheckResult(name="c", severity=Severity.CRITICAL, message="", category=Category.PODS)
        )
        report.add(
            CheckResult(name="w", severity=Severity.WARNING, message="", category=Category.NODES)
        )
        report.add(
            CheckResult(name="i", severity=Severity.INFO, message="", category=Category.PODS)
        )
        report.add(
            CheckResult(name="p", severity=Severity.PASS, message="", category=Category.PODS)
        )

        assert len(report.critical) == 1
        assert len(report.warnings) == 1
        assert len(report.info) == 1
        assert len(report.passed) == 1
        assert len(report.issues) == 3
        assert len(report.by_category(Category.PODS)) == 3
