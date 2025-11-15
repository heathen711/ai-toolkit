# AI Toolkit Installation Summary

## System Configuration
- **Platform**: Linux aarch64 (ARM64)
- **GPU**: NVIDIA GB10 (sm_121, CUDA capability 12.1)
- **Memory**: 119.7 GB unified memory
- **CUDA**: 13.0
- **Python**: 3.12

## Installed Components

### Core Framework
- **PyTorch**: 2.9.1+cu130 (CUDA 13.0 support)
- **diffusers**: 0.36.0.dev0 (from git @ 1448b03)
- **transformers**: 4.52.4
- **accelerate**: 1.11.0
- **peft**: 0.18.0

### Training & Optimization
- **torchao**: 0.10.0
- **optimum-quanto**: 0.2.4
- **bitsandbytes**: 0.48.2
- **lycoris-lora**: 1.8.3
- **prodigyopt**: 1.1.2

### Image Processing
- **albumentations**: 1.4.15
- **opencv-python**: 4.12.0.88
- **kornia**: 0.8.2
- **matplotlib**: 3.10.1

### ONNX Runtime (Custom Build)
- **onnxruntime-training**: 1.23.2+cu130
  - Built from source with CUDA 13.0 support
  - Includes CUDAExecutionProvider, ACLExecutionProvider
  - Extracted from Docker image: `aarch64-sbsa-ai-toolkit-onnxruntime`
  - Wheel saved at: `wheels/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl`

### Additional Tools
- **easy_dwpose**: 1.0.3 (installed without deps, uses onnxruntime-training)
- **gradio**: 5.49.1 (Web UI)
- **tensorboard**: 2.20.0
- **wandb**: 0.23.0
- **k-diffusion**: 0.1.1.post1

## Installation Process

### 1. Virtual Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. PyTorch with CUDA 13.0
```bash
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```

### 3. Core Dependencies
Installed via requirements.txt with version constraints to maintain CUDA 13.0 compatibility.

### 4. Custom ONNX Runtime Build
Extracted pre-built wheel from Docker image instead of building from scratch:
```bash
# Extract wheel from existing Docker image
CONTAINER_ID=$(docker create aarch64-sbsa-ai-toolkit-onnxruntime:latest)
docker cp "$CONTAINER_ID:/onnxruntime/build/Linux/Release/dist/" wheels/
docker rm "$CONTAINER_ID"

# Install
pip3 install wheels/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl
```

### 5. easy_dwpose Installation
Installed without dependencies to use our onnxruntime-training instead of onnxruntime-gpu:
```bash
pip3 install --no-deps 'git+https://github.com/jaretburkett/easy_dwpose.git'
pip3 install kornia-rs loguru  # Install missing deps manually
```

## Known Issues & Workarounds

### 1. Python 3.12 Compatibility
- **Issue**: Some packages like scipy<1.16 don't have binary wheels for Python 3.12 ARM64
- **Solution**: Constrained scipy>=1.16 to use available binary wheels

### 2. ONNX Runtime for Python 3.12
- **Issue**: onnxruntime-gpu 1.21.1 not available for Python 3.12
- **Solution**: Built onnxruntime-training 1.23.2 from source with CUDA 13.0 support

### 3. PyTorch CUDA Capability Warning
- **Warning**: "Found GPU0 NVIDIA GB10 which is of cuda capability 12.1. PyTorch supports (8.0) - (12.0)"
- **Status**: Non-critical - PyTorch still works with the GPU

### 4. Dependency Version Conflicts (Non-critical)
- `easy-dwpose` expects `onnxruntime-gpu==1.21.1` but we have `onnxruntime-training==1.23.2+cu130` (compatible)
- `easy-dwpose` expects `numpy<2.0` but we have `numpy==2.2.6` (works fine)
- `dctorch` expects `numpy<2.0` but we have `numpy==2.2.6` (works fine)

## Configuration

### .env File
Created with placeholder for HuggingFace token:
```bash
HF_TOKEN=your_huggingface_read_token_here
```

Get token from: https://huggingface.co/settings/tokens

### Recommended Training Settings for GB10 Unified Memory

Since your GB10 uses unified memory (shares RAM between CPU/GPU):

```yaml
model:
  quantize: true  # Essential for memory efficiency

train:
  gradient_checkpointing: true  # Essential for memory efficiency
  batch_size: 1  # Start small, increase if stable

  # Try low_vram: false first
  # If you get CUDA allocation errors, switch to low_vram: true
  low_vram: false
```

## Verification

All packages verified working:
```bash
✓ PyTorch 2.9.1+cu130 with CUDA 13.0
✓ GPU: NVIDIA GB10
✓ onnxruntime version: 1.23.2+cu130
  Providers: ['CUDAExecutionProvider', 'ACLExecutionProvider', 'CPUExecutionProvider']
✓ easy_dwpose imported successfully
✓ All core packages working
```

## Usage

### Activate Environment
```bash
source venv/bin/activate
```

### Run Training
```bash
python run.py config/your_config.yaml
```

### Web UI
```bash
cd ui
npm run build_and_start
# Access at http://localhost:8675
```

### Simple Gradio UI
```bash
huggingface-cli login
python flux_train_ui.py
```

## Support for Models

- ✓ FLUX.1-dev (requires HF_TOKEN)
- ✓ FLUX.1-schnell (Apache 2.0)
- ✓ SDXL
- ✓ SD 1.5
- ✓ Wan2
- ✓ OmniGen2

## Additional Resources

- **Project docs**: CLAUDE.md
- **Docker build info**: /home/jay/Documents/ABANDONED_aarch64_sbsa_ai_toolkit_docker/
- **Custom wheel**: wheels/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl

## Date
November 14, 2025
