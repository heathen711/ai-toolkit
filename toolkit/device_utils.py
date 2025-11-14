"""
Utility functions for device detection and memory management.
Handles unified memory GPUs (sm_121/GB10, DGX Spark) that report 0 VRAM.

Based on NVIDIA DGX Spark documentation:
- cudaMemGetInfo underreports available memory (doesn't account for swap)
- nvidia-smi shows "Memory-Usage: Not Supported" for integrated GPUs
- Recommended to query /proc/meminfo for accurate memory estimates

Reference: https://docs.nvidia.com/dgx/dgx-spark/known-issues.html
"""

import torch
from typing import Optional, Dict
import os


def is_unified_memory_gpu(device: Optional[torch.device] = None) -> bool:
    """
    Check if the GPU uses unified memory architecture.

    Unified memory GPUs (like sm_121/GB10) report total_memory as 0.

    Args:
        device: Optional torch device. If None, uses current device.

    Returns:
        True if the GPU uses unified memory (reports 0 VRAM), False otherwise.
    """
    if not torch.cuda.is_available():
        return False

    try:
        if device is None:
            device_id = torch.cuda.current_device()
        elif isinstance(device, torch.device):
            device_id = device.index if device.index is not None else 0
        elif isinstance(device, int):
            device_id = device
        elif isinstance(device, str):
            # Handle "cuda:0" format
            if ":" in device:
                device_id = int(device.split(":")[1])
            else:
                device_id = 0
        else:
            device_id = 0

        props = torch.cuda.get_device_properties(device_id)
        # Unified memory GPUs report 0 total memory
        return props.total_memory == 0
    except Exception:
        # If we can't determine, assume it's not unified memory
        return False


def get_meminfo() -> Dict[str, float]:
    """
    Read /proc/meminfo for accurate memory information on Linux.

    This is more accurate than cudaMemGetInfo for unified memory systems,
    as it accounts for memory that can be reclaimed from swap.

    Returns:
        Dictionary with memory values in GB:
        - mem_total: Total system memory
        - mem_available: Available memory (includes reclaimable)
        - swap_free: Free swap space
        - swap_total: Total swap space
    """
    meminfo = {}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(':')
                    value_kb = int(parts[1])
                    value_gb = value_kb / (1024 * 1024)  # Convert KB to GB

                    if key == 'MemTotal':
                        meminfo['mem_total'] = value_gb
                    elif key == 'MemAvailable':
                        meminfo['mem_available'] = value_gb
                    elif key == 'SwapFree':
                        meminfo['swap_free'] = value_gb
                    elif key == 'SwapTotal':
                        meminfo['swap_total'] = value_gb
    except (FileNotFoundError, PermissionError):
        # /proc/meminfo not available (Windows, macOS, or permission issue)
        pass

    return meminfo


def get_device_memory_gb(device: Optional[torch.device] = None, default: float = 32.0, include_swap: bool = False) -> float:
    """
    Get GPU memory in GB, with fallback for unified memory GPUs.

    For unified memory GPUs, uses /proc/meminfo when available (more accurate
    than cudaMemGetInfo as it accounts for swap). Falls back to psutil if
    /proc/meminfo is unavailable.

    For standard GPUs, returns dedicated VRAM.

    Per NVIDIA DGX Spark documentation, cudaMemGetInfo underreports available
    memory on unified memory systems because it doesn't account for memory
    that can be reclaimed from swap space.

    Args:
        device: Optional torch device. If None, uses current device.
        default: Default value to return if memory cannot be determined.
        include_swap: For unified memory, whether to include swap space in total.

    Returns:
        Memory size in GB.
    """
    if not torch.cuda.is_available():
        return default

    try:
        if device is None:
            device_id = torch.cuda.current_device()
        elif isinstance(device, torch.device):
            device_id = device.index if device.index is not None else 0
        elif isinstance(device, int):
            device_id = device
        elif isinstance(device, str):
            if ":" in device:
                device_id = int(device.split(":")[1])
            else:
                device_id = 0
        else:
            device_id = 0

        props = torch.cuda.get_device_properties(device_id)

        if props.total_memory == 0:
            # Unified memory GPU - use /proc/meminfo for accurate reporting
            meminfo = get_meminfo()

            if meminfo:
                # Use MemAvailable as it includes reclaimable memory
                available = meminfo.get('mem_available', 0)
                if include_swap:
                    available += meminfo.get('swap_free', 0)

                if available > 0:
                    return available

            # Fallback to psutil if /proc/meminfo unavailable
            try:
                import psutil
                vm = psutil.virtual_memory()
                available = vm.available / (1024**3)

                if include_swap:
                    swap = psutil.swap_memory()
                    available += swap.free / (1024**3)

                return available
            except ImportError:
                # psutil not available, return conservative default
                return default
        else:
            # Standard GPU - return dedicated VRAM
            return props.total_memory / (1024**3)

    except Exception:
        return default


def get_device_name(device: Optional[torch.device] = None) -> str:
    """
    Get the name of the CUDA device.

    Args:
        device: Optional torch device. If None, uses current device.

    Returns:
        Device name string, or "Unknown" if cannot be determined.
    """
    if not torch.cuda.is_available():
        return "CPU"

    try:
        if device is None:
            device_id = torch.cuda.current_device()
        elif isinstance(device, torch.device):
            device_id = device.index if device.index is not None else 0
        elif isinstance(device, int):
            device_id = device
        elif isinstance(device, str):
            if ":" in device:
                device_id = int(device.split(":")[1])
            else:
                device_id = 0
        else:
            device_id = 0

        props = torch.cuda.get_device_properties(device_id)
        return props.name
    except Exception:
        return "Unknown"


def flush_system_caches():
    """
    Flush system buffer caches to free memory (Linux only).

    Useful for debugging memory issues on unified memory systems.
    Requires root/sudo privileges.

    Per NVIDIA DGX Spark documentation, this can help troubleshoot
    memory-related issues by freeing cached memory.

    Usage:
        Run from command line with sudo:
        sudo python -c "from toolkit.device_utils import flush_system_caches; flush_system_caches()"

    Or manually:
        sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
    """
    try:
        import subprocess
        print("Flushing system caches (requires sudo)...")
        subprocess.run(['sudo', 'sh', '-c', 'sync; echo 3 > /proc/sys/vm/drop_caches'], check=True)
        print("System caches flushed successfully.")
        print("Note: Restart your application after flushing caches.")
    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError) as e:
        print(f"Failed to flush caches: {e}")
        print("Try manually: sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'")


def print_device_info(device: Optional[torch.device] = None):
    """
    Print detailed information about the CUDA device.
    Handles unified memory GPUs gracefully.

    Args:
        device: Optional torch device. If None, uses current device.
    """
    if not torch.cuda.is_available():
        print("CUDA is not available. Using CPU.")
        return

    try:
        device_name = get_device_name(device)
        is_unified = is_unified_memory_gpu(device)
        memory_gb = get_device_memory_gb(device)
        memory_with_swap = get_device_memory_gb(device, include_swap=True)

        print("=" * 60)
        print("Device Information:")
        print(f"  Name: {device_name}")

        if is_unified:
            print(f"  Architecture: Unified Memory (UMA)")
            print(f"  Available Memory: {memory_gb:.1f} GB")

            if memory_with_swap > memory_gb:
                print(f"  With Swap: {memory_with_swap:.1f} GB")

            # Show /proc/meminfo details if available
            meminfo = get_meminfo()
            if meminfo:
                print(f"\n  Memory Details (from /proc/meminfo):")
                if 'mem_total' in meminfo:
                    print(f"    Total RAM: {meminfo['mem_total']:.1f} GB")
                if 'mem_available' in meminfo:
                    print(f"    Available: {meminfo['mem_available']:.1f} GB")
                if 'swap_total' in meminfo and meminfo['swap_total'] > 0:
                    print(f"    Swap Total: {meminfo['swap_total']:.1f} GB")
                    if 'swap_free' in meminfo:
                        print(f"    Swap Free: {meminfo['swap_free']:.1f} GB")

            print(f"\n  Note: This GPU uses unified memory architecture")
            print(f"        - nvidia-smi may show 'Memory-Usage: Not Supported'")
            print(f"        - cudaMemGetInfo underreports available memory")
            print(f"        - Try low_vram: false first, then true if errors occur")
        else:
            print(f"  Architecture: Dedicated VRAM")
            print(f"  VRAM: {memory_gb:.1f} GB")

        print("=" * 60)

    except Exception as e:
        print(f"Could not determine device information: {e}")


def should_use_low_vram(device: Optional[torch.device] = None, memory_threshold_gb: float = 24.0) -> bool:
    """
    Determine if low_vram mode should be enabled based on device characteristics.

    Automatically returns True for:
    - Unified memory GPUs
    - GPUs with less than threshold GB of VRAM

    Args:
        device: Optional torch device. If None, uses current device.
        memory_threshold_gb: VRAM threshold in GB. Below this, low_vram is recommended.

    Returns:
        True if low_vram mode is recommended, False otherwise.
    """
    if not torch.cuda.is_available():
        return True

    # Always use low_vram for unified memory GPUs
    if is_unified_memory_gpu(device):
        return True

    # Use low_vram if memory is below threshold
    memory_gb = get_device_memory_gb(device, default=16.0)
    return memory_gb < memory_threshold_gb
