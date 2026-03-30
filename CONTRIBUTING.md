# Contributing to k8s-health-checker

Thank you for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Fork and clone
git clone https://github.com/MihirMNai/k8s-health-checker.git
cd k8s-health-checker

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --cov              # With coverage report
pytest tests/test_checks.py::TestPodChecker  # Run specific test class
```

## Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting:

```bash
ruff check .              # Check for issues
ruff check --fix .        # Auto-fix issues
ruff format .             # Format code
```

## Adding a New Health Check

1. Create a new file in `k8s_health_checker/checks/` (or add to an existing one)
2. Inherit from `BaseChecker` and set the `category` class attribute
3. Implement the `run()` method returning `List[CheckResult]`
4. Register the checker in `k8s_health_checker/scanner.py` → `ALL_CHECKERS`
5. Add demo findings in `k8s_health_checker/demo.py`
6. Add tests in `tests/test_checks.py`

### Example:

```python
from k8s_health_checker.checks.base import BaseChecker
from k8s_health_checker.models import Category, CheckResult, Severity

class MyChecker(BaseChecker):
    category = Category.PODS  # or a new category

    def run(self, namespace=None):
        results = []
        # ... your check logic ...
        results.append(CheckResult(
            name="My check name",
            severity=Severity.WARNING,
            message="Description of the issue found.",
            category=self.category,
            namespace="production",
            resource="resource-name",
            fix="How to fix this issue.",
        ))
        return results
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-check`
3. Write your code and tests
4. Ensure all tests pass: `pytest`
5. Ensure code is clean: `ruff check .`
6. Commit with a descriptive message
7. Push and open a Pull Request

## Reporting Issues

Please include:
- Python version (`python --version`)
- k8s-health-checker version (`k8s-health --version`)
- Kubernetes version (`kubectl version`)
- Steps to reproduce the issue
- Expected vs actual behavior
