# Virtual Environment Setup Scripts

Two scripts are provided to set up the AI Toolkit virtual environment on aarch64/ARM64 with CUDA 13.0 and GB10/sm_121 GPU support.

## Scripts Overview

### 1. `setup_venv.sh` - Full Setup (Recommended for first-time setup)

**What it does:**
- Creates a fresh virtual environment
- Installs all dependencies in the correct order
- Extracts onnxruntime-training wheel from Docker image (if available)
- Handles all version constraints and conflicts
- Creates `.env` file template
- Verifies installation with detailed checks

**When to use:**
- First-time setup
- When you have the Docker image available
- When you want a verified, complete installation

**Usage:**
```bash
cd /home/jay/Documents/ai-toolkit
./setup_venv.sh
```

**Requirements:**
- Python 3.12
- Docker (optional, for onnxruntime-training extraction)
- Internet connection
- ~10-15 minutes installation time

**Docker image:** `aarch64-sbsa-ai-toolkit-onnxruntime:latest`
- If not available, the script will warn you and skip onnxruntime-training
- To build the image, see instructions at the end of script output

---

### 2. `quick_rebuild_venv.sh` - Fast Rebuild (For quick recreation)

**What it does:**
- Quickly rebuilds venv using existing onnxruntime wheel
- Minimal output (quiet mode)
- Skips Docker extraction step
- No verification checks (assumes wheel is already available)

**When to use:**
- Rebuilding after testing/breaking your venv
- You already have the onnxruntime wheel saved
- You need a quick fresh environment
- Docker is not available

**Usage:**
```bash
cd /home/jay/Documents/ai-toolkit
./quick_rebuild_venv.sh
```

**Requirements:**
- Python 3.12
- Existing onnxruntime wheel at: `wheels/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl`
- Internet connection
- ~3-5 minutes installation time

---

## Installation Steps Explained

Both scripts follow this general flow:

1. **Create venv** - Clean Python 3.12 virtual environment
2. **Install PyTorch** - Version 2.9.1 with CUDA 13.0 from official wheels
3. **Install diffusers** - From git commit 1448b03 (latest features)
4. **Install scipy** - Version >=1.16 (has binary wheels for ARM64)
5. **Install core packages** - transformers, accelerate, peft, etc.
6. **Install utilities** - tensorboard, wandb, gradio, etc.
7. **Install ML tools** - bitsandbytes, kornia, albumentations, etc.
8. **Fix versions** - Resolve numpy/tokenizers conflicts
9. **Install onnxruntime-training** - From Docker wheel or skip
10. **Install easy_dwpose** - Uses onnxruntime-training
11. **Create .env** - Template for HuggingFace token

## Key Package Versions

| Package | Version | Notes |
|---------|---------|-------|
| PyTorch | 2.9.1+cu130 | CUDA 13.0 support |
| diffusers | 0.36.0.dev0 | From git @ 1448b03 |
| transformers | 4.52.4 | |
| scipy | >=1.16 | Binary wheels for ARM64 |
| numpy | >=2.0,<2.3 | Compatible with opencv |
| onnxruntime-training | 1.23.2+cu130 | Custom built for ARM64/CUDA 13.0 |
| albumentations | 1.4.15 | |
| gradio | 5.49.1 | |

## Troubleshooting

### Script fails with "venv already exists"
```bash
rm -rf venv
./setup_venv.sh
```

### Docker image not found
Build the Docker image first:
```bash
cd /home/jay/Documents/ABANDONED_aarch64_sbsa_ai_toolkit_docker
docker build -t aarch64-sbsa-ai-toolkit-base:latest -f aarch64_docker/Dockerfile.Stage1.base .
docker build -t aarch64-sbsa-ai-toolkit-onnxruntime:latest -f aarch64_docker/Dockerfile.Stage2.onnxruntime .
```

Or use the existing image tar:
```bash
docker load < /home/jay/Documents/ABANDONED_aarch64_sbsa_ai_toolkit_docker/aarch64-sbsa-ai-toolkit.tar
```

### onnxruntime wheel not found (quick_rebuild_venv.sh)
The wheel should be at:
```
wheels/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl
```

If missing, run `setup_venv.sh` once to extract it from Docker, or copy from backup location.

### Package version conflicts
These are normal and non-critical:
- `easy-dwpose` expects `onnxruntime-gpu` but we use `onnxruntime-training` (compatible)
- `dctorch` expects `numpy<2.0` but we have `numpy 2.2.6` (works fine)

### Installation too slow
Use `quick_rebuild_venv.sh` if you have the onnxruntime wheel already.

## Manual Installation

If scripts fail, install manually:

```bash
# Create and activate venv
python3 -m venv venv
source venv/bin/activate

# Install PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# Install from requirements (some packages may fail - that's OK)
pip install -r requirements.txt

# Install onnxruntime wheel
pip install wheels/onnxruntime_training-1.23.2+cu130-cp312-cp312-linux_aarch64.whl

# Install easy_dwpose without deps
pip install --no-deps 'git+https://github.com/jaretburkett/easy_dwpose.git'

# Fix missing deps
pip install kornia-rs loguru psutil ninja
```

## Verification

After installation, verify with:

```bash
source venv/bin/activate
python -c "
import torch
import diffusers
import transformers
print('PyTorch:', torch.__version__)
print('CUDA:', torch.version.cuda)
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')
"
```

Expected output:
```
PyTorch: 2.9.1+cu130
CUDA: 13.0
GPU: NVIDIA GB10
```

## Files Created

After running either script:

- `venv/` - Virtual environment directory
- `.env` - HuggingFace token template (if not exists)
- `wheels/` - Directory with onnxruntime wheel (setup_venv.sh only)

## Next Steps

1. **Add HuggingFace token** to `.env`:
   ```bash
   nano .env
   # Replace 'your_huggingface_read_token_here' with your actual token
   ```

2. **Activate environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Test with simple config**:
   ```bash
   python run.py config/your_config.yaml
   ```

## GB10 Unified Memory Settings

For your GB10 GPU, use these training config settings:

```yaml
model:
  quantize: true  # Essential

train:
  gradient_checkpointing: true  # Essential
  batch_size: 1  # Start small
  low_vram: false  # Try this first; switch to true if CUDA errors
```

## Support

For issues:
1. Check `INSTALLATION_SUMMARY.md` for detailed installation info
2. Check `CLAUDE.md` for project documentation
3. Run `pip check` to see dependency conflicts
4. Check logs in script output

## Related Files

- `INSTALLATION_SUMMARY.md` - Detailed installation documentation
- `CLAUDE.md` - Project overview and usage guide
- `build_onnxruntime_wheel.sh` - Build onnxruntime from Docker (advanced)
- `requirements.txt` - Original requirements (has conflicts on ARM64)
