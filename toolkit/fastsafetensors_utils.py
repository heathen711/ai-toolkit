"""
Utility functions for loading safetensors files with fastsafetensors and GPUDirect support.

This module provides optimized loading for safetensors files using the fastsafetensors library,
which can leverage NVIDIA GPUDirect Storage for direct NVMe-to-GPU transfers.
"""

import os
import time
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


# Track GDS availability - check once and cache result
_GDS_AVAILABLE = None
_GDS_CHECK_DONE = False


def check_gds_available() -> bool:
    """
    Check if GPUDirect Storage is available on the system.

    Returns:
        True if GDS is available and working, False otherwise
    """
    global _GDS_AVAILABLE, _GDS_CHECK_DONE

    if _GDS_CHECK_DONE:
        return _GDS_AVAILABLE

    _GDS_CHECK_DONE = True
    _GDS_AVAILABLE = False

    # Check if CUDA is available
    if not torch.cuda.is_available():
        return False

    # Check if nvidia-fs module is loaded
    try:
        with open('/proc/modules', 'r') as f:
            modules = f.read()
            if 'nvidia_fs' not in modules:
                print_acc("GPUDirect Storage: nvidia-fs kernel module not loaded")
                return False
    except:
        return False

    # Check if GDS is accessible via /proc
    try:
        if os.path.exists('/proc/driver/nvidia-fs/version'):
            with open('/proc/driver/nvidia-fs/version', 'r') as f:
                version = f.read().strip()
                print_acc(f"GPUDirect Storage detected: {version}")
                _GDS_AVAILABLE = True
                return True
    except:
        pass

    return False


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
    # Convert device to string if needed
    device_str = str(device) if isinstance(device, torch.device) else device
    is_cuda = "cuda" in device_str.lower()

    # Normalize device for fastsafetensors - it requires explicit index
    # Convert "cuda" to "cuda:0" for fastsafetensors compatibility
    fastsafe_device = device_str
    if device_str == "cuda":
        fastsafe_device = "cuda:0"

    # Get file info for logging
    filename = os.path.basename(path)
    file_size_mb = 0.0
    if os.path.exists(path):
        file_size_mb = os.path.getsize(path) / (1024 * 1024)

    # Determine loading method and destination
    use_fastsafe = config is not None and config.use_fastsafetensors
    use_gpudirect = use_fastsafe and config.use_gpu_direct

    # Auto-disable GDS if not available on the system
    if use_gpudirect and is_cuda:
        if not check_gds_available():
            use_gpudirect = False
            config.use_gpu_direct = False
            print_acc("GPUDirect Storage not available, using fastsafetensors without GDS")

    # Determine method description
    if use_fastsafe and use_gpudirect and is_cuda:
        method = "disk->gpu (GPUDirect)"
    elif use_fastsafe and is_cuda:
        method = "disk->cpu->gpu (fastsafetensors)"
    elif use_fastsafe and not is_cuda:
        method = "disk->cpu (fastsafetensors)"
    elif is_cuda:
        method = "disk->cpu->gpu (standard)"
    else:
        method = "disk->cpu (standard)"

    destination = device_str

    # Log start
    print_acc(f"Loading {filename} ({file_size_mb:.2f} MB) | Destination: {destination} | Method: {method}")

    # Start timing
    start_time = time.time()

    # Use standard safetensors if no config or fastsafetensors disabled
    if config is None or not config.use_fastsafetensors:
        tensors = standard_load_file(path, device=device_str)
        elapsed_time = time.time() - start_time
        print_acc(f"Loaded {filename} in {elapsed_time:.3f}s")
        return tensors

    # Use fastsafetensors
    tensors = {}
    try:
        # nogds=True means NO GPUDirect (disable it), nogds=False means USE GPUDirect
        nogds = not config.use_gpu_direct

        with fastsafe_open(
            filenames=[path],
            nogds=nogds,
            device=fastsafe_device,  # Use normalized device with explicit index
            debug_log=config.debug_log
        ) as f:
            for key in f.get_keys():
                # Clone and detach to ensure tensor is owned and not sharing memory
                tensors[key] = f.get_tensor(key).clone().detach()

        # Log completion
        elapsed_time = time.time() - start_time
        print_acc(f"Loaded {filename} in {elapsed_time:.3f}s")

    except Exception as e:
        error_msg = str(e)

        # Check if this is a GDS-specific error
        if "register_buffer" in error_msg or "submit_io" in error_msg:
            print_acc(f"Warning: GPUDirect Storage failed ({error_msg[:80]}...)")
            print_acc("Retrying with fastsafetensors without GDS")

            # Mark GDS as unavailable globally
            global _GDS_AVAILABLE, _GDS_CHECK_DONE
            _GDS_AVAILABLE = False
            _GDS_CHECK_DONE = True

            # Retry without GDS
            try:
                start_time = time.time()
                with fastsafe_open(
                    filenames=[path],
                    nogds=True,  # Disable GDS
                    device=fastsafe_device,
                    debug_log=config.debug_log
                ) as f:
                    for key in f.get_keys():
                        tensors[key] = f.get_tensor(key).clone().detach()

                elapsed_time = time.time() - start_time
                print_acc(f"Loaded {filename} (no GDS) in {elapsed_time:.3f}s")
                return tensors

            except Exception as e2:
                print_acc(f"Warning: fastsafetensors retry failed ({e2}), falling back to standard safetensors")
        else:
            print_acc(f"Warning: fastsafetensors failed ({error_msg}), falling back to standard safetensors")

        # Final fallback to standard safetensors
        start_time = time.time()
        tensors = standard_load_file(path, device=device_str)
        elapsed_time = time.time() - start_time
        print_acc(f"Loaded {filename} (standard) in {elapsed_time:.3f}s")

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
        "gpu_direct_available": False,
        "gpu_direct_checked": _GDS_CHECK_DONE,
    }

    if FASTSAFETENSORS_AVAILABLE:
        try:
            import fastsafetensors
            info["version"] = getattr(fastsafetensors, "__version__", "unknown")
            # Check actual GDS availability
            info["gpu_direct_available"] = check_gds_available()
        except:
            pass

    return info


def print_fastsafetensors_status():
    """Print current fastsafetensors and GPUDirect Storage status."""
    info = get_fastsafetensors_info()

    print_acc("=" * 60)
    print_acc("fastsafetensors Status:")
    print_acc(f"  Library available: {info['available']}")

    if info['available']:
        print_acc(f"  Version: {info['version']}")
        print_acc(f"  GPUDirect Storage: {'Available' if info['gpu_direct_available'] else 'Not available'}")

        if not info['gpu_direct_available']:
            print_acc("\n  To enable GPUDirect Storage:")
            print_acc("    1. Install nvidia-gds: sudo apt-get install nvidia-gds")
            print_acc("    2. Load module: sudo modprobe nvidia-fs")
            print_acc("    3. Verify: cat /proc/driver/nvidia-fs/version")
    else:
        print_acc("  Install with: pip install fastsafetensors")

    print_acc("=" * 60)


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
