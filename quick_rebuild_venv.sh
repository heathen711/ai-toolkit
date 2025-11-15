#!/bin/bash
# Quick AI Toolkit Virtual Environment Rebuild Script
# Uses existing onnxruntime wheel - no Docker required
# For aarch64 (ARM64) with CUDA 13.0 and GB10/sm_121 GPU

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_step() { echo -e "${GREEN}==>${NC} $1"; }
print_warning() { echo -e "${YELLOW}WARNING:${NC} $1"; }
print_error() { echo -e "${RED}ERROR:${NC} $1"; }

# Quick check
if [ ! -f "run.py" ]; then
    print_error "Run this from the ai-toolkit root directory"
    exit 1
fi

# Remove existing venv
if [ -d "venv" ]; then
    print_step "Removing existing venv..."
    rm -rf venv
fi

print_step "Creating new venv..."
python3 -m venv venv
source venv/bin/activate

print_step "Installing packages..."

# Core PyTorch with CUDA 13.0
pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# Upgrade build tools
pip install -q --upgrade pip setuptools wheel

# Install from requirements in batches to avoid dependency resolution issues
pip install -q --prefer-binary 'git+https://github.com/huggingface/diffusers@1448b035859dd57bbb565239dcdd79a025a85422'
pip install -q 'scipy>=1.16' 'PyWavelets>=1.5.0' pytorch-wavelets==1.3.0

# Core packages (no-deps to preserve torch version)
pip install -q --no-deps torchao==0.10.0 transformers==4.52.4 lycoris-lora==1.8.3

# Utilities
pip install -q flatten_json oyaml tensorboard toml pydantic omegaconf python-dotenv python-slugify sentencepiece

# ML packages (no-deps)
pip install -q --no-deps einops accelerate kornia invisible-watermark k-diffusion open_clip_torch timm prodigyopt bitsandbytes hf_transfer lpips pytorch_fid optimum-quanto==0.2.4 peft

# Image processing
pip install -q gradio opencv-python matplotlib==3.10.1 albumentations==1.4.15 albucore==0.0.16 controlnet_aux==0.0.10

# Missing dependencies
pip install -q psutil ninja clean-fid clip-anytorch dctorch jsonmerge torchdiffeq torchsde wandb kornia-rs loguru

# Fix versions
pip install -q 'tokenizers>=0.21,<0.22' 'numpy>=2.0,<2.3' 'huggingface_hub<1.0'

# ONNX Runtime (use existing wheel if available)
if [ -f "wheels/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl" ]; then
    print_step "Installing onnxruntime from local wheel..."
    pip install -q wheels/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl
    pip install -q --no-deps 'git+https://github.com/jaretburkett/easy_dwpose.git'
else
    print_warning "onnxruntime wheel not found at wheels/onnxruntime_training-*.whl"
    print_warning "Skipping onnxruntime and easy_dwpose"
fi

# Create .env if needed
[ ! -f ".env" ] && echo "HF_TOKEN=your_huggingface_read_token_here" > .env

print_step "Quick verification..."
python -c "import torch; print(f'PyTorch {torch.__version__} CUDA {torch.version.cuda} - GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

echo ""
print_step "Done! Activate with: source venv/bin/activate"
