"""CLI entry point — all commands are defined here."""

from __future__ import annotations

import sys

import click
from rich.console import Console

from k8s_health_checker import __version__
from k8s_health_checker.models import Category

console = Console()


# ------------------------------------------------------------------
# Main CLI group
# ------------------------------------------------------------------


@click.group()
@click.version_option(__version__, prog_name="k8s-health-checker")
def cli() -> None:
    """🏥 k8s-health-checker — Scan Kubernetes clusters for health issues.

    Run a comprehensive health scan on your Kubernetes cluster to find
    pod failures, resource misconfigurations, security risks, and more.

    \b
    Quick start:
      k8s-health scan          Scan your cluster
      k8s-health scan --demo   Try with demo data (no cluster needed)
      k8s-health score         Just show the health score
    """
    pass


# ------------------------------------------------------------------
# scan command
# ------------------------------------------------------------------


@cli.command()
@click.option(
    "-n",
    "--namespace",
    default=None,
    help="Scan a specific namespace only.",
)
@click.option(
    "-c",
    "--category",
    "categories",
    multiple=True,
    type=click.Choice(
        [c.value for c in Category],
        case_sensitive=False,
    ),
    help="Run only specific check categories (can be repeated).",
)
@click.option(
    "-o",
    "--output",
    "output_format",
    type=click.Choice(["terminal", "json"], case_sensitive=False),
    default="terminal",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--demo",
    is_flag=True,
    default=False,
    help="Run with demo data (no cluster needed).",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed output including passed checks and fix suggestions.",
)
def scan(
    namespace: str | None,
    categories: tuple[str, ...],
    output_format: str,
    demo: bool,
    verbose: bool,
) -> None:
    """Run a full health scan on your Kubernetes cluster.

    \b
    Examples:
      k8s-health scan                          Full cluster scan
      k8s-health scan --demo                   Demo mode (no cluster)
      k8s-health scan -n production            Scan one namespace
      k8s-health scan -c pods -c nodes         Scan specific categories
      k8s-health scan -o json                  JSON output
      k8s-health scan -o json > report.json    Save JSON to file
      k8s-health scan -v                       Verbose output
    """
    if demo:
        report = _run_demo(quiet=output_format == "json")
    else:
        report = _run_live_scan(namespace, categories)

    # Output
    if output_format == "json":
        from k8s_health_checker.output.json_out import write_json

        click.echo(write_json(report))
    else:
        from k8s_health_checker.output.console import print_report

        print_report(report, verbose=verbose)


# ------------------------------------------------------------------
# score command
# ------------------------------------------------------------------


@cli.command()
@click.option("--demo", is_flag=True, default=False, help="Use demo data.")
@click.option("-n", "--namespace", default=None, help="Scan a specific namespace.")
def score(demo: bool, namespace: str | None) -> None:
    """Show just the cluster health score (0-100).

    \b
    Examples:
      k8s-health score            Score from live cluster
      k8s-health score --demo     Score from demo data
    """
    if demo:
        report = _run_demo()
    else:
        report = _run_live_scan(namespace, ())

    color = report.grade_color
    console.print()
    console.print(f"  Cluster: [bold]{report.cluster_name}[/bold]")
    console.print(
        f"  Score:   [{color}]{report.score}/100  (Grade: {report.grade})[/{color}]"
    )
    console.print(
        f"  Issues:  [red]{len(report.critical)} critical[/red], "
        f"[yellow]{len(report.warnings)} warnings[/yellow], "
        f"[blue]{len(report.info)} info[/blue]"
    )
    console.print()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _run_demo(quiet: bool = False):
    """Run in demo mode with synthetic data."""
    from k8s_health_checker.demo import generate_demo_report

    if not quiet:
        console.print("\n[dim]  ℹ️  Running in demo mode (no cluster connection)[/dim]")
    return generate_demo_report()


def _run_live_scan(namespace, categories):
    """Connect to a real cluster and scan."""
    from k8s_health_checker.models import Category as Cat
    from k8s_health_checker.scanner import Scanner

    scanner = Scanner()

    try:
        scanner.connect()
    except Exception as exc:
        console.print(
            f"\n[red]  ✖ Cannot connect to Kubernetes cluster:[/red] {exc}\n"
        )
        console.print("  [dim]Hints:[/dim]")
        console.print("  [dim]  • Is kubectl configured? Run: kubectl cluster-info[/dim]")
        console.print("  [dim]  • Try demo mode: k8s-health scan --demo[/dim]")
        console.print()
        sys.exit(1)

    cat_enums = [Cat(c) for c in categories] if categories else None
    return scanner.scan(namespace=namespace, categories=cat_enums)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    cli()
