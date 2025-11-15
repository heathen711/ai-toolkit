#!/bin/bash
# AI Toolkit Virtual Environment Setup Script
# For aarch64 (ARM64) with CUDA 13.0 and GB10/sm_121 GPU
# Generated: 2025-11-14

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
VENV_DIR="venv"
WHEELS_DIR="wheels"
PYTHON_VERSION="python3.12"
CUDA_VERSION="cu130"
DOCKER_IMAGE="aarch64-sbsa-ai-toolkit-onnxruntime:latest"

# Helper functions
print_step() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

# Check if running in the correct directory
if [ ! -f "run.py" ]; then
    print_error "Please run this script from the ai-toolkit root directory"
    exit 1
fi

# Step 1: Remove existing venv if requested
if [ -d "$VENV_DIR" ]; then
    read -p "Virtual environment already exists. Remove and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        print_error "Aborting. Remove venv manually or use a different name."
        exit 1
    fi
fi

# Step 2: Create virtual environment
print_step "Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

# Activate venv
source "$VENV_DIR/bin/activate"

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi

print_step "Virtual environment activated: $VIRTUAL_ENV"

# Step 3: Upgrade pip, setuptools, and wheel
print_step "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Step 4: Install PyTorch with CUDA 13.0
print_step "Installing PyTorch 2.9.1 with CUDA 13.0..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# Step 5: Install diffusers from git
print_step "Installing diffusers from git..."
pip install --prefer-binary 'git+https://github.com/huggingface/diffusers@1448b035859dd57bbb565239dcdd79a025a85422'

# Step 6: Install scipy (binary wheel)
print_step "Installing scipy..."
pip install 'scipy>=1.16'

# Step 7: Install PyWavelets and pytorch-wavelets
print_step "Installing PyWavelets and pytorch-wavelets..."
pip install 'PyWavelets>=1.5.0'
pip install pytorch-wavelets==1.3.0

# Step 8: Create constraints file
print_step "Creating version constraints..."
cat > /tmp/ai-toolkit-constraints.txt << 'EOF'
torch>=2.9
scipy>=1.16
numpy>=2.0,<2.3
torchvision>=0.24
EOF

# Step 9: Install core packages without dependencies
print_step "Installing core packages (no-deps)..."
pip install --no-deps \
    torchao==0.10.0 \
    transformers==4.52.4 \
    lycoris-lora==1.8.3

# Step 10: Install basic utilities
print_step "Installing basic utilities..."
pip install \
    flatten_json \
    oyaml \
    tensorboard \
    toml \
    pydantic \
    omegaconf \
    python-dotenv \
    python-slugify \
    sentencepiece

# Step 11: Install ML/AI packages (no-deps to avoid conflicts)
print_step "Installing ML/AI packages..."
pip install --constraint /tmp/ai-toolkit-constraints.txt --no-deps \
    einops \
    accelerate \
    kornia \
    invisible-watermark \
    k-diffusion \
    open_clip_torch \
    timm \
    prodigyopt \
    bitsandbytes \
    hf_transfer \
    lpips \
    pytorch_fid \
    optimum-quanto==0.2.4 \
    peft

# Step 12: Install gradio and image processing
print_step "Installing gradio and image processing packages..."
pip install --constraint /tmp/ai-toolkit-constraints.txt \
    gradio \
    opencv-python \
    matplotlib==3.10.1 \
    albumentations==1.4.15 \
    albucore==0.0.16 \
    controlnet_aux==0.0.10

# Step 13: Install missing dependencies
print_step "Installing missing dependencies..."
pip install \
    psutil \
    ninja \
    clean-fid \
    clip-anytorch \
    dctorch \
    jsonmerge \
    torchdiffeq \
    torchsde \
    wandb \
    kornia-rs \
    loguru

# Step 14: Fix version conflicts
print_step "Fixing version conflicts..."
pip install 'tokenizers>=0.21,<0.22' 'numpy>=2.0,<2.3' 'huggingface_hub<1.0'

# Step 15: Extract and install onnxruntime-training from Docker
print_step "Checking for onnxruntime-training wheel..."
mkdir -p "$WHEELS_DIR"

ONNX_WHEEL="$WHEELS_DIR/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl"

if [ -f "$ONNX_WHEEL" ]; then
    print_step "Found existing onnxruntime wheel, installing..."
    pip install "$ONNX_WHEEL"
elif docker images | grep -q "$DOCKER_IMAGE"; then
    print_step "Extracting onnxruntime wheel from Docker image..."
    CONTAINER_ID=$(docker create "$DOCKER_IMAGE")
    docker cp "$CONTAINER_ID:/onnxruntime/build/Linux/Release/dist/" "$WHEELS_DIR/onnxruntime-dist" || {
        print_warning "Failed to extract from Docker. You may need to build onnxruntime manually."
        docker rm "$CONTAINER_ID"
    }
    docker rm "$CONTAINER_ID"

    # Find and copy the wheel
    EXTRACTED_WHEEL=$(find "$WHEELS_DIR/onnxruntime-dist" -name "*.whl" -type f 2>/dev/null | head -n 1)
    if [ -n "$EXTRACTED_WHEEL" ]; then
        cp "$EXTRACTED_WHEEL" "$WHEELS_DIR/"
        rm -rf "$WHEELS_DIR/onnxruntime-dist"
        print_step "Installing onnxruntime-training..."
        pip install "$WHEELS_DIR/$(basename $EXTRACTED_WHEEL)"
    else
        print_warning "No wheel found in Docker image. Skipping onnxruntime-training."
    fi
else
    print_warning "Docker image '$DOCKER_IMAGE' not found."
    print_warning "onnxruntime-training will not be installed."
    print_warning "easy_dwpose may not work without it."
    echo ""
    echo "To build the Docker image and extract the wheel:"
    echo "  1. cd /home/jay/Documents/ABANDONED_aarch64_sbsa_ai_toolkit_docker"
    echo "  2. docker build -t aarch64-sbsa-ai-toolkit-base:latest -f aarch64_docker/Dockerfile.Stage1.base ."
    echo "  3. docker build -t aarch64-sbsa-ai-toolkit-onnxruntime:latest -f aarch64_docker/Dockerfile.Stage2.onnxruntime ."
    echo "  4. Re-run this script"
    echo ""
fi

# Step 16: Install easy_dwpose (no-deps to use our onnxruntime-training)
print_step "Installing easy_dwpose..."
pip install --no-deps 'git+https://github.com/jaretburkett/easy_dwpose.git'

# Step 17: Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_step "Creating .env file..."
    cat > .env << 'EOF'
# HuggingFace token for accessing gated models like FLUX.1-dev
# Get your token from: https://huggingface.co/settings/tokens
# You need a READ token to download gated models
HF_TOKEN=your_huggingface_read_token_here
EOF
    print_step ".env file created. Edit it to add your HuggingFace token."
else
    print_step ".env file already exists, skipping..."
fi

# Step 18: Verify installation
print_step "Verifying installation..."
python << 'PYEOF'
import sys

def test_import(module_name, display_name=None):
    display_name = display_name or module_name
    try:
        mod = __import__(module_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f"  ✓ {display_name}: {version}")
        return True
    except ImportError as e:
        print(f"  ✗ {display_name}: {e}")
        return False

print("\nCore Packages:")
all_ok = True
all_ok &= test_import('torch', 'PyTorch')
all_ok &= test_import('torchvision')
all_ok &= test_import('torchaudio')
all_ok &= test_import('diffusers')
all_ok &= test_import('transformers')
all_ok &= test_import('accelerate')
all_ok &= test_import('peft')

print("\nTraining Tools:")
all_ok &= test_import('torchao')
all_ok &= test_import('optimum.quanto', 'optimum-quanto')
all_ok &= test_import('bitsandbytes')
all_ok &= test_import('lycoris_lora', 'lycoris-lora')

print("\nImage Processing:")
all_ok &= test_import('albumentations')
all_ok &= test_import('cv2', 'opencv-python')
all_ok &= test_import('kornia')

print("\nONNX Runtime:")
all_ok &= test_import('onnxruntime')

try:
    import onnxruntime as ort
    print(f"  Providers: {ort.get_available_providers()}")
except:
    pass

print("\nOptional:")
test_import('easy_dwpose')

print("\nGPU Check:")
try:
    import torch
    print(f"  CUDA available: {torch.cuda.is_available()}")
    print(f"  CUDA version: {torch.version.cuda}")
    if torch.cuda.is_available():
        print(f"  GPU count: {torch.cuda.device_count()}")
        print(f"  GPU name: {torch.cuda.get_device_name(0)}")
except Exception as e:
    print(f"  ✗ GPU check failed: {e}")
    all_ok = False

sys.exit(0 if all_ok else 1)
PYEOF

VERIFY_EXIT=$?

# Cleanup
rm -f /tmp/ai-toolkit-constraints.txt

# Final message
echo ""
echo "============================================"
if [ $VERIFY_EXIT -eq 0 ]; then
    print_step "Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Activate the environment:"
    echo "     source venv/bin/activate"
    echo ""
    echo "  2. Edit .env and add your HuggingFace token:"
    echo "     nano .env"
    echo ""
    echo "  3. Run training:"
    echo "     python run.py config/your_config.yaml"
    echo ""
    echo "For GB10/sm_121 GPUs with unified memory, use these settings:"
    echo "  - quantize: true"
    echo "  - gradient_checkpointing: true"
    echo "  - low_vram: false (try this first)"
    echo "  - batch_size: 1"
else
    print_error "Installation completed with warnings. Check output above."
    echo ""
    echo "Some packages may have version conflicts but should still work."
    echo "Run 'pip check' to see detailed dependency conflicts."
fi
echo "============================================"
