# Contributing to dj-wallets

Thank you for your interest in contributing to dj-wallets! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/khaledsukkar2/dj-wallets.git
   cd dj-wallets
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dj_wallet --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m security      # Security tests only
pytest -m "not slow"    # Skip slow tests
```

## Running Linters

```bash
# Run ruff linter
ruff check src/ tests/

# Run ruff formatter
ruff format src/ tests/

# Run type checker
mypy src/
```

## Multi-version Testing with Tox

```bash
# Run tests across all Python/Django versions
tox

# Run specific environment
tox -e py311-django42
```

## Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small
- Aim for 100% test coverage on new code

## Pull Request Process

1. **Fork the repository** and create your branch from `main`
2. **Write tests** for your changes
3. **Update documentation** if needed
4. **Run the test suite** and ensure all tests pass
5. **Run linters** and fix any issues
6. **Submit a pull request** with a clear description

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add wallet freezing functionality
fix: correct balance calculation in transfers
docs: update README with new examples
test: add security tests for race conditions
refactor: simplify transaction service
```

## Reporting Issues

When reporting issues, please include:

- Python version
- Django version
- dj-wallets version
- Minimal reproducible example
- Expected vs actual behavior

## Security Issues

For security vulnerabilities, please **do not** open a public issue. Instead, contact the maintainers directly at khaled.sukkar.contact@gmail.com.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
