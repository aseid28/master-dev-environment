#!/usr/bin/env bash
# ============================================================
# Cloud VM provisioner — Ubuntu 22.04 LTS
# Idempotent: safe to re-run on an already-provisioned machine.
#
# Run as root or with sudo:
#   curl -fsSL <url>/provision.sh | bash
#   or: bash provision.sh
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[provision]${NC} $*"; }
warn() { echo -e "${YELLOW}[provision]${NC} $*"; }

# ── System packages ──────────────────────────────────────────
log "Updating apt..."
apt-get update -qq

log "Installing system deps..."
apt-get install -y -qq \
    tmux \
    curl \
    wget \
    git \
    build-essential \
    python3 \
    python3-venv \
    python3-pip \
    nodejs \
    npm \
    age \
    jq \
    unzip \
    ca-certificates \
    gnupg

# ── Python tooling ───────────────────────────────────────────
log "Upgrading pip..."
python3 -m pip install --quiet --upgrade pip

log "Installing Python packages..."
python3 -m pip install --quiet \
    pydantic \
    pyyaml \
    fastapi \
    uvicorn[standard] \
    sqlmodel \
    anthropic \
    bandit \
    semgrep \
    httpx \
    pytest \
    pytest-asyncio

# ── ttyd (web terminal) ──────────────────────────────────────
if ! command -v ttyd &>/dev/null; then
    log "Installing ttyd..."
    TTYD_VERSION="1.7.4"
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64) TTYD_ARCH="x86_64" ;;
        aarch64) TTYD_ARCH="aarch64" ;;
        *) warn "Unknown arch $ARCH — skipping ttyd"; TTYD_ARCH="" ;;
    esac
    if [ -n "$TTYD_ARCH" ]; then
        wget -q "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${TTYD_ARCH}" \
            -O /usr/local/bin/ttyd
        chmod +x /usr/local/bin/ttyd
        log "ttyd installed at /usr/local/bin/ttyd"
    fi
else
    log "ttyd already installed: $(ttyd --version 2>&1 | head -1)"
fi

# ── Claude Code CLI ──────────────────────────────────────────
if ! command -v claude &>/dev/null; then
    log "Installing Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code
else
    log "Claude Code already installed: $(claude --version 2>&1 | head -1)"
fi

# ── Node.js (for dashboard frontend) ────────────────────────
NODE_VERSION=$(node --version 2>/dev/null || echo "none")
log "Node.js: $NODE_VERSION"
if ! command -v npx &>/dev/null; then
    warn "npx not found — dashboard frontend builds may fail"
fi

# ── Directories ──────────────────────────────────────────────
log "Creating runtime directories..."
mkdir -p /opt/agent-env/.sessions
mkdir -p /opt/agent-env/credentials
chmod 700 /opt/agent-env/credentials

# ── tmux config ──────────────────────────────────────────────
TMUX_CONF="$HOME/.tmux.conf"
if [ ! -f "$TMUX_CONF" ]; then
    log "Writing tmux config..."
    cat > "$TMUX_CONF" <<'EOF'
# Agent environment tmux config
set -g history-limit 50000
set -g default-terminal "screen-256color"
set -g status-right "[#{session_name}] %H:%M"
set -g status-left ""
setw -g monitor-activity on
EOF
fi

# ── Systemd service for dashboard backend ───────────────────
SERVICE_FILE="/etc/systemd/system/agent-dashboard.service"
if [ ! -f "$SERVICE_FILE" ]; then
    log "Creating dashboard systemd service (disabled by default)..."
    cat > "$SERVICE_FILE" <<'EOF'
[Unit]
Description=Agent Dashboard Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/agent-env/master-dev-environment/dashboard/backend
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    log "Dashboard service created. Enable with: systemctl enable --now agent-dashboard"
fi

# ── Verification ─────────────────────────────────────────────
log "Verifying installations..."
python3 -c "import pydantic, yaml, fastapi, sqlmodel, anthropic; print('  Python packages OK')"
command -v tmux && tmux -V
command -v ttyd && ttyd --version 2>&1 | head -1 || true
command -v claude && claude --version 2>&1 | head -1 || warn "claude CLI not found — run: npm install -g @anthropic-ai/claude-code"
command -v age && echo "  age OK"

log "Provisioning complete."
log "Next: clone your repo to /opt/agent-env/ and run the orchestrator."
