#!/bin/bash
# Script to build onnxruntime-gpu wheel for aarch64 CUDA 13.0 using Docker

set -e

DOCKER_DIR="/home/jay/Documents/ABANDONED_aarch64_sbsa_ai_toolkit_docker/aarch64_docker"
OUTPUT_DIR="/home/jay/Documents/ai-toolkit/wheels"

echo "Building onnxruntime-gpu wheel for aarch64 CUDA 13.0..."

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build base image (Stage 1)
echo "Step 1: Building base image with Arm Compute Library..."
cd /home/jay/Documents/ABANDONED_aarch64_sbsa_ai_toolkit_docker
docker build -t aarch64-sbsa-ai-toolkit-base:latest -f "$DOCKER_DIR/Dockerfile.Stage1.base" .

# Build onnxruntime image (Stage 2)
echo "Step 2: Building onnxruntime with CUDA 13.0 support..."
docker build -t aarch64-sbsa-ai-toolkit-onnxruntime:latest -f "$DOCKER_DIR/Dockerfile.Stage2.onnxruntime" .

# Extract wheel from container
echo "Step 3: Extracting onnxruntime wheel..."
CONTAINER_ID=$(docker create aarch64-sbsa-ai-toolkit-onnxruntime:latest)
docker cp "$CONTAINER_ID:/onnxruntime/build/Linux/Release/dist/" "$OUTPUT_DIR/onnxruntime-dist"
docker rm "$CONTAINER_ID"

# Find and copy the wheel
WHEEL=$(find "$OUTPUT_DIR/onnxruntime-dist" -name "*.whl" -type f | head -n 1)
if [ -n "$WHEEL" ]; then
    cp "$WHEEL" "$OUTPUT_DIR/"
    echo "✓ Wheel extracted to: $OUTPUT_DIR/$(basename $WHEEL)"
    echo ""
    echo "Install with:"
    echo "  source venv/bin/activate"
    echo "  pip install $OUTPUT_DIR/$(basename $WHEEL)"
else
    echo "✗ No wheel found!"
    exit 1
fi

# Cleanup
rm -rf "$OUTPUT_DIR/onnxruntime-dist"

echo "Done!"
