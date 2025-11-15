#!/usr/bin/env python3
"""
Get accurate GPU memory information for unified memory GPUs.
Called by the web UI when nvidia-smi reports [Not Supported].
"""

import sys
import os
import json

# Add parent directory to path to import toolkit modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from toolkit.device_utils import get_meminfo, is_unified_memory_gpu
import torch


def get_gpu_memory_info(gpu_index: int = 0) -> dict:
    """
    Get memory information for a GPU, handling unified memory gracefully.

    Returns:
        Dictionary with memory info in MB for consistency with nvidia-smi
    """
    result = {
        "is_unified": False,
        "total_mb": 0,
        "used_mb": 0,
        "free_mb": 0,
    }

    try:
        if not torch.cuda.is_available():
            return result

        # Check if this is a unified memory GPU
        is_unified = is_unified_memory_gpu(gpu_index)

        # Also check GPU name for known unified memory GPUs
        props = torch.cuda.get_device_properties(gpu_index)
        gpu_name = props.name.upper()
        known_unified_gpus = ['GB10', 'DGX SPARK', 'JETSON']

        # Mark as unified if either detection method works
        if is_unified or any(name in gpu_name for name in known_unified_gpus):
            is_unified = True

        result["is_unified"] = is_unified

        # For unified memory OR when called explicitly (e.g., from UI fallback),
        # always get memory from /proc/meminfo as it's more accurate
        if is_unified or True:  # Always use meminfo when available
            # Get memory from /proc/meminfo for unified memory GPUs
            meminfo = get_meminfo()

            if meminfo:
                # Convert GB to MB
                mem_total_mb = int(meminfo.get('mem_total', 0) * 1024)
                mem_available_mb = int(meminfo.get('mem_available', 0) * 1024)
                mem_used_mb = mem_total_mb - mem_available_mb

                result["total_mb"] = mem_total_mb
                result["free_mb"] = mem_available_mb
                result["used_mb"] = mem_used_mb
                return result  # Return early if we got meminfo

            # Fallback to psutil
            try:
                import psutil
                vm = psutil.virtual_memory()
                result["total_mb"] = int(vm.total / (1024 * 1024))
                result["free_mb"] = int(vm.available / (1024 * 1024))
                result["used_mb"] = int((vm.total - vm.available) / (1024 * 1024))
                return result  # Return early if psutil worked
            except ImportError:
                pass

        # Standard GPU fallback - use torch CUDA memory info
        # (Only reached if meminfo/psutil failed for unified memory)
        if not is_unified:
            result["total_mb"] = int(props.total_memory / (1024 * 1024))

            # Get current memory usage
            mem_allocated = torch.cuda.memory_allocated(gpu_index)
            mem_reserved = torch.cuda.memory_reserved(gpu_index)

            result["used_mb"] = int(mem_reserved / (1024 * 1024))
            result["free_mb"] = result["total_mb"] - result["used_mb"]

    except Exception as e:
        print(f"Error getting GPU memory info: {e}", file=sys.stderr)

    return result


if __name__ == "__main__":
    # Get GPU index from command line argument, default to 0
    gpu_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    # Get memory info
    info = get_gpu_memory_info(gpu_index)

    # Output as JSON
    print(json.dumps(info))
