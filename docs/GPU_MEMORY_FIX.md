# GPU Memory Display Fix for Unified Memory GPUs

## Issue

The web UI was showing `Memory NaN% null MB / null MB` for the GB10 GPU because:
- nvidia-smi returns `[Not Supported]` for memory stats on unified memory GPUs
- When parsed as `parseInt()`, this becomes `NaN`
- The UI couldn't display these NaN values

## Solution

Created a fallback system that detects unified memory GPUs and gets accurate memory info from `/proc/meminfo`:

### Files Modified/Created

1. **`ui/get_gpu_memory.py`** (NEW)
   - Python script that uses `toolkit.device_utils` to get accurate memory info
   - Detects unified memory GPUs (GB10, DGX Spark, Jetson)
   - Falls back to `/proc/meminfo` for system RAM usage
   - Returns JSON with memory stats in MB

2. **`ui/src/app/api/gpu/route.ts`** (MODIFIED)
   - Added `getUnifiedMemoryInfo()` function
   - Detects when nvidia-smi returns NaN for memory values
   - Calls Python script to get accurate unified memory stats
   - Replaces NaN values with real data

3. **`ui/src/components/GPUWidget.tsx`** (MODIFIED)
   - Added null checks to prevent division by zero
   - Shows 'N/A' when memory data unavailable
   - Prevents NaN% display

## How It Works

```
nvidia-smi → returns [Not Supported] → becomes NaN
    ↓
API detects NaN
    ↓
Calls get_gpu_memory.py
    ↓
Python reads /proc/meminfo
    ↓
Returns: {"is_unified": true, "total_mb": 122571, "used_mb": 9483, "free_mb": 113088}
    ↓
UI displays: Memory 7.7% 9.3 GB / 119.7 GB
```

## Testing

```bash
# Test the Python script directly
cd /home/jay/Documents/ai-toolkit
source venv/bin/activate
python3 ui/get_gpu_memory.py 0
```

Expected output for GB10:
```json
{"is_unified": true, "total_mb": 122571, "used_mb": 9483, "free_mb": 113088}
```

## Technical Details

### Unified Memory Detection

The script detects unified memory GPUs via:
1. `torch.cuda.get_device_properties().total_memory == 0`
2. GPU name matching (GB10, DGX SPARK, JETSON)

### Memory Source

For unified memory GPUs, reads `/proc/meminfo`:
- `MemTotal` → total_mb
- `MemAvailable` → free_mb
- `used_mb = total_mb - free_mb`

This is the same method used by `toolkit/device_utils.py` and recommended by NVIDIA DGX Spark documentation.

### Why `/proc/meminfo`?

From NVIDIA docs:
- `cudaMemGetInfo` underreports available memory (doesn't account for swap)
- nvidia-smi shows "Memory-Usage: Not Supported" for unified memory
- `/proc/meminfo` provides accurate system RAM statistics

## Benefits

1. **Accurate memory display** - Shows real system RAM usage for GB10
2. **Real-time monitoring** - Updates every refresh interval
3. **Graceful fallback** - Shows N/A if unable to get data
4. **No crashes** - Proper NaN handling prevents UI errors

## Related Files

- `toolkit/device_utils.py` - Core device utilities used by the script
- `CLAUDE.md` - Project documentation explaining unified memory architecture
- `docs/GB10_OPTIMIZATION_GUIDE.md` - GB10 optimization guide

---

**Created:** 2025-11-14
**GPU:** NVIDIA GB10 (119.7 GB unified memory)
**Issue:** Memory showing as NaN in web UI
**Status:** ✅ Fixed
