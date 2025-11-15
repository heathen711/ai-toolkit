# Dataloader Worker Memory Usage Guide

## The Problem: Each Worker Uses Massive Memory

When training with multiple dataloader workers (e.g., `num_workers: 2`), you may observe extremely high memory usage per worker:

**Typical scenario:**
- Main process: 19GB
- Worker 1: 42GB
- Worker 2: 42GB
- **Total: 103GB** (for just 2 workers!)

This is **not a bug** - it's how PyTorch's multiprocessing dataloader works, combined with how the AI Toolkit caches data.

## Root Cause: Dataset Pickling

When PyTorch creates dataloader workers with `num_workers > 0`, it:

1. **Pickles the entire dataset object** (serializes it to bytes)
2. **Sends it to each worker process** via inter-process communication
3. **Each worker unpickles** and gets its own complete copy

### What Gets Copied to Each Worker

The `AiToolkitDataset` object contains:

**1. Model Reference (`self.sd`)**
- Line 406 in `toolkit/data_loader.py`: `self.sd = sd`
- This is a reference to the **entire StableDiffusion model**
- Includes: transformer/UNet weights, VAE, text encoders, vision encoders
- For Qwen-Image: ~19GB of model weights

**2. Cached Latents (if `cache_latents: true`)**
- Each `FileItemDTO` in `self.file_list` stores `_encoded_latent`
- For 100 images at 1024x1024 with FLUX/Qwen:
  - Latent shape: ~128x128x16 channels (1/8 resolution, 16 channels)
  - Per latent: ~4-8MB (depending on dtype)
  - Total: ~400-800MB for 100 images

**3. Cached Text Embeddings (if `cache_text_embeddings: true`)**
- Each `FileItemDTO` stores `prompt_embeds` (PromptEmbeds object)
- T5-XXL embeddings for FLUX: 256 tokens × 4096 dims × 2 bytes = ~2MB per prompt
- For 100 images: ~200MB

**4. Other Cached Data**
- CLIP vision embeddings
- Control images/latents
- Augmentation transforms
- Dataset configuration

### Memory Calculation Example

For **Qwen-Image with 2 workers, 100 training images:**

| Component | Main Process | Worker 1 | Worker 2 |
|-----------|-------------|----------|----------|
| Model weights | 19GB | 19GB | 19GB |
| Cached latents (100 imgs) | 800MB | 800MB | 800MB |
| Text embeddings (100 prompts) | 200MB | 200MB | 200MB |
| Control images (if used) | 500MB | 500MB | 500MB |
| CLIP embeddings (if used) | 200MB | 200MB | 200MB |
| Python overhead | 500MB | 500MB | 500MB |
| **Total** | **~21GB** | **~21GB** | **~21GB** |

**With additional training overhead:**
- Main process: ~19GB (model) + gradients/optimizer states
- Each worker: ~42GB (full copy of everything)
- **Total: 19 + 42 + 42 = 103GB**

## Solutions

### Solution 1: Disable Workers (Simplest)

**Best for: Small datasets, systems with limited RAM**

```yaml
train:
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 0  # ← Disable multiprocessing
      cache_latents_to_disk: true
```

**Pros:**
- Minimal memory usage (only main process)
- No worker memory duplication
- Simpler debugging

**Cons:**
- Slower data loading (single-threaded)
- CPU may become bottleneck during I/O
- Training may wait for data preparation

**When to use:**
- Dataset < 500 images
- System RAM < 64GB
- Already using `cache_latents_to_disk: true`

### Solution 2: Use Disk Caching (Recommended)

**Best for: Large datasets, when you have fast SSD**

```yaml
train:
  datasets:
    - folder_path: "/path/to/dataset"
      cache_latents_to_disk: true  # ← Cache to disk, not RAM
      cache_text_embeddings_to_disk: true  # ← Also cache text to disk
      num_workers: 2  # Can use workers safely now

      # Optional: Use fastsafetensors for faster loading
      use_fastsafetensors_cache: true
      use_gpu_direct_cache: true  # If GDS available
```

**How it works:**
- Latents computed once and saved to `_latent_cache/` folder
- Text embeddings saved to `_t_e_cache/` folder
- Workers load from disk on-demand instead of keeping in RAM
- Model reference still copied but no large cached data

**Memory with disk caching:**
- Main process: 19GB
- Worker 1: ~20GB (model + minimal overhead)
- Worker 2: ~20GB (model + minimal overhead)
- **Total: ~59GB** (44GB savings!)

**Pros:**
- Significantly lower memory usage
- Fast loading with fastsafetensors (4-5x faster than standard)
- Cache persists between training runs
- Can use multiple workers safely

**Cons:**
- Requires disk space (latents + embeddings)
- First epoch slower (building cache)
- Requires fast SSD for best performance

### Solution 3: Reduce Workers

**Best for: Medium datasets, moderate RAM**

```yaml
train:
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 1  # ← Reduce from 2 to 1
      cache_latents_to_disk: true
```

**Memory reduction:**
- 2 workers: 19 + 42 + 42 = 103GB
- 1 worker: 19 + 42 = 61GB
- **Savings: 42GB**

**Trade-off:**
- Lower memory but still decent parallelism
- One worker can prepare next batch while GPU trains

### Solution 4: Disable In-Memory Caching

**Best for: When you must use workers but have limited RAM**

```yaml
train:
  datasets:
    - folder_path: "/path/to/dataset"
      cache_latents: false  # ← Don't cache in RAM
      cache_latents_to_disk: true  # ← Use disk instead
      cache_text_embeddings: false
      cache_text_embeddings_to_disk: true
      num_workers: 2
```

This is similar to Solution 2 but explicitly disables in-memory caching.

### Solution 5: Advanced - Persistent Workers (PyTorch 1.7+)

**Best for: Long training runs, want to amortize worker startup cost**

```yaml
train:
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 2
      persistent_workers: true  # ← Keep workers alive between epochs
      cache_latents_to_disk: true
```

**Note:** This setting is not yet exposed in AI Toolkit config but could be added.

**Pros:**
- Workers don't restart between epochs
- Faster epoch transitions
- Memory allocated once and reused

**Cons:**
- Memory stays allocated for entire training session
- Slightly more complex cleanup

## Prefetch Factor Impact

The `prefetch_factor` setting controls how many batches each worker prepares in advance:

```yaml
train:
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 2
      prefetch_factor: 2  # Each worker prefetches 2 batches
```

**Memory impact:**
- Each prefetched batch holds images/latents in memory
- `prefetch_factor: 2` with `batch_size: 4` means:
  - Each worker holds 2 × 4 = 8 images in prefetch queue
  - For 1024×1024 images: 8 × 6MB = ~48MB per worker

**Recommendations:**
- Default `prefetch_factor: 2` is usually good
- Increase to 4-6 if you have fast GPU and slow storage
- Decrease to 1 if memory constrained

## Recommended Configurations

### Small Dataset (<500 images), Limited RAM (<64GB)

```yaml
train:
  batch_size: 1
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 0  # No workers
      cache_latents_to_disk: true
      use_fastsafetensors_cache: true  # Fast disk loading
```

### Medium Dataset (500-2000 images), Moderate RAM (64-128GB)

```yaml
train:
  batch_size: 1
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 1  # Single worker
      prefetch_factor: 2
      cache_latents_to_disk: true
      cache_text_embeddings_to_disk: true
      use_fastsafetensors_cache: true
```

### Large Dataset (>2000 images), Plenty of RAM (>128GB)

```yaml
train:
  batch_size: 1
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 2  # Multiple workers OK
      prefetch_factor: 2
      cache_latents_to_disk: true
      cache_text_embeddings_to_disk: true
      use_fastsafetensors_cache: true
      use_gpu_direct_cache: true  # If GDS available
```

### Unified Memory GPU (GB10/DGX Spark) - Unlimited RAM

```yaml
train:
  batch_size: 1
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 2  # Can use workers freely
      prefetch_factor: 3  # Higher prefetch OK with unlimited RAM
      cache_latents_to_disk: true
      cache_text_embeddings_to_disk: true
      use_fastsafetensors_cache: true
```

## Diagnostic Commands

### Check Current Memory Usage

```bash
# Overall system memory
free -h

# Per-process memory
ps aux | grep python | awk '{print $2, $6/1024, "MB", $11}'

# Detailed memory breakdown
sudo python -c "
from toolkit.device_utils import print_device_info
print_device_info()
"
```

### Monitor Memory During Training

```bash
# Watch memory usage in real-time
watch -n 2 'ps aux | grep python | awk "{print \$2, \$6/1024, \"MB\", \$11}"'

# Or use htop with tree view
htop -t  # Press F5 for tree view
```

### Check Dataloader Configuration

```bash
# Verify your config
cat config/your_config.yaml | grep -A 10 "datasets:"
```

## Technical Details: Why This Happens

### PyTorch Multiprocessing Dataloader Architecture

```
Main Process (Training Loop)
    │
    ├─> Worker 1 Process (fork/spawn)
    │   └─> Full copy of Dataset object via pickle
    │       ├─> self.sd (StableDiffusion model)
    │       ├─> self.file_list (all FileItemDTO objects)
    │       └─> All cached data in memory
    │
    └─> Worker 2 Process (fork/spawn)
        └─> Full copy of Dataset object via pickle
            ├─> self.sd (StableDiffusion model)
            ├─> self.file_list (all FileItemDTO objects)
            └─> All cached data in memory
```

### Why Model Gets Copied

The `AiToolkitDataset.__init__()` stores the model:

```python
# toolkit/data_loader.py:406
self.sd = sd  # Full StableDiffusion object with all weights!
```

When each worker is created:
1. Python pickles the dataset: `pickle.dumps(dataset)`
2. Includes `self.sd` and all its weights
3. Each worker gets a complete copy

### Why Cached Data Gets Copied

With `cache_latents: true`:

```python
# toolkit/dataloader_mixins.py:1803
file_item._encoded_latent = latent.to('cpu', dtype=self.sd.torch_dtype)
```

This stores latents in the FileItemDTO object, which is part of `self.file_list`, which gets pickled and sent to each worker.

### Disk Caching Avoids This

With `cache_latents_to_disk: true`:

```python
# toolkit/dataloader_mixins.py:1696
if not self.is_caching_to_memory:
    self._encoded_latent = None  # Don't keep in memory!
```

Workers load from disk on-demand:

```python
# toolkit/dataloader_mixins.py:1704-1716
if self._encoded_latent is None:
    # Load from disk using fastsafetensors
    state_dict = load_file_fast(latent_path, device='cpu', config=fast_config)
    self._encoded_latent = state_dict['latent']
```

## Future Optimizations

Potential improvements to reduce memory usage:

### 1. Lazy Model Loading in Workers

Instead of pickling the model, workers could load it separately:

```python
class AiToolkitDataset:
    def __init__(self, sd=None):
        # Store model config instead of model
        self.model_config = sd.model_config if sd else None
        self.sd = None  # Don't store model

    def _ensure_model_loaded(self):
        if self.sd is None and in_worker_process():
            # Load model in worker on first access
            self.sd = load_model_from_config(self.model_config)
```

**Savings:** ~19GB per worker for Qwen-Image

### 2. Shared Memory for Cached Data

Use PyTorch's shared memory for cached latents:

```python
# Store latents in shared memory accessible to all workers
shared_latent_cache = torch.multiprocessing.Manager().dict()
```

**Complexity:** High (requires significant refactoring)

### 3. Memory-Mapped Tensor Storage

Use `mmap` for cached latents stored on disk:

```python
# Instead of loading full tensor, map it from disk
latent = torch.from_file(latent_path, shared=True, size=tensor_size)
```

**Savings:** Near-zero memory per worker for cached data

## Summary

**Key takeaway:** Use `cache_latents_to_disk: true` and `cache_text_embeddings_to_disk: true` instead of in-memory caching to enable multiple workers without massive memory duplication.

**Quick fix for your config:**
```yaml
train:
  datasets:
    - folder_path: "/path/to/dataset"
      num_workers: 2
      cache_latents_to_disk: true  # ← Add this
      cache_text_embeddings_to_disk: true  # ← Add this
      use_fastsafetensors_cache: true  # ← Fast disk loading
```

This should reduce worker memory from ~42GB each to ~20GB each, saving ~44GB total.
