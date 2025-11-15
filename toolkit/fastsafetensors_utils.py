"""
Utility functions for loading safetensors files with fastsafetensors and GPUDirect support.

This module provides optimized loading for safetensors files using the fastsafetensors library,
which can leverage NVIDIA GPUDirect Storage for direct NVMe-to-GPU transfers.
"""

import os
import torch
from typing import Optional, Union, Dict, List
from collections import OrderedDict

from toolkit.print import print_acc

try:
    from fastsafetensors import fastsafe_open
    FASTSAFETENSORS_AVAILABLE = True
except ImportError:
    FASTSAFETENSORS_AVAILABLE = False
    print_acc("Warning: fastsafetensors not available. Falling back to standard safetensors.")

from safetensors.torch import load_file as standard_load_file, save_file


class FastSafetensorsConfig:
    """Configuration for fastsafetensors loading behavior."""

    def __init__(
        self,
        use_fastsafetensors: bool = False,
        use_gpu_direct: bool = True,
        debug_log: bool = False,
    ):
        """
        Initialize FastSafetensors configuration.

        Args:
            use_fastsafetensors: Whether to use fastsafetensors for loading (requires installation)
            use_gpu_direct: Whether to use GPUDirect Storage (nogds=False in fastsafetensors)
            debug_log: Whether to enable debug logging in fastsafetensors
        """
        self.use_fastsafetensors = use_fastsafetensors and FASTSAFETENSORS_AVAILABLE
        self.use_gpu_direct = use_gpu_direct
        self.debug_log = debug_log

        if use_fastsafetensors and not FASTSAFETENSORS_AVAILABLE:
            print_acc("Warning: fastsafetensors requested but not available. Install with: pip install fastsafetensors")


def load_file_fast(
    path: str,
    device: Union[str, torch.device] = "cpu",
    config: Optional[FastSafetensorsConfig] = None,
) -> Dict[str, torch.Tensor]:
    """
    Load a safetensors file, optionally using fastsafetensors with GPUDirect.

    This function provides a drop-in replacement for safetensors.torch.load_file
    with optional fastsafetensors acceleration.

    Args:
        path: Path to the safetensors file
        device: Target device for tensors (e.g., 'cpu', 'cuda', 'cuda:0')
        config: FastSafetensorsConfig object. If None, uses standard safetensors.

    Returns:
        Dictionary mapping tensor names to torch.Tensor objects

    Example:
        >>> config = FastSafetensorsConfig(use_fastsafetensors=True, use_gpu_direct=True)
        >>> state_dict = load_file_fast("model.safetensors", device="cuda", config=config)
    """
    # Use standard safetensors if no config or fastsafetensors disabled
    if config is None or not config.use_fastsafetensors:
        return standard_load_file(path, device=str(device))

    # Convert device to string if needed
    device_str = str(device) if isinstance(device, torch.device) else device

    # Use fastsafetensors
    tensors = {}
    try:
        # nogds=True means NO GPUDirect (disable it), nogds=False means USE GPUDirect
        nogds = not config.use_gpu_direct

        with fastsafe_open(
            filenames=[path],
            nogds=nogds,
            device=device_str,
            debug_log=config.debug_log
        ) as f:
            for key in f.get_keys():
                # Clone and detach to ensure tensor is owned and not sharing memory
                tensors[key] = f.get_tensor(key).clone().detach()
    except Exception as e:
        print_acc(f"Warning: fastsafetensors failed ({e}), falling back to standard safetensors")
        tensors = standard_load_file(path, device=device_str)

    return tensors


def load_model_weights_fast(
    path: str,
    device: Union[str, torch.device] = "cpu",
    config: Optional[FastSafetensorsConfig] = None,
) -> OrderedDict:
    """
    Load model weights from a safetensors file with optional fastsafetensors acceleration.

    Returns an OrderedDict to maintain compatibility with PyTorch model loading.

    Args:
        path: Path to the safetensors file
        device: Target device for tensors
        config: FastSafetensorsConfig object

    Returns:
        OrderedDict of model weights
    """
    state_dict = load_file_fast(path, device=device, config=config)
    return OrderedDict(state_dict)


def save_safetensors(
    tensors: Dict[str, torch.Tensor],
    path: str,
    metadata: Optional[Dict[str, str]] = None,
):
    """
    Save tensors to a safetensors file.

    This is a simple wrapper around safetensors.torch.save_file for consistency.
    Note: fastsafetensors currently only supports loading, not saving.

    Args:
        tensors: Dictionary of tensors to save
        path: Output file path
        metadata: Optional metadata dictionary
    """
    save_file(tensors, path, metadata=metadata)


def get_fastsafetensors_info() -> Dict[str, any]:
    """
    Get information about fastsafetensors availability and capabilities.

    Returns:
        Dictionary with fastsafetensors status information
    """
    info = {
        "available": FASTSAFETENSORS_AVAILABLE,
        "version": None,
        "gpu_direct_supported": False,
    }

    if FASTSAFETENSORS_AVAILABLE:
        try:
            import fastsafetensors
            info["version"] = getattr(fastsafetensors, "__version__", "unknown")
            # GPUDirect is supported if CUDA is available and we're on Linux
            info["gpu_direct_supported"] = torch.cuda.is_available() and os.name == 'posix'
        except:
            pass

    return info


def should_use_fastsafetensors(
    file_size_bytes: Optional[int] = None,
    device: Union[str, torch.device] = "cpu",
    threshold_mb: int = 100,
) -> bool:
    """
    Heuristic to determine if fastsafetensors would be beneficial.

    fastsafetensors provides most benefit for:
    - Large files (> threshold_mb)
    - CUDA devices (especially with GPUDirect)

    Args:
        file_size_bytes: Size of the file in bytes (if known)
        device: Target device
        threshold_mb: Minimum file size in MB to consider fastsafetensors

    Returns:
        True if fastsafetensors is recommended
    """
    if not FASTSAFETENSORS_AVAILABLE:
        return False

    device_str = str(device) if isinstance(device, torch.device) else device
    is_cuda = "cuda" in device_str.lower()

    # Always beneficial for CUDA if available
    if is_cuda:
        # Check file size if provided
        if file_size_bytes is not None:
            threshold_bytes = threshold_mb * 1024 * 1024
            return file_size_bytes >= threshold_bytes
        # If no file size info, assume it's worth trying
        return True

    # For CPU, only if file is very large
    if file_size_bytes is not None:
        threshold_bytes = threshold_mb * 1024 * 1024 * 5  # 5x threshold for CPU
        return file_size_bytes >= threshold_bytes

    return False


# Convenience function to create a config from boolean flags
def create_fast_config(
    use_fastsafetensors: bool = False,
    use_gpu_direct: bool = True,
    debug: bool = False,
) -> FastSafetensorsConfig:
    """
    Create a FastSafetensorsConfig from simple boolean flags.

    Args:
        use_fastsafetensors: Enable fastsafetensors
        use_gpu_direct: Enable GPUDirect Storage
        debug: Enable debug logging

    Returns:
        FastSafetensorsConfig instance
    """
    return FastSafetensorsConfig(
        use_fastsafetensors=use_fastsafetensors,
        use_gpu_direct=use_gpu_direct,
        debug_log=debug,
    )
