# AI Toolkit Web UI System Service

This directory contains configuration files to run the AI Toolkit Web UI as a systemd service that automatically starts on boot and restarts on crashes.

## 📁 Files

| File | Purpose |
|------|---------|
| `ai-toolkit-webui.service` | Systemd service configuration |
| `start-webui.sh` | Startup script for the web UI |
| `manage-webui-service.sh` | Service management utility |
| `WEBUI_SERVICE.md` | This documentation |

## 🚀 Quick Start

### 1. Test Configuration
```bash
./manage-webui-service.sh test
```

This verifies:
- ✓ Service files exist
- ✓ Virtual environment is set up
- ✓ UI directory exists
- ✓ Scripts are executable

### 2. Install Service
```bash
./manage-webui-service.sh install
```

This will:
1. Copy service file to `/etc/systemd/system/`
2. Reload systemd daemon
3. Enable service to start on boot

### 3. Start Service
```bash
./manage-webui-service.sh start
```

The Web UI will be available at: **http://localhost:8675**

## 🎮 Service Management Commands

### Basic Operations
```bash
# Start the service
./manage-webui-service.sh start

# Stop the service
./manage-webui-service.sh stop

# Restart the service
./manage-webui-service.sh restart

# Check service status
./manage-webui-service.sh status
```

### Monitoring
```bash
# Show last 50 lines of logs
./manage-webui-service.sh logs

# Show last 100 lines of logs
./manage-webui-service.sh logs 100

# Follow logs in real-time (Ctrl+C to exit)
./manage-webui-service.sh follow
```

### Maintenance
```bash
# Test configuration
./manage-webui-service.sh test

# Reinstall service
./manage-webui-service.sh uninstall
./manage-webui-service.sh install

# Uninstall service
./manage-webui-service.sh uninstall
```

## 🔧 Direct systemctl Commands

You can also use systemctl directly:

```bash
# Start/stop/restart
sudo systemctl start ai-toolkit-webui
sudo systemctl stop ai-toolkit-webui
sudo systemctl restart ai-toolkit-webui

# Enable/disable auto-start on boot
sudo systemctl enable ai-toolkit-webui
sudo systemctl disable ai-toolkit-webui

# Check status
sudo systemctl status ai-toolkit-webui

# View logs
sudo journalctl -u ai-toolkit-webui -f
sudo journalctl -u ai-toolkit-webui -n 100
sudo journalctl -u ai-toolkit-webui --since "1 hour ago"
```

## ⚙️ Service Configuration

### Service Details

- **Name:** `ai-toolkit-webui`
- **Type:** Simple service
- **User:** jay
- **Working Directory:** `/home/jay/Documents/ai-toolkit/ui`
- **Port:** 8675
- **Auto-start:** Yes (after installation)

### Restart Policy

The service is configured to automatically restart on failure:

- **Restart:** Always
- **Restart Delay:** 10 seconds
- **Max Restarts:** 5 attempts within 5 minutes
- **Behavior:** If the service crashes, it will automatically restart after 10 seconds

### Resource Limits

Default limits (can be adjusted in service file):

- **Memory:** 4GB maximum
- **CPU:** 200% (2 cores maximum)

### Security Features

The service includes security hardening:

- ✓ No privilege escalation
- ✓ Private /tmp directory
- ✓ Protected system files
- ✓ Read-only home directory (except ai-toolkit folder)
- ✓ CUDA device access allowed

## 🔍 Troubleshooting

### Service won't start

Check logs:
```bash
./manage-webui-service.sh logs 50
```

Common issues:
1. **Virtual environment missing** - Run `./setup_venv.sh`
2. **Port 8675 in use** - Stop other services using the port
3. **npm dependencies missing** - The startup script will install them automatically
4. **Permissions issue** - Check that `jay` user owns all files

### Service crashes immediately

Check the startup script logs:
```bash
tail -f webui.log
```

And system logs:
```bash
sudo journalctl -u ai-toolkit-webui -n 100
```

### View real-time logs

```bash
# Follow service logs
./manage-webui-service.sh follow

# Or directly
sudo journalctl -u ai-toolkit-webui -f
```

### Check service health

```bash
./manage-webui-service.sh status
```

Look for:
- **Active:** `active (running)` (green)
- **Loaded:** `enabled` (auto-starts on boot)
- **Main PID:** Should show a process ID

### Restart after crash

The service automatically restarts on crash. To verify:

```bash
# Kill the process (simulate crash)
sudo systemctl kill -s KILL ai-toolkit-webui

# Wait 10 seconds, then check status
sleep 10
./manage-webui-service.sh status
```

Should show the service running again with a new PID.

### Manual testing

Test the startup script manually:
```bash
./start-webui.sh
```

This runs the same script the service uses.

## 📝 Startup Script Details

The `start-webui.sh` script:

1. **Activates virtual environment** from `/home/jay/Documents/ai-toolkit/venv`
2. **Loads environment variables** from `.env` file
3. **Checks npm dependencies** - installs if missing
4. **Builds Next.js app** - builds if `.next` folder missing
5. **Starts the server** on port 8675
6. **Logs everything** to `webui.log`

## 🌐 Web UI Access

### Local Access
```
http://localhost:8675
```

### Remote Access

If accessing from another machine:
```
http://<server-ip>:8675
```

**Security Note:** For production/remote deployments, use authentication:

```bash
# Set authentication token
export AI_TOOLKIT_AUTH=your_secure_password

# Restart service
./manage-webui-service.sh restart
```

Or add to `.env`:
```
AI_TOOLKIT_AUTH=your_secure_password
```

## 🔐 Environment Variables

The service loads environment from:
1. Service file `Environment=` directives
2. `.env` file in the ai-toolkit root directory

### Available Variables

From `.env`:
```bash
# HuggingFace token
HF_TOKEN=your_token_here

# Web UI authentication (optional)
AI_TOOLKIT_AUTH=your_password

# Node environment
NODE_ENV=production
```

## 🛠️ Customization

### Modify Service Configuration

1. Edit the service file:
   ```bash
   nano ai-toolkit-webui.service
   ```

2. Reinstall:
   ```bash
   ./manage-webui-service.sh uninstall
   ./manage-webui-service.sh install
   ```

3. Restart:
   ```bash
   ./manage-webui-service.sh restart
   ```

### Common Modifications

**Change port** (edit `start-webui.sh`):
```bash
# Add before npm start:
export PORT=8080
```

**Increase memory limit** (edit `ai-toolkit-webui.service`):
```ini
MemoryMax=8G
```

**Change restart delay** (edit `ai-toolkit-webui.service`):
```ini
RestartSec=5  # Restart after 5 seconds instead of 10
```

**Disable auto-restart** (edit `ai-toolkit-webui.service`):
```ini
Restart=no  # Don't restart on failure
```

## 📊 Monitoring

### Check if service is running
```bash
systemctl is-active ai-toolkit-webui
```

Returns: `active` or `inactive`

### Check if enabled on boot
```bash
systemctl is-enabled ai-toolkit-webui
```

Returns: `enabled` or `disabled`

### View recent crashes
```bash
sudo journalctl -u ai-toolkit-webui | grep -i "failed\|error\|crash"
```

### Monitor system resources
```bash
# CPU and memory usage
systemctl status ai-toolkit-webui

# Detailed resource usage
systemd-cgtop -1 | grep ai-toolkit-webui
```

## 🔄 Updates and Maintenance

### Update AI Toolkit code

```bash
# Pull latest changes
cd /home/jay/Documents/ai-toolkit
git pull

# Rebuild UI
cd ui
npm run build

# Restart service
cd ..
./manage-webui-service.sh restart
```

### Update Python dependencies

```bash
# Recreate venv
./quick_rebuild_venv.sh

# Restart service
./manage-webui-service.sh restart
```

### Update Node dependencies

```bash
# Update packages
cd ui
npm update

# Rebuild
npm run build

# Restart service
cd ..
./manage-webui-service.sh restart
```

## 🐛 Debug Mode

To run the service in debug mode:

1. Stop the service:
   ```bash
   ./manage-webui-service.sh stop
   ```

2. Run manually:
   ```bash
   ./start-webui.sh
   ```

3. Check `webui.log` for detailed logs

4. When done, restart service:
   ```bash
   ./manage-webui-service.sh start
   ```

## 📱 Integration with Other Services

### Start training when UI starts

Edit `start-webui.sh` to add custom initialization:
```bash
# Before 'exec npm start', add:
log "Running custom initialization..."
# Your custom commands here
```

### Notifications on crashes

Add a notification service (edit `ai-toolkit-webui.service`):
```ini
OnFailure=notify-admin@%n.service
```

## 💡 Best Practices

1. **Always test before installing:**
   ```bash
   ./manage-webui-service.sh test
   ```

2. **Monitor logs after changes:**
   ```bash
   ./manage-webui-service.sh follow
   ```

3. **Keep backups of service file:**
   ```bash
   cp ai-toolkit-webui.service ai-toolkit-webui.service.backup
   ```

4. **Use authentication for remote access:**
   ```bash
   echo "AI_TOOLKIT_AUTH=secure_password" >> .env
   ```

5. **Check service health regularly:**
   ```bash
   ./manage-webui-service.sh status
   ```

## 📚 Additional Resources

- **Systemd Documentation:** `man systemd.service`
- **Journalctl Guide:** `man journalctl`
- **AI Toolkit Docs:** `CLAUDE.md`
- **Setup Scripts:** `SETUP_SCRIPTS.md`

## 🆘 Getting Help

If you encounter issues:

1. Check service status:
   ```bash
   ./manage-webui-service.sh status
   ```

2. View recent logs:
   ```bash
   ./manage-webui-service.sh logs 100
   ```

3. Test configuration:
   ```bash
   ./manage-webui-service.sh test
   ```

4. Check `webui.log` in the ai-toolkit directory

5. Run startup script manually for debugging:
   ```bash
   ./start-webui.sh
   ```

---

**Created:** 2025-11-14
**Service:** ai-toolkit-webui
**Port:** 8675
**URL:** http://localhost:8675
