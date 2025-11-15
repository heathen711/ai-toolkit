#!/bin/bash
# AI Toolkit Web UI Service Management Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SERVICE_NAME="ai-toolkit-webui"
SERVICE_FILE="ai-toolkit-webui.service"
SYSTEMD_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STARTUP_SCRIPT="${SCRIPT_DIR}/start-webui.sh"

# Helper functions
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_info() { echo -e "${BLUE}→${NC} $1"; }

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_error "Don't run this script as root. Use sudo when prompted."
        exit 1
    fi
}

# Install service
install_service() {
    print_info "Installing AI Toolkit Web UI service..."

    # Make startup script executable
    chmod +x "$STARTUP_SCRIPT"
    print_success "Made startup script executable"

    # Copy service file to systemd directory
    sudo cp "${SCRIPT_DIR}/${SERVICE_FILE}" "$SYSTEMD_PATH"
    print_success "Copied service file to $SYSTEMD_PATH"

    # Reload systemd daemon
    sudo systemctl daemon-reload
    print_success "Reloaded systemd daemon"

    # Enable service
    sudo systemctl enable "$SERVICE_NAME"
    print_success "Enabled service to start on boot"

    echo ""
    print_success "Service installed successfully!"
    echo ""
    echo "Next steps:"
    echo "  Start service:    sudo systemctl start $SERVICE_NAME"
    echo "  Check status:     sudo systemctl status $SERVICE_NAME"
    echo "  View logs:        sudo journalctl -u $SERVICE_NAME -f"
    echo "  Stop service:     sudo systemctl stop $SERVICE_NAME"
}

# Uninstall service
uninstall_service() {
    print_info "Uninstalling AI Toolkit Web UI service..."

    # Stop service if running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        sudo systemctl stop "$SERVICE_NAME"
        print_success "Stopped service"
    fi

    # Disable service
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        sudo systemctl disable "$SERVICE_NAME"
        print_success "Disabled service"
    fi

    # Remove service file
    if [ -f "$SYSTEMD_PATH" ]; then
        sudo rm "$SYSTEMD_PATH"
        print_success "Removed service file"
    fi

    # Reload systemd daemon
    sudo systemctl daemon-reload
    print_success "Reloaded systemd daemon"

    echo ""
    print_success "Service uninstalled successfully!"
}

# Start service
start_service() {
    print_info "Starting AI Toolkit Web UI service..."
    sudo systemctl start "$SERVICE_NAME"
    sleep 2

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service started successfully!"
        echo ""
        echo "Web UI should be accessible at: http://localhost:8675"
        echo ""
        echo "View logs with: sudo journalctl -u $SERVICE_NAME -f"
    else
        print_error "Service failed to start. Check logs with: sudo journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
}

# Stop service
stop_service() {
    print_info "Stopping AI Toolkit Web UI service..."
    sudo systemctl stop "$SERVICE_NAME"
    print_success "Service stopped"
}

# Restart service
restart_service() {
    print_info "Restarting AI Toolkit Web UI service..."
    sudo systemctl restart "$SERVICE_NAME"
    sleep 2

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service restarted successfully!"
    else
        print_error "Service failed to restart. Check logs with: sudo journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
}

# Rebuild and restart service
rebuild_service() {
    print_info "Force rebuilding and restarting Web UI..."
    echo ""

    # Stop the service
    print_info "Stopping service..."
    sudo systemctl stop "$SERVICE_NAME"
    print_success "Service stopped"

    # Remove the build directory to force rebuild
    print_info "Removing old build..."
    cd "${SCRIPT_DIR}/ui"
    if [ -d ".next" ]; then
        rm -rf .next
        print_success "Old build removed"
    else
        print_warning "No existing build found"
    fi

    # Start the service (startup script will rebuild)
    print_info "Starting service (will rebuild automatically)..."
    sudo systemctl start "$SERVICE_NAME"

    if [ $? -eq 0 ]; then
        print_success "Service starting with fresh build"
        echo ""
        print_warning "Waiting for build to complete (this may take 30-60 seconds)..."
        sleep 10

        # Check if service is still running
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            print_success "Service is running!"
            echo ""
            echo "Web UI should be accessible at: http://localhost:8675"
            echo ""
            echo "Monitor build progress with: ./manage-webui-service.sh follow"
        else
            print_error "Service failed to start. Check logs with: sudo journalctl -u $SERVICE_NAME -n 50"
            exit 1
        fi
    else
        print_error "Failed to start service"
        exit 1
    fi
}

# Show status
show_status() {
    echo ""
    sudo systemctl status "$SERVICE_NAME" --no-pager
    echo ""
    echo "Service file: $SYSTEMD_PATH"
    echo "Startup script: $STARTUP_SCRIPT"
    echo "Web UI URL: http://localhost:8675"
}

# Show logs
show_logs() {
    local lines="${1:-50}"
    print_info "Showing last $lines lines of logs..."
    echo ""
    sudo journalctl -u "$SERVICE_NAME" -n "$lines" --no-pager
    echo ""
    echo "Follow logs live with: sudo journalctl -u $SERVICE_NAME -f"
}

# Follow logs
follow_logs() {
    print_info "Following logs (Ctrl+C to exit)..."
    echo ""
    sudo journalctl -u "$SERVICE_NAME" -f
}

# Test configuration
test_config() {
    print_info "Testing configuration..."
    echo ""

    # Check if service file exists
    if [ ! -f "${SCRIPT_DIR}/${SERVICE_FILE}" ]; then
        print_error "Service file not found: ${SCRIPT_DIR}/${SERVICE_FILE}"
        exit 1
    fi
    print_success "Service file exists"

    # Check if startup script exists
    if [ ! -f "$STARTUP_SCRIPT" ]; then
        print_error "Startup script not found: $STARTUP_SCRIPT"
        exit 1
    fi
    print_success "Startup script exists"

    # Check if startup script is executable
    if [ ! -x "$STARTUP_SCRIPT" ]; then
        print_warning "Startup script not executable (will be fixed on install)"
    else
        print_success "Startup script is executable"
    fi

    # Check if venv exists
    if [ ! -d "${SCRIPT_DIR}/venv" ]; then
        print_error "Virtual environment not found. Run setup_venv.sh first"
        exit 1
    fi
    print_success "Virtual environment exists"

    # Check if UI directory exists
    if [ ! -d "${SCRIPT_DIR}/ui" ]; then
        print_error "UI directory not found"
        exit 1
    fi
    print_success "UI directory exists"

    # Check if .env exists
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        print_warning ".env file not found (will be created on first run)"
    else
        print_success ".env file exists"
    fi

    echo ""
    print_success "Configuration test passed!"
}

# Show usage
show_usage() {
    cat << EOF
AI Toolkit Web UI Service Management

Usage: $0 <command> [options]

Commands:
  install         Install the systemd service
  uninstall       Uninstall the systemd service
  start           Start the service
  stop            Stop the service
  restart         Restart the service
  rebuild         Force rebuild Next.js and restart service
  status          Show service status
  logs [N]        Show last N lines of logs (default: 50)
  follow          Follow logs in real-time
  test            Test configuration before installing
  help            Show this help message

Examples:
  $0 install              # Install the service
  $0 start                # Start the service
  $0 status               # Check if service is running
  $0 logs 100             # Show last 100 log lines
  $0 follow               # Watch logs live
  $0 restart              # Restart the service

Service Information:
  Name:        $SERVICE_NAME
  Port:        8675
  URL:         http://localhost:8675
  Service:     $SYSTEMD_PATH
  Startup:     $STARTUP_SCRIPT

Note: Some commands require sudo privileges and will prompt for password.
EOF
}

# Main
main() {
    check_root

    case "${1:-}" in
        install)
            test_config
            install_service
            ;;
        uninstall)
            uninstall_service
            ;;
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        rebuild)
            rebuild_service
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-50}"
            ;;
        follow)
            follow_logs
            ;;
        test)
            test_config
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: ${1:-}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
