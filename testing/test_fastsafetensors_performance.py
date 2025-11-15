#!/usr/bin/env python3
"""
Performance test script for comparing standard safetensors vs fastsafetensors with GPUDirect.

This script performs a controlled comparison by:
1. Clearing Linux filesystem cache before each test
2. Loading a safetensors file with standard method
3. Clearing cache again
4. Loading the same file with fastsafetensors + GPUDirect
5. Reporting detailed timing and performance metrics

Usage:
    sudo python testing/test_fastsafetensors_performance.py <path_to_safetensors_file> [device]

Arguments:
    path_to_safetensors_file: Path to the .safetensors file to test
    device: Target device (default: 'cuda' if available, else 'cpu')

Examples:
    sudo python testing/test_fastsafetensors_performance.py models/flux_transformer.safetensors
    sudo python testing/test_fastsafetensors_performance.py models/flux_transformer.safetensors cuda:0
    sudo python testing/test_fastsafetensors_performance.py cache/latents.safetensors cpu

Note: This script requires sudo privileges to clear filesystem cache.
"""

import sys
import os
import time
import subprocess
import gc
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from safetensors.torch import load_file as standard_load_file

try:
    from toolkit.fastsafetensors_utils import load_file_fast, create_fast_config
    FASTSAFETENSORS_AVAILABLE = True
except ImportError:
    FASTSAFETENSORS_AVAILABLE = False
    print("Warning: fastsafetensors_utils not available")


def clear_system_cache():
    """
    Clear Linux filesystem cache.

    Requires sudo privileges. Drops all caches including:
    - Page cache
    - Dentries and inodes

    This ensures fair testing by forcing actual disk reads.
    """
    print("\n" + "="*80)
    print("Clearing system file cache...")
    print("="*80)
    try:
        # Sync to ensure all dirty pages are written
        subprocess.run(['sync'], check=True)

        # Drop caches: 3 = clear pagecache, dentries and inodes
        subprocess.run(
            ['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'],
            check=True
        )

        print("✓ File cache cleared successfully")
        # Give system a moment to settle
        time.sleep(1)

    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to clear cache: {e}")
        print("  Make sure you run this script with sudo:")
        print(f"  sudo python {sys.argv[0]} <file>")
        sys.exit(1)
    except PermissionError:
        print("✗ Permission denied. This script requires sudo privileges.")
        print(f"  Run: sudo python {sys.argv[0]} <file>")
        sys.exit(1)


def get_file_info(path):
    """Get file size and basic info."""
    if not os.path.exists(path):
        print(f"✗ Error: File not found: {path}")
        sys.exit(1)

    size_bytes = os.path.getsize(path)
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_bytes / (1024 * 1024 * 1024)

    return {
        'path': path,
        'filename': os.path.basename(path),
        'size_bytes': size_bytes,
        'size_mb': size_mb,
        'size_gb': size_gb,
    }


def cleanup_memory():
    """Force Python garbage collection and clear CUDA cache if available."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    # Give system a moment to settle
    time.sleep(0.5)


def test_standard_loading(file_path, device):
    """Test loading with standard safetensors."""
    print("\n" + "="*80)
    print("TEST 1: Standard safetensors loading")
    print("="*80)
    print(f"Method: disk->cpu->gpu (standard safetensors)")
    print(f"Device: {device}")

    # Clear cache before test
    clear_system_cache()

    print("\nStarting load...")
    start_time = time.time()

    # Load the file
    state_dict = standard_load_file(file_path, device=str(device))

    # Ensure completion (especially for CUDA)
    if 'cuda' in str(device):
        torch.cuda.synchronize()

    elapsed = time.time() - start_time

    # Get tensor info
    num_tensors = len(state_dict)
    total_elements = sum(t.numel() for t in state_dict.values())

    print(f"\n✓ Load completed successfully")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Tensors: {num_tensors}")
    print(f"  Total elements: {total_elements:,}")

    # Cleanup
    del state_dict
    cleanup_memory()

    return elapsed


def test_fastsafetensors_loading(file_path, device):
    """Test loading with fastsafetensors + GPUDirect."""
    print("\n" + "="*80)
    print("TEST 2: fastsafetensors with GPUDirect loading")
    print("="*80)

    if not FASTSAFETENSORS_AVAILABLE:
        print("✗ fastsafetensors not available - skipping test")
        return None

    is_cuda = 'cuda' in str(device)
    if is_cuda:
        print(f"Method: disk->gpu (GPUDirect Storage)")
    else:
        print(f"Method: disk->cpu (fastsafetensors)")
    print(f"Device: {device}")

    # Clear cache before test
    clear_system_cache()

    # Create config with GPUDirect enabled
    config = create_fast_config(
        use_fastsafetensors=True,
        use_gpu_direct=True,
        debug=False
    )

    print("\nStarting load...")
    start_time = time.time()

    # Load the file
    state_dict = load_file_fast(file_path, device=device, config=config)

    # Ensure completion (especially for CUDA)
    if 'cuda' in str(device):
        torch.cuda.synchronize()

    elapsed = time.time() - start_time

    # Get tensor info
    num_tensors = len(state_dict)
    total_elements = sum(t.numel() for t in state_dict.values())

    print(f"\n✓ Load completed successfully")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Tensors: {num_tensors}")
    print(f"  Total elements: {total_elements:,}")

    # Cleanup
    del state_dict
    cleanup_memory()

    return elapsed


def print_comparison(file_info, standard_time, fastsafe_time, device):
    """Print detailed comparison of results."""
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON SUMMARY")
    print("="*80)

    print(f"\nFile: {file_info['filename']}")
    print(f"Size: {file_info['size_mb']:.2f} MB ({file_info['size_gb']:.3f} GB)")
    print(f"Device: {device}")

    print(f"\n{'Method':<40} {'Time (s)':<12} {'Speed (MB/s)':<15}")
    print("-" * 70)

    standard_speed = file_info['size_mb'] / standard_time
    print(f"{'Standard safetensors':<40} {standard_time:>8.3f}     {standard_speed:>12.2f}")

    if fastsafe_time is not None:
        fastsafe_speed = file_info['size_mb'] / fastsafe_time
        print(f"{'fastsafetensors + GPUDirect':<40} {fastsafe_time:>8.3f}     {fastsafe_speed:>12.2f}")

        # Calculate speedup
        speedup = standard_time / fastsafe_time
        improvement_pct = ((standard_time - fastsafe_time) / standard_time) * 100

        print("\n" + "-" * 70)
        print(f"Speedup: {speedup:.2f}x faster")
        print(f"Time saved: {standard_time - fastsafe_time:.3f}s ({improvement_pct:.1f}% improvement)")

        if speedup > 1.0:
            print(f"\n✓ fastsafetensors is FASTER")
        elif speedup < 1.0:
            print(f"\n✗ fastsafetensors is SLOWER (might not be beneficial for this file/device)")
        else:
            print(f"\n= Performance is EQUIVALENT")
    else:
        print(f"{'fastsafetensors + GPUDirect':<40} {'N/A':<12} {'N/A':<15}")
        print("\n✗ fastsafetensors test was skipped")

    print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Test fastsafetensors performance with cache clearing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'file_path',
        help='Path to the safetensors file to test'
    )
    parser.add_argument(
        '--device',
        default=None,
        help='Target device (default: cuda if available, else cpu)'
    )

    args = parser.parse_args()

    # Determine device
    if args.device:
        device = args.device
    else:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    print("\n" + "="*80)
    print("FASTSAFETENSORS PERFORMANCE TEST")
    print("="*80)

    # Get file info
    file_info = get_file_info(args.file_path)

    print(f"\nTest Configuration:")
    print(f"  File: {file_info['filename']}")
    print(f"  Path: {file_info['path']}")
    print(f"  Size: {file_info['size_mb']:.2f} MB ({file_info['size_gb']:.3f} GB)")
    print(f"  Device: {device}")
    print(f"  PyTorch: {torch.__version__}")

    if torch.cuda.is_available():
        print(f"  CUDA: {torch.version.cuda}")
        print(f"  GPU: {torch.cuda.get_device_name(0)}")

    if not FASTSAFETENSORS_AVAILABLE:
        print(f"\n⚠ Warning: fastsafetensors not available")
        print(f"  Install with: pip install fastsafetensors")

    # Check if running as root
    if os.geteuid() != 0:
        print("\n✗ Error: This script must be run with sudo to clear filesystem cache")
        print(f"  Run: sudo python {sys.argv[0]} {args.file_path}")
        sys.exit(1)

    # Run tests
    standard_time = test_standard_loading(file_info['path'], device)

    fastsafe_time = None
    if FASTSAFETENSORS_AVAILABLE:
        fastsafe_time = test_fastsafetensors_loading(file_info['path'], device)

    # Print comparison
    print_comparison(file_info, standard_time, fastsafe_time, device)

    print("\n✓ All tests completed successfully\n")


if __name__ == '__main__':
    main()
