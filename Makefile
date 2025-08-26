# -------- Settings you can tweak --------
# Variables (so you only need to change things in one place)
PYTHON := python            # which Python to use; change to 'python3' if needed
PKG    := .             # your source folder/package (change if different, just "." if main.py lives in the root)

# -------- Declare "phony" targets --------
# These targets don't create files named 'install', 'test', etc.
# Marking them .PHONY forces make to always run them (not skip due to timestamps).
.PHONY: install test lint format format-check security-code security-deps security all help

# -------- Install dependencies --------
# Installs BOTH runtime deps (requirements.txt) and dev tools (requirements-dev.txt).
# Keep this if you want a one-liner to set up your dev environment.
install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

# -------- Run tests --------
# Executes your pytest test suite. Fails the build if tests fail.
test:
	pytest -q

# -------- Lint (style + common mistakes) --------
# Uses Ruff to catch issues like unused imports, bad patterns, etc.
# Keep this to enforce code quality.
lint:
	ruff check .

# -------- Auto-format code --------
# Uses Black to reformat files (in-place) to a standard style.
# Keep this for consistent formatting across the team.
format:
	black .

# -------- Verify formatting only --------
# Fails if files are not formatted (does not change them).
# Keep this if you want a "check mode" like CI has.
format-check:
	black --check .

# -------- Security: code scanning (Bandit) --------
# Scans your SOURCE CODE for common security issues (e.g., unsafe usage).
# Keep this if security matters (recommended).
security-code:
	bandit -q -r $(PKG)

# -------- Security: dependency vulnerabilities (pip-audit) --------
# Scans INSTALLED DEPENDENCIES for known CVEs (public advisories).
# Keep this to be alerted about vulnerable packages (recommended).
security-deps:
	pip-audit

# -------- Aggregate security target --------
# Runs both code and dependency security checks.
security: security-code security-deps

# -------- Run a typical "pre-CI" pipeline locally --------
# This runs targets in the ORDER listed: install -> lint -> format-check -> test -> security
# Keep this to simulate what CI does before you push.
all-basic: install lint format-check test

all-advanced: install lint format-check test security

# -------- List available commands --------
# Prints a tiny help menu (doesn't run anything).
help:
	@echo "make install         # install runtime + dev dependencies"
	@echo "make test            # run test suite (pytest)"
	@echo "make lint            # run linter (ruff)"
	@echo "make format          # auto-format code (black)"
	@echo "make format-check    # verify formatting without changing files"
	@echo "make security-code   # scan source code security issues (bandit)"
	@echo "make security-deps   # scan dependency vulnerabilities (pip-audit)"
	@echo "make security        # run both security checks"
	@echo "make all-basic       # install -> lint -> format-check -> test -> security"
	@echo "make all-advanced    # install -> lint -> format-check -> test -> security"
