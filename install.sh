#!/usr/bin/env bash
set -euo pipefail

# install.sh - Bootstrap script for formaltask development environment
# Idempotent: safe to run multiple times

echo "=== FormalTask Setup ==="

# Check Python version (requires 3.11+)
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found in PATH"
    exit 1
fi

python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
required_major=3
required_minor=11

major="${python_version%%.*}"
minor="${python_version#*.}"

if [[ "${major}" -lt "${required_major}" ]] || { [[ "${major}" -eq "${required_major}" ]] && [[ "${minor}" -lt "${required_minor}" ]]; }; then
    echo "ERROR: Python 3.11+ required (found ${python_version})"
    echo ""
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "Install via: brew install python@3.11"
    else
        echo "Install via: sudo apt install python3.11"
    fi
    echo "Or use pyenv: pyenv install 3.11 && pyenv global 3.11"
    exit 1
fi
echo "Python ${python_version}"

# Create venv if not in virtual environment
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    echo "Creating venv at ~/.formaltask/venv..."
    python3 -m venv ~/.formaltask/venv
    # shellcheck source=/dev/null
    source ~/.formaltask/venv/bin/activate
    echo "Activated venv at ~/.formaltask/venv"
fi

# Verify we're in the project root
if [[ ! -f pyproject.toml ]]; then
    echo "ERROR: pyproject.toml not found. Run this script from the project root."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
python3 -m pip install -e .
echo "Dependencies installed"

# Configure git hooks
if ! git rev-parse --git-dir &>/dev/null; then
    echo "Warning: Not a git repository, skipping hooks setup"
elif [[ -d .githooks ]]; then
    current_hooks_path=$(git config --get core.hooksPath 2>/dev/null || echo "")
    if [[ "${current_hooks_path}" != ".githooks" ]]; then
        if [[ -n "${current_hooks_path}" ]]; then
            echo "Warning: Overwriting existing core.hooksPath (was: ${current_hooks_path})"
        fi
        git config core.hooksPath .githooks
        echo "Git hooks configured"
    else
        echo "Git hooks already configured"
    fi
else
    echo "Warning: .githooks directory not found, skipping hooks setup"
fi

# Check for required environment variables
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    echo "Warning: OPENROUTER_API_KEY not set (required for LLM operations)"
fi

echo ""
echo "=== Running ft setup ==="
ft setup --yes

echo ""
echo "=== Setup Complete ==="
echo "Run 'ft --help' to get started"
