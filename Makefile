# -------- Settings you can tweak --------
# $(PYTHON) isn't required with UV, but we keep a PKG path for reuse.
PKG := .               # your source folder (e.g., ".", "my_app", or "src/my_app")

# -------- PHONY targets --------
# Mark these as always-run (they don't produce files named 'install', etc.)
.PHONY: install test lint format format-check security-code security-deps security all help

# -------- Install all deps into .venv --------
# Creates .venv (if missing) and installs runtime + dev tools via UV.
install:
	uv sync

# -------- Run tests --------
# Use uv run so you don't need to activate the venv.
test:
	uv run pytest -q

# -------- Lint (Ruff) --------
lint:
	uv run ruff check .

# -------- Format (Black) --------
format:
	uv run black .

# -------- Format check (no changes) --------
format-check:
	uv run black --check .

# -------- Security: source code (Bandit) --------
# Change $(PKG) to your code path: ".", "my_app", or "src/my_app".
security-code:
	uv run bandit -q -r $(PKG)

# -------- Security: dependencies (pip-audit) --------
# Checks installed packages for known vulnerabilities (requires network).
security-deps:
	uv run pip-audit

# -------- Aggregate security --------
security: security-code security-deps

# -------- Run a typical "pre-CI" pipeline locally --------

# This runs targets in the ORDER listed: install -> lint -> format-check -> test

# Keep this to simulate what the most basic CI usually does before you push.

all-basic: install lint format-check test

# This runs targets/commands in the ORDER listed: install -> lint -> format-check -> test -> security

# Keep this to simulate what a more advanced/in-depth CI does before you push.

all-advanced: install lint format-check test security

# -------- Helper: list commands --------
help:
	@echo "make install         # create .venv and install deps (UV)"
	@echo "make test            # run tests (pytest) via UV"
	@echo "make lint            # lint with ruff"
	@echo "make format          # format with black"
	@echo "make format-check    # verify formatting"
	@echo "make security-code   # Bandit scan of source code"
	@echo "make security-deps   # pip-audit dependency vulnerabilities"
	@echo "make security        # both security checks"
	@echo "make all-basic		# install -> lint -> format-check -> test"
	@echo "make all-advanced    # install -> lint -> format-check -> test -> security"
