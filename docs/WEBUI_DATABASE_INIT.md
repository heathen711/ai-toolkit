# Web UI Database Initialization

## Issue

The web UI was showing `500 Internal Server Error` when accessing `/api/jobs`:
```
Failed to save job. Please try again.
XHR GET http://spark2.server:8675/api/jobs [HTTP/1.1 500 Internal Server Error]
```

## Root Cause

The SQLite database file (`aitk_db.db`) existed but was **empty (0 bytes)**. Prisma was trying to query tables that didn't exist, causing the API to crash.

## Solution

Initialize the database schema using Prisma:

```bash
cd /home/jay/Documents/ai-toolkit/ui
npx prisma db push
```

This creates the required tables:
- `Settings` - Application settings
- `Queue` - GPU queue management
- `Job` - Training job configuration and status

## Prevention

Updated `start-webui.sh` to automatically check and initialize the database if needed:

```bash
# Check and initialize database if needed
DB_FILE="$TOOLKIT_DIR/aitk_db.db"
if [ ! -f "$DB_FILE" ] || [ ! -s "$DB_FILE" ]; then
    log "Database not initialized, running Prisma db push..."
    npx prisma db push
fi
```

The `-s` flag checks if the file is non-empty (size > 0).

## Database Schema

Located at: `ui/prisma/schema.prisma`

```prisma
model Job {
  id              String   @id @default(uuid())
  name            String   @unique
  gpu_ids         String
  job_config      String   // JSON string
  created_at      DateTime @default(now())
  updated_at      DateTime @updatedAt
  status          String   @default("stopped")
  stop            Boolean  @default(false)
  return_to_queue Boolean  @default(false)
  step            Int      @default(0)
  info            String   @default("")
  speed_string    String   @default("")
  queue_position  Int      @default(0)
}
```

## Verification

After initialization, the database should be ~48KB:

```bash
ls -lh /home/jay/Documents/ai-toolkit/aitk_db.db
# -rw-r--r-- 1 jay jay 48K Nov 14 16:20 aitk_db.db
```

## Related Files

- `ui/prisma/schema.prisma` - Database schema definition
- `ui/src/app/api/jobs/route.ts` - Jobs API endpoint
- `start-webui.sh` - Startup script with auto-initialization

---

**Created:** 2025-11-14
**Issue:** 500 error on /api/jobs endpoint
**Status:** ✅ Fixed - Database initialized and auto-init added to startup script
