# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Toolkit by Ostris is a Python-based training framework for diffusion models (FLUX.1, SDXL, SD 1.5, Wan2, OmniGen2, etc.) optimized for consumer-grade hardware (24GB+ NVIDIA GPUs). It supports LoRA/LoKr adapter training with both CLI and web UI interfaces.

Version: 0.7.4

## Common Commands

### Initial Setup

```bash
# Linux
python3 -m venv venv
source venv/bin/activate
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
pip3 install -r requirements.txt

# Windows
python -m venv venv
.\venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the root directory:
```
HF_TOKEN=your_huggingface_read_token_here
```

Required for gated models like FLUX.1-dev. Get token from: https://huggingface.co/settings/tokens

### Training Commands

```bash
# Run training job from config file
python run.py config/your_config.yaml

# Run multiple configs sequentially
python run.py config/config1.yaml config/config2.yaml

# Continue running jobs even if one fails
python run.py -r config/config1.yaml config/config2.yaml

# Replace [name] tag in config with custom name
python run.py -n my_custom_name config/config.yaml

# Log output to file
python run.py -l output.log config/config.yaml
```

### Web UI Commands

```bash
cd ui
npm run build_and_start  # Installs dependencies, builds, and starts UI on port 8675

# With authentication token (for remote/cloud deployments)
AI_TOOLKIT_AUTH=super_secure_password npm run build_and_start  # Linux
set AI_TOOLKIT_AUTH=super_secure_password && npm run build_and_start  # Windows
$env:AI_TOOLKIT_AUTH="super_secure_password"; npm run build_and_start  # PowerShell
```

Access UI at: `http://localhost:8675`

### Simple Gradio UI

```bash
huggingface-cli login  # Provide write token to publish LoRA
python flux_train_ui.py
```

### Cloud Training (Modal)

```bash
pip install modal
modal setup  # Authenticate
modal run run_modal.py --config-file-list-str=/root/ai-toolkit/config/your_config.yml
```

### Testing & Development

No formal test infrastructure exists. Testing is manual using scripts in `/testing/`.

```bash
# Debug mode - enables torch anomaly detection
DEBUG_TOOLKIT=1 python run.py config/your_config.yaml
```

## Architecture Overview

### Job-Process Pattern

The codebase uses a command pattern with clear separation:

- **Jobs** (`/jobs/`) - Orchestration layer (TrainJob, ExtractJob, GenerateJob, ModJob, ExtensionJob)
- **Processes** (`/jobs/process/`) - Execution layer (TrainVAEProcess, TrainSliderProcess, etc.)
- **Factory** (`toolkit/job.py`) - `get_job()` dynamically creates jobs from config

Flow: Config → `get_job()` → Job → Process → Extension

### Extension System

Plugins are auto-discovered from two locations:
- `/extensions_built_in/` - Built-in extensions (sd_trainer, diffusion_models, etc.)
- `/extensions/` - User custom extensions (gitignored)

Each extension:
1. Registers via `AI_TOOLKIT_EXTENSIONS` list in `__init__.py`
2. Inherits from `Extension` base class
3. Implements `get_process()` method returning process dict
4. Maps process types to implementations

Example structure:
```python
class MyExtension(Extension):
    def get_process(self):
        return {
            'my_process_type': MyProcess
        }
```

### Core Module Responsibilities

- **toolkit/stable_diffusion_model.py** (3,144 lines) - `StableDiffusion` class wraps diffusers operations
- **toolkit/dataloader_mixins.py** (2,151 lines) - Composable data loading with mixins (CaptionMixin, BucketsMixin, LatentCachingMixin)
- **toolkit/config_modules.py** (1,333 lines) - Typed configuration objects and validation
- **jobs/process/BaseSDTrainProcess.py** - Base training loop for Stable Diffusion models
- **extensions_built_in/sd_trainer/SDTrainer.py** - Concrete trainer handling FLUX, SDXL, SD 1.5

### Mixin Pattern for Data Loading

The dataloader uses mixins for composable functionality:
- `CaptionMixin` - Caption handling and dropout
- `BucketsMixin` - Resolution bucketing for batch efficiency
- `LatentCachingMixin` - Cache latents to disk to save VRAM/compute
- `AugmentationMixin` - Image augmentations (albumentations)

These compose to create flexible data pipelines for different training scenarios.

### Configuration System

Configs use YAML/JSON with special features:

```yaml
job: extension
config:
  name: "model_name"  # [name] tag can be replaced via CLI -n flag
  process:
    - type: 'sd_trainer'
      model:
        name_or_path: "${MODEL_PATH}"  # Environment variable substitution
```

- **Environment variables**: `${VAR_NAME}` syntax
- **Tag replacement**: `[name]` replaced with CLI `-n` argument or config name
- **Trigger word**: `[trigger]` in captions replaced with `trigger_word` from config

### UI Architecture (Next.js)

The web UI (`/ui/`) is a full-stack Next.js application:

- **Frontend**: React 19, TypeScript, Tailwind CSS
- **Database**: Prisma ORM with SQLite (schema in `ui/prisma/schema.prisma`)
  - Tables: Settings, Queue, Job
- **Background Worker**: Built-in worker process for job execution
- **API**: Next.js API routes handle job management
- **Port**: 8675

The UI runs independently of training jobs - you can close it and jobs continue.

## Training Configuration Patterns

### Layer-Specific Training

Use `only_if_contains` to target specific layers:

```yaml
network:
  type: "lora"
  linear: 128
  linear_alpha: 128
  network_kwargs:
    only_if_contains:
      - "transformer.single_transformer_blocks.7.proj_out"
```

Exclude layers with `ignore_if_contains`:

```yaml
network:
  type: "lora"
  linear: 128
  linear_alpha: 128
  network_kwargs:
    ignore_if_contains:
      - "transformer.single_transformer_blocks."
```

Note: `ignore_if_contains` takes priority over `only_if_contains`.

### Network Types

- **LoRA**: Standard low-rank adaptation
- **LoKr**: Kronecker product factorization (see LyCORIS docs)

```yaml
network:
  type: "lokr"
  lokr_full_rank: true
  lokr_factor: 8
```

### FLUX.1 Models

**FLUX.1-dev** (non-commercial, gated):
- Requires HF_TOKEN and license acceptance at https://huggingface.co/black-forest-labs/FLUX.1-dev
- Best quality but non-commercial license

**FLUX.1-schnell** (Apache 2.0):
- Requires training adapter: `ostris/FLUX.1-schnell-training-adapter`
- Commercial-friendly but lower quality

```yaml
model:
  name_or_path: "black-forest-labs/FLUX.1-schnell"
  assistant_lora_path: "ostris/FLUX.1-schnell-training-adapter"
  is_flux: true
  quantize: true
sample:
  guidance_scale: 1  # schnell doesn't use guidance
  sample_steps: 4
```

## Dataset Requirements

Datasets are folders with images and matching text files:
- **Formats**: jpg, jpeg, png (webp has issues)
- **Captions**: Same filename with `.txt` extension (e.g., `image2.jpg` + `image2.txt`)
- **No preprocessing needed**: Loader handles resizing, cropping, and bucketing
- **Resolution handling**: Images are never upscaled, only downscaled and bucketed

Caption features:
- `[trigger]` in caption files replaced with config's `trigger_word`
- `caption_dropout_rate` randomly drops captions during training
- `shuffle_tokens` shuffles comma-separated tokens

## Important Conventions

### Git Operations

Training creates checkpoints frequently - add to `.gitignore`:
- `/output/` - Training outputs (already ignored)
- `/datasets/` - Training data (already ignored)
- `/models/` - Downloaded models (already ignored)
- `.env` - Contains HF_TOKEN (already ignored)

### Memory Management

For 24GB VRAM:
- Set `quantize: true` in model config (runs 8-bit mixed precision)
- Set `gradient_checkpointing: true` in train config
- Set `low_vram: true` if GPU drives monitors (slower but uses less VRAM)
- Use `cache_latents_to_disk: true` to avoid recomputing latents

**Unified Memory GPUs** (sm_121/GB10, DGX Spark, etc.):

These GPUs use system RAM instead of dedicated VRAM and report 0 VRAM to PyTorch.

Since unified memory uses the same physical RAM for both CPU and GPU, the `low_vram` setting only changes how PyTorch tracks memory allocations, not where data physically resides.

**Important NVIDIA findings** (DGX Spark documentation):
- `nvidia-smi` shows "Memory-Usage: Not Supported" for unified memory GPUs (expected behavior)
- `cudaMemGetInfo` underreports available memory (doesn't account for swap)
- Toolkit uses `/proc/meminfo` for accurate memory reporting on Linux

**Recommended approach** (test to find what works):
1. **Try `low_vram: false` first** - unified memory may work fine with standard settings
2. If you get CUDA allocation errors, try `low_vram: true` to work around PyTorch allocator issues
3. Set `quantize: true` for better memory efficiency
4. Set `gradient_checkpointing: true`
5. Start with `batch_size: 1` and increase if stable

**Debugging memory issues:**
```bash
# Check device info (shows accurate memory from /proc/meminfo)
python -c "from toolkit.device_utils import print_device_info; print_device_info()"

# If experiencing memory issues, flush system caches (requires sudo)
sudo python -c "from toolkit.device_utils import flush_system_caches; flush_system_caches()"
# Or manually: sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
```

**Note**: The `low_vram: true` setting was designed for GPUs with limited dedicated VRAM. For unified memory, any benefit comes from working around potential bugs in PyTorch's CUDA memory allocator when `total_memory=0`, not from actual memory movement.

### Checkpoint Recovery

Training saves checkpoints every N steps. If interrupted:
- Resume automatically by running same config again
- **NEVER ctrl+c while saving** - will corrupt checkpoint
- Set `max_step_saves_to_keep` to limit disk usage

### Naming Conventions

Layer names use diffusers format (not original model format):
- Check state dict to find exact layer names
- Example: `transformer.single_transformer_blocks.7.proj_out`

## Docker Deployment

```bash
docker-compose up
```

Configured mounts (see `docker-compose.yml`):
- Datasets
- Output folder
- Config folder
- HuggingFace cache

Requires nvidia-docker for GPU passthrough.

## Key Dependencies

- **PyTorch**: Latest version with CUDA 13.0
- **diffusers**: From git (latest features)
- **transformers**: 4.52.4
- **accelerate**: Multi-GPU training
- **lycoris-lora**: 1.8.3 for LoKr support
- **bitsandbytes**: 8-bit optimizers
- **gradio**: Simple UI
- **tensorboard/wandb**: Training monitoring

## File Path Conventions

Configs support multiple path resolution strategies:
1. Full path: `/absolute/path/to/config.yaml`
2. Config folder: `config_name` → looks in `/config/` for `config_name.yaml` or `config_name.json`
3. Relative path: `./relative/path/config.yaml`

Within configs, use absolute paths or environment variables:
```yaml
folder_path: "${DATASET_PATH}/my_dataset"
# or
folder_path: "/full/path/to/dataset"
```

## Troubleshooting Context

- **Windows WSL**: Known to work, native Windows has reported issues
- **Monitor attached to training GPU**: Set `low_vram: true`
- **Unified Memory GPUs** (sm_121/GB10): These GPUs report 0 VRAM. Try `low_vram: false` first; use `true` if you get allocation errors
- **Schnell training**: Highly experimental, dev recommended for quality
- **No tests failing**: Project has no formal test suite - validation is manual

## Extension Development

To create custom extensions:

1. Create folder in `/extensions/`
2. Create `__init__.py` with Extension subclass
3. Register in `AI_TOOLKIT_EXTENSIONS` list
4. Implement `get_process()` returning process dict
5. Create process class inheriting from BaseProcess or BaseSDTrainProcess

Example extensions in `/extensions_built_in/`:
- `sd_trainer` - Main training implementation
- `diffusion_models/` - Model-specific adapters (FLUX, Wan2, etc.)
- `ultimate_slider_trainer` - Concept slider training
- `dataset_tools` - Dataset utilities
- save all docs within the docs folder