"""
Utility functions for device detection and memory management.
Handles unified memory GPUs (sm_121/GB10) that report 0 VRAM.
"""

import torch
from typing import Optional


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


def get_device_memory_gb(device: Optional[torch.device] = None, default: float = 32.0) -> float:
    """
    Get GPU memory in GB, with fallback for unified memory GPUs.

    For unified memory GPUs, attempts to return system RAM amount.
    For standard GPUs, returns dedicated VRAM.

    Args:
        device: Optional torch device. If None, uses current device.
        default: Default value to return if memory cannot be determined.

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
            # Unified memory GPU - try to get system RAM
            try:
                import psutil
                # Return system RAM in GB
                return psutil.virtual_memory().total / (1024**3)
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

        print("=" * 50)
        print("Device Information:")
        print(f"  Name: {device_name}")

        if is_unified:
            print(f"  Architecture: Unified Memory")
            print(f"  Available Memory: {memory_gb:.1f} GB (System RAM)")
            print(f"  Note: This GPU uses unified memory architecture")
            print(f"        Recommend setting low_vram: true in config")
        else:
            print(f"  Architecture: Dedicated VRAM")
            print(f"  VRAM: {memory_gb:.1f} GB")

        print("=" * 50)

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
