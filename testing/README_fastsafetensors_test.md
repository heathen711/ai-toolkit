# fastsafetensors Performance Testing

This directory contains a performance test script for comparing standard safetensors vs fastsafetensors with GPUDirect Storage.

## Test Script

**`test_fastsafetensors_performance.py`** - Comprehensive performance comparison tool

## Features

- **Cache Clearing**: Clears Linux filesystem cache before each test for fair comparison
- **Detailed Metrics**: Reports loading time, speed (MB/s), and speedup ratio
- **Memory Management**: Properly unloads tensors and clears GPU memory between tests
- **Device Flexibility**: Test with CPU or any CUDA device

## Requirements

- Root/sudo privileges (required to clear filesystem cache)
- PyTorch with CUDA support (for GPU testing)
- fastsafetensors library (optional, test will skip if not available)

## Usage

### Basic Usage

```bash
sudo python testing/test_fastsafetensors_performance.py <path_to_safetensors_file>
```

### Specify Device

```bash
# Test with specific CUDA device
sudo python testing/test_fastsafetensors_performance.py model.safetensors --device cuda:0

# Test with CPU
sudo python testing/test_fastsafetensors_performance.py model.safetensors --device cpu
```

### Examples

```bash
# Test a large model file (FLUX transformer)
sudo python testing/test_fastsafetensors_performance.py \
    models/flux_transformer.safetensors

# Test cached latents
sudo python testing/test_fastsafetensors_performance.py \
    datasets/my_data/_latent_cache/image_001.safetensors

# Test text embeddings
sudo python testing/test_fastsafetensors_performance.py \
    datasets/my_data/_t_e_cache/embedding_001.safetensors
```

## How It Works

The test performs these steps:

1. **File Analysis**: Reads file size and metadata
2. **Test 1 - Standard Loading**:
   - Clears filesystem cache
   - Loads file with standard `safetensors.torch.load_file()`
   - Measures wall time
   - Unloads and cleans up memory
3. **Test 2 - fastsafetensors + GPUDirect**:
   - Clears filesystem cache again
   - Loads file with `fastsafetensors` and GPUDirect enabled
   - Measures wall time
   - Unloads and cleans up memory
4. **Comparison**: Reports speedup ratio and performance improvement

## Sample Output

```
================================================================================
FASTSAFETENSORS PERFORMANCE TEST
================================================================================

Test Configuration:
  File: flux_transformer.safetensors
  Path: /models/flux_transformer.safetensors
  Size: 2048.50 MB (2.000 GB)
  Device: cuda
  PyTorch: 2.1.0
  CUDA: 13.0
  GPU: NVIDIA RTX 4090

================================================================================
Clearing system file cache...
================================================================================
✓ File cache cleared successfully

================================================================================
TEST 1: Standard safetensors loading
================================================================================
Method: disk->cpu->gpu (standard safetensors)
Device: cuda

Starting load...

✓ Load completed successfully
  Time: 8.234s
  Tensors: 145
  Total elements: 12,345,678,900

================================================================================
Clearing system file cache...
================================================================================
✓ File cache cleared successfully

================================================================================
TEST 2: fastsafetensors with GPUDirect loading
================================================================================
Method: disk->gpu (GPUDirect Storage)
Device: cuda

Starting load...

✓ Load completed successfully
  Time: 1.234s
  Tensors: 145
  Total elements: 12,345,678,900

================================================================================
PERFORMANCE COMPARISON SUMMARY
================================================================================

File: flux_transformer.safetensors
Size: 2048.50 MB (2.000 GB)
Device: cuda

Method                                   Time (s)     Speed (MB/s)
----------------------------------------------------------------------
Standard safetensors                        8.234          248.77
fastsafetensors + GPUDirect                 1.234         1660.27

----------------------------------------------------------------------
Speedup: 6.67x faster
Time saved: 7.000s (85.0% improvement)

✓ fastsafetensors is FASTER

================================================================================

✓ All tests completed successfully
```

## Cache Clearing Explanation

The script uses Linux's `/proc/sys/vm/drop_caches` interface to clear:
- **Page cache**: Cached file data in RAM
- **Dentries**: Directory entry cache
- **Inodes**: Inode cache

This ensures each test performs actual disk I/O rather than reading from RAM cache, providing accurate measurements of loading performance.

## Why Sudo is Required

Clearing the filesystem cache requires root privileges because it affects system-wide resources. The script checks for root access and provides clear error messages if not running with sudo.

## Interpreting Results

### When fastsafetensors is Faster

- **Large files (>1GB)**: Maximum benefit from GPUDirect
- **CUDA devices**: Direct disk-to-GPU transfer avoids CPU bottleneck
- **NVMe storage**: GPUDirect Storage designed for NVMe SSDs

### When Performance is Similar

- **Small files (<100MB)**: Overhead may negate benefits
- **CPU device**: No GPUDirect benefit without GPU
- **Non-NVMe storage**: Limited by storage speed

### Expected Speedups

Based on research paper results:
- **7B param models**: 4.8x - 5.5x faster
- **13B param models**: 5.8x - 6.2x faster
- **70B+ param models**: 6.5x - 7.5x faster

## Troubleshooting

### Permission Denied
```bash
✗ Permission denied. This script requires sudo privileges.
  Run: sudo python testing/test_fastsafetensors_performance.py <file>
```
**Solution**: Run with `sudo`

### fastsafetensors Not Available
```
⚠ Warning: fastsafetensors not available
  Install with: pip install fastsafetensors
```
**Solution**: Install fastsafetensors:
```bash
pip install fastsafetensors
```

### CUDA Out of Memory
If the file is too large for your GPU memory, the test will fail. Try:
```bash
# Test with CPU instead
sudo python testing/test_fastsafetensors_performance.py model.safetensors --device cpu
```

## Notes

- The script automatically uses CUDA if available, falls back to CPU otherwise
- All timing includes tensor deserialization and device transfer
- Memory is properly cleaned between tests to avoid interference
- The 1-second sleep after cache clearing ensures system stability
