# Installation

## Requirements

- Python 3.11+
- Git
- GitHub CLI (`gh`) — optional, used for PR queries in `ft work` status

## Quick Start

```bash
pip install formaltask
```

After installation, run the setup wizard:

```bash
ft setup
```

The setup wizard handles all configuration automatically, including:
- Database initialization
- Claude Code hook registration in `~/.claude/settings.json`
- Configuration verification via `ft doctor`

## Development Setup

For contributing to FormalTask or running from source:

```bash
# 1. Clone the repository
git clone https://github.com/davidabeyer/formaltask.git
cd formaltask

# 2. Create and activate virtual environment
python3 -m venv venv && source venv/bin/activate

# 3. Install dependencies and configure git hooks
./install.sh

# 4. Run setup wizard
ft setup
```

### Manual pip Installation

If you prefer manual installation:

```bash
pip install -e .
```

Note: You'll still need to run `ft setup` to register hooks and initialize the database.

## Troubleshooting

### Python Version Issues

FormalTask requires Python 3.11+. If you have multiple Python versions installed:

```bash
# Check your Python version
python3 --version

# On macOS with pyenv
pyenv install 3.11
pyenv local 3.11

# On Ubuntu/Debian
sudo apt install python3.11 python3.11-venv
```

### Shell Configuration Not Loading

If `ft` command is not found after installation, ensure your shell configuration is reloaded:

```bash
# For bash
source ~/.bashrc

# For zsh
source ~/.zshrc

# For fish
source ~/.config/fish/config.fish
```
