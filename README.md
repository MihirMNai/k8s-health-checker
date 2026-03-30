# 🏥 k8s-health-checker

![PyPI](https://img.shields.io/pypi/v/k8s-health-checker.svg) ![Python](https://img.shields.io/pypi/pyversions/k8s-health-checker) ![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg) ![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

**A powerful CLI tool to scan Kubernetes clusters for health issues, misconfigurations, and security risks.**

Run one command. Get a complete health report with severity ratings, fix suggestions, and a health score — right in your terminal.

```
$ k8s-health scan
```
---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🫛 **Pod Health** | CrashLoopBackOff, Pending, Failed, OOMKilled, high restarts |
| 🖥️ **Node Health** | NotReady, DiskPressure, MemoryPressure, PIDPressure, cordoned |
| 📊 **Resource Limits** | Missing CPU/memory requests and limits |
| 🩺 **Health Probes** | Missing readiness and liveness probes |
| 🔒 **Security** | NetworkPolicies, privileged containers, root UID, service accounts |
| ⚙️ **Workloads** | Deployment/StatefulSet/DaemonSet replicas, stuck rollouts |
| 📈 **Autoscaling** | HPA at max, min=max (disabled autoscaling), no HPAs |
| 🎯 **Health Score** | 0-100 score with letter grade (A-F) |
| 🎨 **Beautiful Output** | Rich terminal tables with colors and icons |
| 📄 **JSON Export** | Pipe results to other tools or dashboards |
| 🔍 **Verbose Mode** | Show detailed fix suggestions with `-v` |
| 🎮 **Demo Mode** | Try instantly — no cluster needed |

---

## 🚀 Quick Start

### Install

```bash
git clone https://github.com/MihirMNai/k8s-health-checker.git
cd k8s-health-checker
pip install -e ".[dev]"
```

### Try It (No Cluster Needed)

```bash
k8s-health scan --demo
```

This runs a full scan with realistic demo data — perfect for trying the tool before connecting to a real cluster.

### Scan Your Cluster

```bash
# Full cluster scan
k8s-health scan

# Scan a specific namespace
k8s-health scan -n production

# Scan specific categories only
k8s-health scan -c pods -c nodes

# JSON output (pipe to jq, file, or API)
k8s-health scan -o json
k8s-health scan -o json > report.json

# Verbose output with fix suggestions
k8s-health scan -v

# Just the health score
k8s-health score
```

---

## 📋 Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python** | 3.9 or higher |
| **kubectl** | Configured with access to your cluster |
| **RBAC** | Cluster-wide read access (or namespace-scoped) |

For demo mode, only Python is needed — no cluster, no kubectl, no credentials.

---

## 🔍 What It Checks (27 Rules)

### 🫛 Pods (6 rules)
- **CrashLoopBackOff** — containers crash-looping (CRITICAL)
- **OOMKilled** — containers killed by OOM killer (CRITICAL)
- **Failed state** — pods in Failed phase (CRITICAL)
- **Excessive restarts** — containers with 20+ restarts (CRITICAL)
- **Elevated restarts** — containers with 5+ restarts (WARNING)
- **Pending** — pods stuck in Pending phase (WARNING)

### 🖥️ Nodes (5 rules)
- **NotReady** — nodes not accepting workloads (CRITICAL)
- **DiskPressure** — nodes running out of disk (CRITICAL)
- **MemoryPressure** — nodes running out of memory (CRITICAL)
- **PIDPressure** — too many processes on node (WARNING)
- **Cordoned** — nodes marked unschedulable (INFO)

### 📊 Resources (2 rules)
- **Missing requests** — containers without CPU/memory requests (WARNING)
- **Missing limits** — containers without CPU/memory limits (WARNING)

### 🩺 Probes (2 rules)
- **Missing readiness probe** — traffic may hit unready containers (WARNING)
- **Missing liveness probe** — hung containers won't restart (INFO)

### 🔒 Security (4 rules)
- **Privileged containers** — full host access (CRITICAL)
- **Running as root** — UID 0 containers (WARNING)
- **No NetworkPolicies** — unrestricted pod communication (WARNING)
- **Default ServiceAccount** — pods using default SA (INFO)

### ⚙️ Workloads (5 rules)
- **No ready replicas** — deployment completely down (CRITICAL)
- **Partial readiness** — not all replicas ready (WARNING)
- **Stuck rollout** — rollout not progressing (WARNING)
- **Single replica** — no high availability (INFO)
- **Scaled to zero** — intentionally or accidentally (INFO)

### 📈 Autoscaling (3 rules)
- **HPA at max** — autoscaler can't add more replicas (WARNING)
- **HPA min = max** — autoscaling effectively disabled (INFO)
- **No HPAs** — no autoscaling configured (INFO)

---

## 📊 Health Score

The tool calculates a health score from **0 to 100**:

| Severity | Points Deducted |
|----------|----------------|
| 🔴 CRITICAL | -8 per issue |
| 🟡 WARNING | -3 per issue |
| 🔵 INFO | -1 per issue |
| 🟢 PASS | 0 |

| Score | Grade | Meaning |
|-------|-------|---------|
| 90-100 | **A** | Excellent — minimal issues |
| 75-89 | **B** | Good — some improvements needed |
| 60-74 | **C** | Fair — several issues to address |
| 40-59 | **D** | Poor — significant problems |
| 0-39 | **F** | Critical — immediate attention needed |

---

## 🔧 CLI Reference

```
Usage: k8s-health [OPTIONS] COMMAND [ARGS]...

🏥 k8s-health-checker — Scan Kubernetes clusters for health issues.

Commands:
  scan     Run a full health scan on your Kubernetes cluster.
  score    Show just the cluster health score (0-100).

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.
```

### `k8s-health scan`

```
Options:
  -n, --namespace TEXT        Scan a specific namespace only.
  -c, --category [pods|nodes|resources|probes|security|workloads|autoscaling]
                              Run only specific categories (repeatable).
  -o, --output [terminal|json]
                              Output format (default: terminal).
  -v, --verbose               Show detailed output with fix suggestions.
  --demo                      Run with demo data (no cluster needed).
  --help                      Show this message and exit.
```

### `k8s-health score`

```
Options:
  -n, --namespace TEXT  Scan a specific namespace.
  --demo                Use demo data.
  --help                Show this message and exit.
```

---

## 🏗️ Project Structure

```
k8s-health-checker/
├── k8s_health_checker/
│   ├── __init__.py          # Package metadata and version
│   ├── cli.py               # Click CLI entry point (scan, score)
│   ├── scanner.py           # Main scanner orchestrator
│   ├── models.py            # Data models (CheckResult, HealthReport, Severity)
│   ├── demo.py              # Demo mode data generator
│   ├── checks/
│   │   ├── base.py          # BaseChecker abstract class
│   │   ├── pods.py          # Pod health checks (6 rules)
│   │   ├── nodes.py         # Node health checks (5 rules)
│   │   ├── resources.py     # Resource limits checks (2 rules)
│   │   ├── probes.py        # Health probe checks (2 rules)
│   │   ├── security.py      # Security checks (4 rules)
│   │   ├── workloads.py     # Workload checks (5 rules)
│   │   └── autoscaling.py   # HPA checks (3 rules)
│   └── output/
│       ├── console.py       # Rich terminal renderer
│       └── json_out.py      # JSON output formatter
├── tests/
│   ├── conftest.py          # Test fixtures and mock builders
│   └── test_checks.py       # 53 tests covering all checkers
├── .github/
│   └── workflows/
│       └── ci.yml           # CI pipeline (test + lint + publish)
├── Dockerfile               # Multi-stage Docker build
├── pyproject.toml           # Project config (hatchling)
├── CONTRIBUTING.md          # Contributor guide
├── LICENSE                  # MIT License
└── README.md
```

---

## 🧪 Testing

```bash
# Run all 53 tests
pytest

# With coverage
pytest --cov=k8s_health_checker --cov-report=term-missing

# Run specific test class
pytest tests/test_checks.py::TestPodChecker -v

# Run linter
ruff check .
```

Test coverage includes:
- **Pod checks** — healthy, crash loop, pending, failed, OOMKilled, restart thresholds, namespace-scoped
- **Node checks** — ready, NotReady, DiskPressure, MemoryPressure, PIDPressure, cordoned, multi-condition
- **Resource checks** — all defined, missing requests, missing limits, missing both
- **Probe checks** — all present, missing readiness, missing liveness, missing both
- **Security checks** — privileged containers, root containers, no NetworkPolicies
- **Workload checks** — healthy, unhealthy, partial readiness, single replica, scaled to zero
- **Autoscaling checks** — at max, healthy, min=max, no HPAs
- **CLI tests** — version, help, demo scan (terminal + JSON + verbose), score
- **JSON output** — structure validation, field completeness
- **Model edge cases** — score clamping, grade boundaries, severity/category properties, filtering

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---


## 🐳 Docker

Run without installing Python:

```bash
# Build the image
docker build -t k8s-health-checker .

# Run demo mode
docker run --rm k8s-health-checker scan --demo

# Run with kubeconfig mount
docker run --rm -v ~/.kube:/home/appuser/.kube:ro k8s-health-checker scan

# JSON output
docker run --rm k8s-health-checker scan --demo -o json
```
