# AI Toolkit Web UI - Troubleshooting Guide

## Common Issues and Solutions

### Issue: Service fails with "tsc: not found" error

**Symptoms:**
```
sh: 1: tsc: not found
ai-toolkit-webui.service: Main process exited, code=exited, status=127/n/a
ai-toolkit-webui.service: Failed with result 'exit-code'.
```

**Cause:**
The `node_modules` directory is corrupted or incomplete, missing the TypeScript compiler binary.

**Solutions:**

#### Quick Fix (Automatic)
The updated `start-webui.sh` now automatically detects and fixes this issue. Just restart the service:

```bash
./manage-webui-service.sh restart
```

The service will automatically:
1. Detect corrupted node_modules
2. Remove it
3. Run fresh npm install
4. Continue with startup

#### Manual Fix
If automatic fix doesn't work:

```bash
# Use the fix script
./fix-ui-dependencies.sh

# Or manually:
cd ui
rm -rf node_modules
npm install
cd ..
./manage-webui-service.sh restart
```

#### Verify Fix
```bash
# Check that binaries exist
ls -la ui/node_modules/.bin/ | grep -E "tsc|next"

# Should show:
# tsc
# next

# Check service status
./manage-webui-service.sh status
```

---

### Issue: Service keeps restarting

**Symptoms:**
```
ai-toolkit-webui.service: Scheduled restart job, restart counter is at 2.
ai-toolkit-webui.service: Scheduled restart job, restart counter is at 3.
```

**Cause:**
Service is crashing and systemd is auto-restarting it (up to 5 times in 5 minutes).

**Solutions:**

1. **Check logs for actual error:**
   ```bash
   ./manage-webui-service.sh logs 100
   ```

2. **Common causes:**
   - Port 8675 already in use
   - Missing dependencies
   - Corrupted node_modules (see above)
   - Build failure

3. **Test manually:**
   ```bash
   ./manage-webui-service.sh stop
   ./start-webui.sh
   # Watch for errors
   ```

---

### Issue: npm install fails during service start

**Symptoms:**
```
[ERROR] npm install failed
ai-toolkit-webui.service: Failed with result 'exit-code'.
```

**Solutions:**

1. **Check internet connection:**
   ```bash
   ping registry.npmjs.org
   ```

2. **Clear npm cache:**
   ```bash
   cd ui
   npm cache clean --force
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Check disk space:**
   ```bash
   df -h .
   ```

4. **Check permissions:**
   ```bash
   ls -la ui/
   # Should be owned by 'jay'
   # If not:
   sudo chown -R jay:jay ui/
   ```

---

### Issue: Build fails with TypeScript errors

**Symptoms:**
```
> tsc -p tsconfig.worker.json && next build
Type error: ...
ai-toolkit-webui.service: Failed with result 'exit-code'.
```

**Solutions:**

1. **Update dependencies:**
   ```bash
   cd ui
   npm update
   cd ..
   ./manage-webui-service.sh restart
   ```

2. **Fresh install:**
   ```bash
   ./fix-ui-dependencies.sh
   ./manage-webui-service.sh restart
   ```

3. **Check TypeScript version:**
   ```bash
   cd ui
   npm list typescript
   ```

---

### Issue: Port 8675 already in use

**Symptoms:**
```
Error: listen EADDRINUSE: address already in use :::8675
```

**Solutions:**

1. **Find what's using the port:**
   ```bash
   sudo lsof -i :8675
   ```

2. **Kill the process:**
   ```bash
   # Get PID from lsof output
   kill -9 <PID>
   ```

3. **Change port (edit start-webui.sh):**
   ```bash
   nano start-webui.sh
   # Add before 'exec npm start':
   export PORT=8080
   ```

---

### Issue: Service doesn't start on boot

**Symptoms:**
After reboot, service is not running.

**Solutions:**

1. **Check if service is enabled:**
   ```bash
   systemctl is-enabled ai-toolkit-webui
   # Should show: enabled
   ```

2. **Enable the service:**
   ```bash
   sudo systemctl enable ai-toolkit-webui
   ```

3. **Check for startup errors:**
   ```bash
   sudo journalctl -b -u ai-toolkit-webui
   # -b shows logs since last boot
   ```

---

### Issue: Cannot access Web UI from browser

**Symptoms:**
Service is running but http://localhost:8675 doesn't load.

**Solutions:**

1. **Verify service is actually running:**
   ```bash
   ./manage-webui-service.sh status
   # Should show: active (running)
   ```

2. **Check if port is listening:**
   ```bash
   sudo netstat -tlnp | grep 8675
   # Should show: LISTEN
   ```

3. **Check firewall:**
   ```bash
   sudo ufw status
   # If active and port blocked:
   sudo ufw allow 8675/tcp
   ```

4. **Test with curl:**
   ```bash
   curl http://localhost:8675
   # Should return HTML
   ```

5. **Check browser console for errors**

---

### Issue: Service takes too long to start

**Symptoms:**
Service shows "starting" for a long time.

**Causes:**
- First time build (can take 2-5 minutes)
- Slow npm install
- Compiling TypeScript

**Solutions:**

1. **Watch build progress:**
   ```bash
   ./manage-webui-service.sh follow
   ```

2. **Pre-build manually:**
   ```bash
   cd ui
   npm install
   npm run build
   cd ..
   ./manage-webui-service.sh start
   ```

3. **Increase timeout (edit ai-toolkit-webui.service):**
   ```ini
   TimeoutStartSec=600  # 10 minutes instead of default
   ```

---

### Issue: Logs show "[WARN] Some warning"

**Common warnings that are safe to ignore:**

- `npm warn deprecated` - Old package versions (usually safe)
- `1 critical severity vulnerability` - Check with `npm audit` but often false positives
- `GPU device discovery failed` - ONNX runtime warning, doesn't affect operation

**When to worry:**

- `ERROR` messages
- `FATAL` errors
- `ECONNREFUSED` - Can't connect to services
- `EACCES` - Permission denied

---

### Issue: Service stops after manual code changes

**Expected behavior:**
Service runs a built version, not development mode.

**Solutions:**

1. **For development, run manually:**
   ```bash
   ./manage-webui-service.sh stop
   cd ui
   npm run dev  # Development mode with hot reload
   ```

2. **After code changes, rebuild:**
   ```bash
   cd ui
   npm run build
   cd ..
   ./manage-webui-service.sh restart
   ```

3. **Auto-rebuild script (create rebuild-and-restart.sh):**
   ```bash
   #!/bin/bash
   cd ui
   npm run build
   cd ..
   ./manage-webui-service.sh restart
   ./manage-webui-service.sh follow
   ```

---

## Debugging Workflow

### Step 1: Check Service Status
```bash
./manage-webui-service.sh status
```

### Step 2: View Recent Logs
```bash
./manage-webui-service.sh logs 50
```

### Step 3: Check for Common Issues
```bash
# Dependencies OK?
ls -la ui/node_modules/.bin/ | grep -E "tsc|next"

# Build exists?
ls -la ui/.next/

# Port available?
sudo lsof -i :8675

# Disk space?
df -h .

# Permissions OK?
ls -la ui/
```

### Step 4: Test Manually
```bash
./manage-webui-service.sh stop
./start-webui.sh
# Watch output for errors
```

### Step 5: Fix and Restart
```bash
# Fix dependencies if needed
./fix-ui-dependencies.sh

# Restart service
./manage-webui-service.sh restart

# Watch for startup success
./manage-webui-service.sh follow
```

---

## Useful Commands Reference

### Service Management
```bash
./manage-webui-service.sh start       # Start service
./manage-webui-service.sh stop        # Stop service
./manage-webui-service.sh restart     # Restart service
./manage-webui-service.sh status      # Check status
./manage-webui-service.sh logs 100    # Last 100 lines
./manage-webui-service.sh follow      # Live logs
./manage-webui-service.sh test        # Test configuration
```

### Dependency Fixes
```bash
./fix-ui-dependencies.sh              # Fix corrupted node_modules
cd ui && npm install && cd ..         # Manual install
cd ui && rm -rf node_modules && npm install && cd ..  # Fresh install
```

### Systemctl Direct Commands
```bash
sudo systemctl status ai-toolkit-webui
sudo systemctl restart ai-toolkit-webui
sudo systemctl stop ai-toolkit-webui
sudo systemctl start ai-toolkit-webui
sudo journalctl -u ai-toolkit-webui -f
sudo journalctl -u ai-toolkit-webui -n 100
```

### Port Checking
```bash
sudo lsof -i :8675                    # What's using port 8675?
sudo netstat -tlnp | grep 8675        # Is port listening?
curl http://localhost:8675            # Test connection
```

### Log Files
```bash
tail -f webui.log                     # Local log file
sudo journalctl -u ai-toolkit-webui -f # System journal
sudo journalctl -u ai-toolkit-webui --since "1 hour ago"
sudo journalctl -u ai-toolkit-webui | grep -i error
```

---

## Getting Additional Help

If issues persist:

1. **Gather information:**
   ```bash
   ./manage-webui-service.sh status > debug-info.txt
   ./manage-webui-service.sh logs 200 >> debug-info.txt
   cat webui.log >> debug-info.txt
   npm list > ui-packages.txt
   ```

2. **Check documentation:**
   - `WEBUI_SERVICE.md` - Full documentation
   - `WEBUI_SERVICE_QUICKREF.md` - Quick reference
   - `SETUP_SCRIPTS.md` - Setup guide

3. **Common fix workflow:**
   ```bash
   # Try this sequence:
   ./manage-webui-service.sh stop
   ./fix-ui-dependencies.sh
   ./manage-webui-service.sh start
   ./manage-webui-service.sh follow
   ```

---

**Last Updated:** 2025-11-14
**Issue Covered:** tsc not found, corrupted node_modules, service crashes
