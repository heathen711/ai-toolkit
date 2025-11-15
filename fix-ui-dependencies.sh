#!/bin/bash
# Fix corrupted npm dependencies in UI directory

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() { echo -e "${GREEN}==>${NC} $1"; }
print_warning() { echo -e "${YELLOW}WARNING:${NC} $1"; }

cd "$(dirname "$0")/ui"

print_step "Checking UI dependencies..."

# Check if node_modules/.bin exists
if [ ! -d "node_modules/.bin" ]; then
    print_warning "node_modules is corrupted (missing .bin directory)"
    print_step "Removing corrupted node_modules..."
    rm -rf node_modules

    print_step "Running fresh npm install..."
    npm install

    print_step "Dependencies fixed!"
else
    print_step "Dependencies look good!"
fi

# Verify tsc exists
if [ -f "node_modules/.bin/tsc" ]; then
    print_step "TypeScript compiler found ✓"
else
    print_warning "TypeScript compiler not found, reinstalling..."
    rm -rf node_modules
    npm install
fi

# Verify next exists
if [ -f "node_modules/.bin/next" ]; then
    print_step "Next.js found ✓"
else
    print_warning "Next.js not found, reinstalling..."
    rm -rf node_modules
    npm install
fi

echo ""
print_step "All dependencies verified!"
echo ""
echo "Now restart the service:"
echo "  cd .. && ./manage-webui-service.sh restart"
