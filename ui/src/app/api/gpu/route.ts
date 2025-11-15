import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import os from 'os';

const execAsync = promisify(exec);

export async function GET() {
  try {
    // Get platform
    const platform = os.platform();
    const isWindows = platform === 'win32';

    // Check if nvidia-smi is available
    const hasNvidiaSmi = await checkNvidiaSmi(isWindows);

    if (!hasNvidiaSmi) {
      return NextResponse.json({
        hasNvidiaSmi: false,
        gpus: [],
        error: 'nvidia-smi not found or not accessible',
      });
    }

    // Get GPU stats
    const gpuStats = await getGpuStats(isWindows);

    return NextResponse.json({
      hasNvidiaSmi: true,
      gpus: gpuStats,
    });
  } catch (error) {
    console.error('Error fetching NVIDIA GPU stats:', error);
    return NextResponse.json(
      {
        hasNvidiaSmi: false,
        gpus: [],
        error: `Failed to fetch GPU stats: ${error instanceof Error ? error.message : String(error)}`,
      },
      { status: 500 },
    );
  }
}

async function checkNvidiaSmi(isWindows: boolean): Promise<boolean> {
  try {
    if (isWindows) {
      // Check if nvidia-smi is available on Windows
      // It's typically located in C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe
      // but we'll just try to run it directly as it may be in PATH
      await execAsync('nvidia-smi -L');
    } else {
      // Linux/macOS check
      await execAsync('which nvidia-smi');
    }
    return true;
  } catch (error) {
    return false;
  }
}

async function getGpuStats(isWindows: boolean) {
  // Command is the same for both platforms, but the path might be different
  const command =
    'nvidia-smi --query-gpu=index,name,driver_version,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used,power.draw,power.limit,clocks.current.graphics,clocks.current.memory,fan.speed --format=csv,noheader,nounits';

  // Execute command
  const { stdout } = await execAsync(command, {
    env: { ...process.env, CUDA_DEVICE_ORDER: 'PCI_BUS_ID' },
  });

  // Parse CSV output
  const gpus = await Promise.all(
    stdout
      .trim()
      .split('\n')
      .map(async line => {
        const [
          index,
          name,
          driverVersion,
          temperature,
          gpuUtil,
          memoryUtil,
          memoryTotal,
          memoryFree,
          memoryUsed,
          powerDraw,
          powerLimit,
          clockGraphics,
          clockMemory,
          fanSpeed,
        ] = line.split(', ').map(item => item.trim());

        let memTotal = parseInt(memoryTotal);
        let memFree = parseInt(memoryFree);
        let memUsed = parseInt(memoryUsed);
        let memUtil = parseInt(memoryUtil);

        // Check if memory values are NaN (unified memory GPU case)
        // nvidia-smi returns "[Not Supported]" which becomes NaN when parsed
        if (isNaN(memTotal) || isNaN(memUsed) || memTotal === 0) {
          // Fall back to Python script to get accurate unified memory stats
          try {
            const pythonMemInfo = await getUnifiedMemoryInfo(parseInt(index));
            if (pythonMemInfo) {
              memTotal = pythonMemInfo.total_mb;
              memFree = pythonMemInfo.free_mb;
              memUsed = pythonMemInfo.used_mb;
              // Calculate memory utilization percentage
              memUtil = memTotal > 0 ? Math.round((memUsed / memTotal) * 100) : 0;
            }
          } catch (error) {
            console.error(`Failed to get unified memory info for GPU ${index}:`, error);
            // Set to 0 if we can't get the info
            memTotal = 0;
            memFree = 0;
            memUsed = 0;
            memUtil = 0;
          }
        }

        return {
          index: parseInt(index),
          name,
          driverVersion,
          temperature: parseInt(temperature),
          utilization: {
            gpu: parseInt(gpuUtil) || 0,
            memory: memUtil || 0,
          },
          memory: {
            total: memTotal,
            free: memFree,
            used: memUsed,
          },
          power: {
            draw: parseFloat(powerDraw),
            limit: parseFloat(powerLimit),
          },
          clocks: {
            graphics: parseInt(clockGraphics),
            memory: parseInt(clockMemory),
          },
          fan: {
            speed: parseInt(fanSpeed) || 0, // Some GPUs might not report fan speed, default to 0
          },
        };
      }),
  );

  return gpus;
}

async function getUnifiedMemoryInfo(gpuIndex: number): Promise<{
  total_mb: number;
  free_mb: number;
  used_mb: number;
  is_unified: boolean;
} | null> {
  try {
    // Call Python script to get accurate memory info for unified memory GPUs
    const scriptPath = `${process.cwd()}/get_gpu_memory.py`;
    const pythonCmd = `python3 ${scriptPath} ${gpuIndex}`;

    const { stdout } = await execAsync(pythonCmd);
    const result = JSON.parse(stdout.trim());

    if (result.is_unified && result.total_mb > 0) {
      return result;
    }
    return null;
  } catch (error) {
    console.error('Error getting unified memory info:', error);
    return null;
  }
}
