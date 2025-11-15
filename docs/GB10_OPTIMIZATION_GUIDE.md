# GB10 Training Configuration Optimization Guide

## System Configuration
- **GPU:** NVIDIA GB10 (sm_121, CUDA capability 12.1)
- **Memory:** 119.7 GB unified memory (shares system RAM)
- **Architecture:** Unified memory (not dedicated VRAM)
- **CUDA:** 13.0

## Model Details
- **Model:** Wan2.2-T2V-A14B (14 billion parameter text-to-video model)
- **Training Type:** LoRA fine-tuning
- **Purpose:** Training custom character/style

---

## Configuration Files Comparison

### 1. Original Config (`config.yml`)
**Purpose:** Original training configuration
**Profile:** Conservative, safe settings

| Setting | Value | Notes |
|---------|-------|-------|
| batch_size | 1 | Safe for large models |
| gradient_accumulation | 4 | Effective batch = 4 |
| low_vram | true | For limited VRAM GPUs |
| quantize | true (qfloat8) | Memory efficient |
| gradient_checkpointing | true | Essential |
| cache_text_embeddings | false | Recomputes each time |
| cache_latents_to_disk | true | Good |

**Pros:**
- Very safe, won't run out of memory
- Known to work on limited hardware

**Cons:**
- Not optimized for GB10's large unified memory
- `low_vram: true` may slow training unnecessarily on unified memory

---

### 2. GB10 Optimized Config (`config-gb10-optimized.yml`)
**Purpose:** Recommended configuration for GB10
**Profile:** Balanced optimization for unified memory

| Setting | Value | Change | Reason |
|---------|-------|--------|--------|
| batch_size | 1 | Same | Safe for 14B model stability |
| gradient_accumulation | 8 | +4 | Smoother gradients with available memory |
| low_vram | **false** | ✓ | GB10 unified memory - try without first |
| num_workers | **0** | ✓ | Load in main process - no worker overhead |
| quantize | true (qfloat8) | Same | Still essential for efficiency |
| gradient_checkpointing | true | Same | Still essential |
| cache_text_embeddings | false | Same | Conservative |
| cache_latents_to_disk | true | Same | Good practice |

**Key Optimization:**
```yaml
low_vram: false  # Try this first for GB10
```

**Effective Batch Size:** 1 × 8 = 8

**Expected Benefits:**
- **~10-20% faster training** - Less memory management overhead
- **Better gradient quality** - Higher accumulation steps
- **More stable training** - Better gradient averaging

**Recommended for:**
- First training runs on GB10
- Production training
- Users wanting safe but optimized performance

---

### 3. GB10 Experimental Config (`config-gb10-experimental.yml`)
**Purpose:** Push GB10 to higher performance
**Profile:** Aggressive optimization - requires monitoring

| Setting | Value | Change | Reason |
|---------|-------|--------|--------|
| batch_size | **2** | +1 | Test with 119.7 GB available |
| gradient_accumulation | 4 | -4 | Keep effective batch at 8 |
| low_vram | false | ✓ | Unified memory optimization |
| num_workers | **0** | ✓ | Load in main process - no worker overhead |
| quantize | true (qfloat8) | Same | Essential |
| gradient_checkpointing | true | Same | Essential |
| cache_text_embeddings | **true** | ✓ | Save compute, use memory |
| cache_latents_to_disk | true | Same | Good practice |

**Key Optimizations:**
```yaml
batch_size: 2              # Double the batch size
gradient_accumulation: 4   # Keep effective batch = 8
cache_text_embeddings: true # Trade memory for speed
low_vram: false
```

**Effective Batch Size:** 2 × 4 = 8 (same total, but computed differently)

**Expected Benefits:**
- **~30-50% faster training** - Batch processing efficiency
- **Better GPU utilization** - More parallel work
- **Cached embeddings** - Don't recompute text encodings

**Risks:**
- May cause CUDA out of memory errors
- Requires monitoring during first run
- If it fails, fall back to optimized config

**Recommended for:**
- Experienced users
- After successful run with optimized config
- When you need faster iteration

---

## Optimization Rationale

### Why `low_vram: false` for GB10?

From the CLAUDE.md documentation:

> **Unified Memory GPUs** (sm_121/GB10, DGX Spark, etc.):
> These GPUs use system RAM instead of dedicated VRAM and report 0 VRAM to PyTorch.
>
> **Recommended approach** (test to find what works):
> 1. **Try `low_vram: false` first** - unified memory may work fine with standard settings
> 2. If you get CUDA allocation errors, try `low_vram: true`

**Why this matters:**
- `low_vram: true` moves data to CPU when not in use
- With unified memory, CPU and GPU share the same RAM
- This creates unnecessary overhead
- `low_vram: false` lets PyTorch manage memory naturally

**Test approach:**
1. Start with `low_vram: false` (optimized config)
2. Monitor first 50 steps closely
3. If CUDA allocation errors occur, switch to `low_vram: true`

### Why `num_workers: 0` for unified memory?

**Worker processes** normally pre-load batches in separate processes to hide I/O latency.

**With unified memory:**
- No benefit from separate worker processes
- Workers create duplicate data in memory (each worker loads a copy)
- Inter-process communication overhead
- More complex memory management

**Benefits of `num_workers: 0`:**
- Simpler memory management - everything in main process
- No duplicate data across workers
- No IPC overhead
- With `cache_latents_to_disk: true`, data loading is already fast

**Note:** This is similar to Windows, which forces `num_workers: 0` automatically.

### Why increase gradient_accumulation?

With 119.7 GB of unified memory, you have room for larger gradient buffers.

**Benefits:**
- More stable training
- Better gradient estimates
- Reduces variance in updates

**Math:**
- Original: batch_size 1 × accumulation 4 = effective batch 4
- Optimized: batch_size 1 × accumulation 8 = effective batch 8
- Experimental: batch_size 2 × accumulation 4 = effective batch 8

### Why cache_text_embeddings in experimental?

**Memory vs Speed trade-off:**
- **Without caching:** Recomputes text embeddings every step (slower, less memory)
- **With caching:** Stores embeddings in memory (faster, more memory)

**With 119.7 GB available:**
- Text embeddings are relatively small (~few GB)
- Worth trading memory for speed

---

## Recommended Testing Workflow

### Step 1: Start with Optimized Config
```bash
cd /home/jay/Documents/ai-toolkit
source venv/bin/activate

# Run with optimized config
python run.py config/rebecka_config-gb10-optimized.yml
```

**Watch for:**
- First 50 steps complete without errors
- Memory usage stays under 100 GB
- Training speed (steps/sec)

### Step 2: Monitor Performance
```bash
# Watch NVIDIA SMI
watch -n 1 nvidia-smi

# Or use the device utilities
python -c "from toolkit.device_utils import print_device_info; print_device_info()"
```

### Step 3: If Successful, Try Experimental
```bash
# After optimized config works well
python run.py config/rebecka_config-gb10-experimental.yml
```

**Watch for:**
- CUDA allocation errors in first 10 steps
- If errors occur, fall back to optimized config
- Note the training speed difference

### Step 4: If CUDA Errors Occur

Edit the config to add:
```yaml
model:
  low_vram: true  # Switch back if needed
```

Or use the original config with just quantization:
```bash
python run.py datasets/rebecka/config.yml
```

---

## Expected Performance

### Original Config
- **Steps/sec:** ~0.5-1.0 (baseline)
- **Memory:** ~60-80 GB peak
- **Training time (2000 steps):** ~40-60 minutes

### Optimized Config
- **Steps/sec:** ~0.6-1.2 (10-20% faster)
- **Memory:** ~70-90 GB peak
- **Training time (2000 steps):** ~30-45 minutes

### Experimental Config
- **Steps/sec:** ~0.8-1.5 (30-50% faster)
- **Memory:** ~80-110 GB peak
- **Training time (2000 steps):** ~20-35 minutes

*Note: Actual performance depends on CPU, disk speed, and dataset size*

---

## Troubleshooting

### CUDA Out of Memory Error

**Solution 1:** Switch to `low_vram: true`
```yaml
model:
  low_vram: true
```

**Solution 2:** Reduce batch_size
```yaml
train:
  batch_size: 1
```

**Solution 3:** Reduce gradient_accumulation
```yaml
train:
  gradient_accumulation: 4
```

**Solution 4:** Use original config
```bash
python run.py datasets/rebecka/config.yml
```

### Training Very Slow

**Check:**
1. Is `cache_latents_to_disk: true`? (Should be)
2. Is disk I/O slow? (Check with `iostat`)
3. Is quantization enabled? (Should be)
4. Try experimental config with `batch_size: 2`

### Memory Warnings from PyTorch

This is normal for unified memory GPUs:
```
Found GPU0 NVIDIA GB10 which is of cuda capability 12.1.
PyTorch supports (8.0) - (12.0)
```

This warning is non-critical - PyTorch still works fine.

### System Caches Need Flush

If memory issues persist:
```bash
# Flush system caches (requires sudo)
sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'

# Or use the utility
sudo python -c "from toolkit.device_utils import flush_system_caches; flush_system_caches()"
```

---

## Configuration Summary Table

| Metric | Original | Optimized | Experimental |
|--------|----------|-----------|--------------|
| **Batch Size** | 1 | 1 | 2 |
| **Gradient Accum** | 4 | 8 | 4 |
| **Effective Batch** | 4 | 8 | 8 |
| **low_vram** | true | false | false |
| **num_workers** | 2 (default) | 0 | 0 |
| **Cache Embeddings** | false | false | true |
| **Expected Speed** | Baseline | +10-20% | +30-50% |
| **Memory Usage** | ~70 GB | ~80 GB | ~100 GB |
| **Risk Level** | Low | Low | Medium |
| **Recommended For** | Fallback | **First Try** | Experienced |

---

## Best Practices for GB10

1. **Always enable:**
   - `quantize: true` (qfloat8)
   - `gradient_checkpointing: true`
   - `cache_latents_to_disk: true`

2. **Start conservative:**
   - Use optimized config first
   - Monitor for 50+ steps
   - Then experiment if desired

3. **Monitor memory:**
   - Watch `nvidia-smi` during first run
   - Note peak memory usage
   - Adjust if getting close to 119 GB

4. **Test the `low_vram` setting:**
   - Start with `false`
   - Switch to `true` only if errors occur

5. **Don't over-optimize:**
   - Batch size 2 is the maximum you should try
   - Higher batch sizes won't fit in memory
   - Training quality matters more than speed

---

## Quick Start Commands

```bash
# Activate environment
cd /home/jay/Documents/ai-toolkit
source venv/bin/activate

# Test with optimized config (RECOMMENDED)
python run.py config/rebecka_config-gb10-optimized.yml

# Or test experimental (AFTER optimized works)
python run.py config/rebecka_config-gb10-experimental.yml

# Fall back to original if needed
python run.py datasets/rebecka/config.yml

# Monitor training
tail -f output/Rebecka-nsfw-high-gb10/training.log
```

---

## Files Reference

| File | Location | Purpose |
|------|----------|---------|
| `config.yml` | `datasets/rebecka/` | Original configuration |
| `rebecka_config-gb10-optimized.yml` | `config/` | **Recommended for GB10** |
| `rebecka_config-gb10-experimental.yml` | `config/` | Aggressive optimization (test) |
| `GB10_OPTIMIZATION_GUIDE.md` | `docs/` | This guide |
| `QUICK_CONFIG_COMPARISON.md` | `docs/` | Quick reference |

---

**Created:** 2025-11-14
**GPU:** NVIDIA GB10 (119.7 GB unified memory)
**Model:** Wan2.2-T2V-A14B (14B parameters)
**Recommendation:** Start with `config-gb10-optimized.yml`
