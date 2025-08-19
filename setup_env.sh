#!/usr/bin/env bash
set -e

# === 1. Install build dependencies ===
echo "[*] Installing dependencies..."
sudo apt update
sudo apt install -y build-essential curl git \
  libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
  libsqlite3-dev llvm libncurses5-dev libncursesw5-dev \
  xz-utils tk-dev libffi-dev liblzma-dev python3-openssl

# === 2. Install pyenv ===
if [ ! -d "$HOME/.pyenv" ]; then
  echo "[*] Installing pyenv..."
  curl https://pyenv.run | bash
else
  echo "[*] pyenv already installed"
fi

# === 3. Add pyenv to shell if not present ===
if ! grep -q 'pyenv init' ~/.bashrc; then
  echo "[*] Updating ~/.bashrc..."
  cat <<'EOF' >> ~/.bashrc

# pyenv setup
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
EOF
fi

# Reload shell environment
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# === 4. Install Python with pyenv ===
PY_VER=3.12.5
if ! pyenv versions --bare | grep -q "$PY_VER"; then
  echo "[*] Installing Python $PY_VER..."
  pyenv install $PY_VER
fi

pyenv global $PY_VER
echo "[*] Using Python $(python --version)"

# === 5. Create project venv ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  echo "[*] Creating virtual environment..."
  python -m venv .venv
fi

# === 6. Start MySQL ===
if ! systemctl is-active --quiet mysql; then
    sudo systemctl start mysql
fi

# === 7. Install dependencies ===
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
deactivate
echo "[*] Setup complete."
echo "[*] Running the application..."
python run.py
