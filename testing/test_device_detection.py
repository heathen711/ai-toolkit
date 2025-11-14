"""
Test script for device detection utilities.
Tests unified memory GPU detection and device information display.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import torch
from toolkit.device_utils import (
    is_unified_memory_gpu,
    get_device_memory_gb,
    get_device_name,
    print_device_info,
    should_use_low_vram
)


def main():
    print("=" * 60)
    print("Device Detection Test")
    print("=" * 60)
    print()

    # Check CUDA availability
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("No CUDA devices found. Exiting.")
        return

    print(f"CUDA Device Count: {torch.cuda.device_count()}")
    print()

    # Test each CUDA device
    for i in range(torch.cuda.device_count()):
        print(f"\n--- Device {i} ---")

        # Get basic info
        device_name = get_device_name(i)
        print(f"Device Name: {device_name}")

        # Check if unified memory
        is_unified = is_unified_memory_gpu(i)
        print(f"Unified Memory: {is_unified}")

        # Get memory info
        memory_gb = get_device_memory_gb(i)
        print(f"Available Memory: {memory_gb:.2f} GB")

        # Check low_vram recommendation
        should_low_vram = should_use_low_vram(i)
        print(f"Recommend low_vram: {should_low_vram}")

        # Try to get raw device properties
        try:
            props = torch.cuda.get_device_properties(i)
            print(f"\nRaw Device Properties:")
            print(f"  Name: {props.name}")
            print(f"  Total Memory: {props.total_memory / (1024**3):.2f} GB")
            print(f"  Multi Processor Count: {props.multi_processor_count}")
            print(f"  Compute Capability: {props.major}.{props.minor}")
        except Exception as e:
            print(f"Could not get raw properties: {e}")

    print("\n" + "=" * 60)
    print("Full Device Info:")
    print("=" * 60)
    print_device_info()

    # Test with different memory thresholds
    print("\n" + "=" * 60)
    print("Low VRAM Recommendations at Different Thresholds:")
    print("=" * 60)
    for threshold in [16, 24, 32, 48]:
        result = should_use_low_vram(memory_threshold_gb=threshold)
        print(f"Threshold {threshold}GB: low_vram = {result}")


if __name__ == "__main__":
    main()
