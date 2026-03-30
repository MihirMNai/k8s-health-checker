"""Rich console output — the beautiful terminal report."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from k8s_health_checker.models import Category, HealthReport, Severity

console = Console()


def print_report(report: HealthReport, verbose: bool = False) -> None:
    """Render the full health report to the terminal with Rich."""
    _print_header(report)
    _print_issues(report, Severity.CRITICAL, verbose=verbose)
    _print_issues(report, Severity.WARNING, verbose=verbose)
    _print_issues(report, Severity.INFO, verbose=verbose)
    _print_passed(report)
    _print_summary_table(report)
    _print_score(report)
    _print_footer(report)


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------


def _print_header(report: HealthReport) -> None:
    header = Text()
    header.append("🏥 Kubernetes Cluster Health Report\n", style="bold white")
    header.append(f"   Cluster:  {report.cluster_name}\n", style="dim")
    header.append(
        f"   Date:     {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
        style="dim",
    )
    if report.namespaces_scanned:
        ns_count = len(report.namespaces_scanned)
        label = f"{ns_count} namespaces" if ns_count > 3 else ", ".join(report.namespaces_scanned)
        header.append(f"   Scanned:  {label}", style="dim")

    console.print()
    console.print(Panel(header, border_style="cyan", padding=(1, 2)))


# ------------------------------------------------------------------
# Issues by severity
# ------------------------------------------------------------------


def _print_issues(report: HealthReport, severity: Severity, verbose: bool = False) -> None:
    items = [r for r in report.results if r.severity == severity]
    if not items:
        return

    color = {
        Severity.CRITICAL: "red",
        Severity.WARNING: "yellow",
        Severity.INFO: "blue",
    }[severity]

    count = len(items)
    title = f"{severity.icon}  {severity.label} ({count} issue{'s' if count != 1 else ''})"

    table = Table(
        show_header=True,
        header_style=f"bold {color}",
        border_style=color,
        title=title,
        title_style=f"bold {color}",
        expand=True,
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Check", style="bold", min_width=20)
    table.add_column("Details", ratio=2)
    table.add_column("Namespace", style="cyan", width=14)
    table.add_column("Resource", style="magenta", width=20)

    for i, result in enumerate(items, 1):
        detail = result.message
        if verbose and result.fix:
            detail += f"\n[dim]Fix: {result.fix}[/dim]"
        table.add_row(
            str(i),
            result.name,
            detail,
            result.namespace or "—",
            _truncate(result.resource or "—", 20),
        )

    console.print()
    console.print(table)


# ------------------------------------------------------------------
# Passed checks
# ------------------------------------------------------------------


def _print_passed(report: HealthReport) -> None:
    passed = report.passed
    if not passed:
        return

    title = f"🟢  PASSED ({len(passed)} check{'s' if len(passed) != 1 else ''})"

    table = Table(
        show_header=False,
        border_style="green",
        title=title,
        title_style="bold green",
        expand=True,
        padding=(0, 1),
    )
    table.add_column("", width=3)
    table.add_column("Check")

    for result in passed:
        table.add_row("✅", f"{result.name} — [dim]{result.message}[/dim]")

    console.print()
    console.print(table)


# ------------------------------------------------------------------
# Category summary table
# ------------------------------------------------------------------


def _print_summary_table(report: HealthReport) -> None:
    table = Table(
        title="📊  Summary by Category",
        title_style="bold white",
        show_header=True,
        header_style="bold",
        expand=True,
        border_style="dim",
        padding=(0, 1),
    )
    table.add_column("Category", style="bold")
    table.add_column("🔴 Critical", justify="center", width=10)
    table.add_column("🟡 Warning", justify="center", width=10)
    table.add_column("🔵 Info", justify="center", width=10)
    table.add_column("🟢 Pass", justify="center", width=10)

    for cat in Category:
        cat_results = report.by_category(cat)
        if not cat_results:
            continue
        crit = sum(1 for r in cat_results if r.severity == Severity.CRITICAL)
        warn = sum(1 for r in cat_results if r.severity == Severity.WARNING)
        info = sum(1 for r in cat_results if r.severity == Severity.INFO)
        ok = sum(1 for r in cat_results if r.severity == Severity.PASS)

        table.add_row(
            f"{cat.icon}  {cat.label}",
            _count_cell(crit, "red"),
            _count_cell(warn, "yellow"),
            _count_cell(info, "blue"),
            _count_cell(ok, "green"),
        )

    console.print()
    console.print(table)


# ------------------------------------------------------------------
# Score
# ------------------------------------------------------------------


def _print_score(report: HealthReport) -> None:
    score = report.score
    grade = report.grade
    color = report.grade_color

    bar_width = 40
    filled = int(score / 100 * bar_width)
    bar = f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (bar_width - filled)}[/dim]"

    summary = report.summary
    cluster_text = (
        f"   Nodes: {summary.node_count}  │  "
        f"Pods: {summary.pod_running} running, {summary.pod_pending} pending, "
        f"{summary.pod_failed} failed  │  "
        f"Deployments: {summary.deployment_count}  │  "
        f"Namespaces: {summary.namespace_count}"
    )

    score_text = Text()
    score_text.append("   Health Score:  ", style="bold")
    score_panel = Text.from_markup(
        f"   {bar}  [{color}]{score}/100  (Grade: {grade})[/{color}]\n\n"
        f"[dim]{cluster_text}[/dim]"
    )

    all_text = Text()
    all_text.append("📋  CLUSTER SCORE\n\n", style="bold white")
    all_text.append_text(score_panel)

    console.print()
    console.print(Panel(all_text, border_style=color, padding=(1, 2)))


# ------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------


def _print_footer(report: HealthReport) -> None:
    issues = len(report.issues)
    passed = len(report.passed)
    console.print()
    console.print(
        f"[dim]   Scan completed in {report.scan_duration_seconds}s  │  "
        f"{issues} issue{'s' if issues != 1 else ''}  │  "
        f"{passed} check{'s' if passed != 1 else ''} passed  │  "
        f"k8s-health-checker v1.0.0[/dim]"
    )
    console.print()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _count_cell(count: int, color: str) -> str:
    if count == 0:
        return "[dim]—[/dim]"
    return f"[{color}]{count}[/{color}]"
