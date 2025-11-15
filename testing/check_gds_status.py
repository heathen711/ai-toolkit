#!/usr/bin/env python3
"""
Check GPUDirect Storage (GDS) availability and configuration.

This script checks if NVIDIA GPUDirect Storage is available on your system
and provides guidance on how to enable it if it's not.

Usage:
    python testing/check_gds_status.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from toolkit.fastsafetensors_utils import check_gds_available, print_fastsafetensors_status, FASTSAFETENSORS_AVAILABLE


def check_nvidia_fs_module():
    """Check if nvidia-fs kernel module is loaded."""
    try:
        with open('/proc/modules', 'r') as f:
            modules = f.read()
            return 'nvidia_fs' in modules
    except:
        return False


def check_gds_version():
    """Get GDS version if available."""
    try:
        if os.path.exists('/proc/driver/nvidia-fs/version'):
            with open('/proc/driver/nvidia-fs/version', 'r') as f:
                return f.read().strip()
    except:
        pass
    return None


def check_cuda_version():
    """Get CUDA version."""
    if torch.cuda.is_available():
        return torch.version.cuda
    return None


def main():
    print("=" * 70)
    print("GPUDirect Storage (GDS) Status Check")
    print("=" * 70)
    print()

    # Check CUDA
    print("CUDA Status:")
    cuda_available = torch.cuda.is_available()
    print(f"  Available: {cuda_available}")

    if cuda_available:
        cuda_version = check_cuda_version()
        print(f"  Version: {cuda_version}")
        print(f"  Device: {torch.cuda.get_device_name(0)}")

        # Check CUDA version for GDS support
        if cuda_version:
            try:
                major, minor = map(int, cuda_version.split('.')[:2])
                cuda_ver_num = major * 10 + minor

                if cuda_ver_num >= 114:
                    print(f"  GDS Support: ✓ (CUDA {cuda_version} >= 11.4)")
                else:
                    print(f"  GDS Support: ✗ (CUDA {cuda_version} < 11.4 - upgrade needed)")
            except:
                print(f"  GDS Support: ? (Could not parse CUDA version)")
    else:
        print("  ✗ CUDA not available - GDS requires CUDA")

    print()

    # Check nvidia-fs module
    print("nvidia-fs Kernel Module:")
    module_loaded = check_nvidia_fs_module()
    print(f"  Loaded: {module_loaded}")

    if module_loaded:
        print("  Status: ✓ Module is loaded")
    else:
        print("  Status: ✗ Module not loaded")
        print("  Action: Run 'sudo modprobe nvidia-fs' to load")

    print()

    # Check GDS version
    print("GPUDirect Storage:")
    gds_version = check_gds_version()

    if gds_version:
        print(f"  Version: {gds_version}")
        print("  Status: ✓ GDS is installed and accessible")
    else:
        print("  Status: ✗ GDS not detected")
        print("  Path: /proc/driver/nvidia-fs/version not found")

    print()

    # Overall GDS availability
    print("Overall GDS Availability:")
    gds_available = check_gds_available()

    if gds_available:
        print("  ✓ GPUDirect Storage is AVAILABLE")
        print()
        print("You can use fastsafetensors with GPUDirect Storage:")
        print("  model:")
        print("    use_fastsafetensors: true")
        print("    use_gpu_direct: true")
    else:
        print("  ✗ GPUDirect Storage is NOT AVAILABLE")
        print()
        print("How to enable GDS:")
        print()
        print("1. Install NVIDIA GDS package:")
        print("   sudo apt-get update")
        print("   sudo apt-get install nvidia-gds")
        print()
        print("2. Load the nvidia-fs kernel module:")
        print("   sudo modprobe nvidia-fs")
        print()
        print("3. Verify installation:")
        print("   cat /proc/driver/nvidia-fs/version")
        print()
        print("4. Make module load on boot (optional):")
        print("   echo 'nvidia-fs' | sudo tee /etc/modules-load.d/nvidia-fs.conf")
        print()
        print("Note: You can still use fastsafetensors without GDS:")
        print("  model:")
        print("    use_fastsafetensors: true")
        print("    use_gpu_direct: false")
        print()
        print("This will be faster than standard safetensors, just not as fast as with GDS.")

    print()
    print("=" * 70)

    # Check fastsafetensors library
    print()
    if FASTSAFETENSORS_AVAILABLE:
        print_fastsafetensors_status()
    else:
        print("fastsafetensors library: NOT INSTALLED")
        print("  Install with: pip install fastsafetensors")

    print()


if __name__ == '__main__':
    main()
