#!/bin/bash
# AI Toolkit Web UI Startup Script
# This script is used by the systemd service to start the web UI

set -e

# Configuration
TOOLKIT_DIR="/home/jay/Documents/ai-toolkit"
UI_DIR="$TOOLKIT_DIR/ui"
VENV_DIR="$TOOLKIT_DIR/venv"
LOG_FILE="$TOOLKIT_DIR/webui.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting AI Toolkit Web UI..."

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    log "Virtual environment activated"
else
    log "ERROR: Virtual environment not found at $VENV_DIR"
    exit 1
fi

# Load environment variables
if [ -f "$TOOLKIT_DIR/.env" ]; then
    set -a
    source "$TOOLKIT_DIR/.env"
    set +a
    log "Environment variables loaded"
fi

# Change to UI directory
cd "$UI_DIR"
log "Changed directory to $UI_DIR"

# Check and initialize database if needed
DB_FILE="$TOOLKIT_DIR/aitk_db.db"
if [ ! -f "$DB_FILE" ] || [ ! -s "$DB_FILE" ]; then
    log "Database not initialized, running Prisma db push..."
    npx prisma db push 2>&1 | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "Database initialized successfully"
    else
        log "WARNING: Database initialization had issues, but continuing..."
    fi
else
    log "Database already initialized"
fi

# Check if node_modules exists and is valid
if [ ! -d "node_modules" ]; then
    log "node_modules not found, installing npm dependencies..."
    npm install 2>&1 | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        log "ERROR: npm install failed"
        exit 1
    fi
    log "npm install completed successfully"
elif [ ! -d "node_modules/.bin" ]; then
    log "node_modules corrupted (missing .bin), reinstalling..."
    rm -rf node_modules
    npm install 2>&1 | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        log "ERROR: npm install failed"
        exit 1
    fi
    log "npm install completed successfully"
elif [ ! -f "node_modules/.bin/tsc" ] || [ ! -f "node_modules/.bin/next" ]; then
    log "Required binaries missing, reinstalling npm dependencies..."
    rm -rf node_modules
    npm install 2>&1 | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        log "ERROR: npm install failed"
        exit 1
    fi
    log "npm install completed successfully"
else
    log "npm dependencies already installed and valid"
fi

# Check if we need to rebuild
FORCE_REBUILD="${FORCE_REBUILD:-false}"
REBUILD_NEEDED=false

if [ ! -d ".next" ]; then
    log "Build directory not found, building..."
    REBUILD_NEEDED=true
elif [ "$FORCE_REBUILD" = "true" ]; then
    log "FORCE_REBUILD set, rebuilding..."
    REBUILD_NEEDED=true
else
    # Check if source files are newer than build
    if [ -n "$(find src -type f -newer .next 2>/dev/null | head -1)" ]; then
        log "Source files changed since last build, rebuilding..."
        REBUILD_NEEDED=true
    else
        log "Next.js build is up to date, skipping..."
    fi
fi

if [ "$REBUILD_NEEDED" = "true" ]; then
    log "Building Next.js application..."
    npm run build 2>&1 | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        log "ERROR: npm build failed"
        exit 1
    fi
    log "Build completed successfully"
fi

# Start the server
log "Starting web UI server on port 8675..."
exec npm start
