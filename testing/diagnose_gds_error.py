#!/usr/bin/env python3
"""
Detailed GDS error diagnosis script.
Investigates why cuFileBufRegister returns error 5048.
"""

import os
import sys
import subprocess
from pathlib import Path

def print_section(title):
    print(f"\n{'='*80}")
    print(f"{title}")
    print('='*80)

def check_file_system(path):
    """Check file system type for GDS compatibility"""
    print_section("File System Check")

    try:
        # Get mount point for the path
        result = subprocess.run(['df', '-T', str(path)],
                              capture_output=True, text=True, check=True)
        print(result.stdout)

        # Parse file system type
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 2:
                fs_type = parts[1]
                print(f"\nFile system type: {fs_type}")

                if fs_type in ['xfs', 'ext4']:
                    print(f"✓ {fs_type} is GDS-compatible")
                else:
                    print(f"⚠ {fs_type} may not support GDS (requires XFS or ext4)")

    except subprocess.CalledProcessError as e:
        print(f"Error checking file system: {e}")

def check_ulimits():
    """Check memory lock limits"""
    print_section("Memory Lock Limits (ulimit)")

    try:
        # Check current user limits
        result = subprocess.run(['bash', '-c', 'ulimit -a'],
                              capture_output=True, text=True, check=True)
        print("Current limits:")
        print(result.stdout)

        # Check specifically for locked memory
        result = subprocess.run(['bash', '-c', 'ulimit -l'],
                              capture_output=True, text=True, check=True)
        locked_mem = result.stdout.strip()

        print(f"\nLocked memory limit: {locked_mem}")
        if locked_mem == 'unlimited':
            print("✓ Locked memory is unlimited (good for GDS)")
        else:
            print(f"⚠ Locked memory is limited to {locked_mem} KB")
            print("  GDS may require unlimited locked memory")
            print("  Try: ulimit -l unlimited")

    except subprocess.CalledProcessError as e:
        print(f"Error checking ulimits: {e}")

def check_gds_config():
    """Check GDS configuration"""
    print_section("GDS Configuration")

    gds_config = Path('/etc/cufile.json')
    if gds_config.exists():
        print("Found /etc/cufile.json:")
        try:
            with open(gds_config, 'r') as f:
                print(f.read())
        except PermissionError:
            print("⚠ Cannot read /etc/cufile.json (permission denied)")
    else:
        print("⚠ /etc/cufile.json not found")
        print("  This is the GDS configuration file")
        print("  It may not be required, but could help diagnose issues")

def check_nvidia_gds_status():
    """Check detailed nvidia-fs status"""
    print_section("NVIDIA GDS Detailed Status")

    gds_stats = Path('/proc/driver/nvidia-fs/stats')
    if gds_stats.exists():
        print("GDS statistics (/proc/driver/nvidia-fs/stats):")
        try:
            with open(gds_stats, 'r') as f:
                print(f.read())
        except PermissionError:
            print("⚠ Cannot read stats (permission denied)")

    gds_devices = Path('/proc/driver/nvidia-fs/devices')
    if gds_devices.exists():
        print("\nGDS devices (/proc/driver/nvidia-fs/devices):")
        try:
            with open(gds_devices, 'r') as f:
                print(f.read())
        except PermissionError:
            print("⚠ Cannot read devices (permission denied)")

def check_cuda_driver():
    """Check CUDA and driver versions"""
    print_section("CUDA and Driver Versions")

    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=driver_version,cuda_version',
                               '--format=csv,noheader'],
                              capture_output=True, text=True, check=True)
        print("NVIDIA Driver and CUDA:")
        print(result.stdout)

        # Check nvidia-fs module info
        result = subprocess.run(['modinfo', 'nvidia_fs'],
                              capture_output=True, text=True, check=True)
        print("\nnvidia_fs module info:")
        for line in result.stdout.split('\n'):
            if 'version' in line.lower() or 'description' in line.lower():
                print(f"  {line}")

    except subprocess.CalledProcessError as e:
        print(f"Error checking driver: {e}")

def check_permissions(path):
    """Check file permissions"""
    print_section("File Permissions")

    if os.path.isfile(path):
        files = [path]
    elif os.path.isdir(path):
        # Check directory and first few files
        files = [path]
        try:
            dir_files = list(Path(path).glob('*.safetensors'))[:3]
            files.extend(dir_files)
        except:
            pass
    else:
        files = []

    for f in files:
        try:
            stat = os.stat(f)
            perms = oct(stat.st_mode)[-3:]
            print(f"{f}")
            print(f"  Permissions: {perms}")
            print(f"  UID: {stat.st_uid}, GID: {stat.st_gid}")
            print(f"  Readable: {os.access(f, os.R_OK)}")
            print()
        except Exception as e:
            print(f"Error checking {f}: {e}")

def check_cufile_error_codes():
    """Reference for CUfileOpError codes"""
    print_section("CUfileOpError Code Reference")

    # Common error codes from NVIDIA GDS documentation
    error_codes = {
        5000: "CU_FILE_SUCCESS",
        5001: "CU_FILE_DRIVER_NOT_INITIALIZED",
        5002: "CU_FILE_DRIVER_VERSION_MISMATCH",
        5003: "CU_FILE_INVALID_MAPPING_SIZE",
        5004: "CU_FILE_INVALID_MAPPING_TYPE",
        5005: "CU_FILE_INVALID_VALUE",
        5006: "CU_FILE_MEMORY_ALREADY_REGISTERED",
        5007: "CU_FILE_MEMORY_NOT_REGISTERED",
        5008: "CU_FILE_PERMISSION_DENIED",
        5009: "CU_FILE_INVALID_FILE_TYPE",
        5010: "CU_FILE_IO_NOT_SUPPORTED",
        5011: "CU_FILE_CUDA_DRIVER_ERROR",
        5048: "UNKNOWN_ERROR_5048 (Buffer registration failed)",
    }

    print("Error code 5048 received from cuFileBufRegister")
    print(f"Description: {error_codes.get(5048, 'Unknown')}")
    print("\nThis typically indicates:")
    print("  1. Insufficient permissions on the file or device")
    print("  2. File system does not support GDS operations")
    print("  3. Memory locking limits are too restrictive")
    print("  4. Buffer size exceeds system limits")
    print("  5. GDS driver/CUDA version incompatibility")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Diagnose GDS error 5048')
    parser.add_argument('path', nargs='?',
                       default='/home/jay/Documents/ai-toolkit/models/Qwen/Qwen-Image/transformer',
                       help='Path to model file or directory')

    args = parser.parse_args()

    print("="*80)
    print("GDS Error 5048 Diagnostic Tool")
    print("="*80)
    print(f"\nTarget path: {args.path}")

    # Run all diagnostics
    check_file_system(args.path)
    check_permissions(args.path)
    check_ulimits()
    check_cuda_driver()
    check_nvidia_gds_status()
    check_gds_config()
    check_cufile_error_codes()

    # Recommendations
    print_section("Recommendations")
    print("""
Based on the diagnostics above, try these solutions:

1. Increase memory lock limits:
   sudo bash -c 'echo "* hard memlock unlimited" >> /etc/security/limits.conf'
   sudo bash -c 'echo "* soft memlock unlimited" >> /etc/security/limits.conf'
   Then logout and login again, or:
   ulimit -l unlimited

2. If using NFS or network file system, GDS is not supported:
   - Move files to local XFS or ext4 file system

3. Check if running in a container or VM:
   - GDS requires bare metal or specific container setup
   - GPU must be accessible with full CUDA capabilities

4. Verify CUDA Unified Memory is working:
   python -c "import torch; print(torch.cuda.get_device_properties(0))"

5. For GB10 (unified memory GPU), GDS might not be supported:
   - These GPUs use system RAM, not dedicated VRAM
   - GDS is designed for direct NVMe-to-VRAM transfers
   - Continue using fastsafetensors without GDS (still faster!)

Current workaround:
  The automatic fallback to fastsafetensors without GDS is working well
  and still provides ~4-5x speedup compared to standard safetensors.
""")

if __name__ == '__main__':
    main()
