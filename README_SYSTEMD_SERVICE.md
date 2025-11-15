# AI Toolkit Web UI Systemd Service

Automatically run the AI Toolkit Web UI as a system service that starts on boot and restarts on crashes.

## 📦 What's Included

This package contains everything needed to run the Web UI as a systemd service:

### Core Files
- **`ai-toolkit-webui.service`** - Systemd service configuration
- **`start-webui.sh`** - Service startup script with logging
- **`manage-webui-service.sh`** - Comprehensive service management tool

### Documentation
- **`WEBUI_SERVICE.md`** - Complete documentation and troubleshooting guide
- **`WEBUI_SERVICE_QUICKREF.md`** - Quick reference for common commands
- **`README_SYSTEMD_SERVICE.md`** - This file

## 🎯 Features

✅ **Auto-start on boot** - Service starts automatically when system boots
✅ **Auto-restart on crash** - Restarts automatically if it crashes (max 5 times in 5 min)
✅ **Restart delay** - 10 second delay between restart attempts
✅ **Resource limits** - Memory (4GB) and CPU (200%) limits configured
✅ **Security hardening** - No privilege escalation, protected system files
✅ **CUDA support** - Access to NVIDIA GPU devices
✅ **Logging** - Full systemd journal integration + local log file
✅ **Management script** - Easy install/start/stop/logs commands

## 🚀 Quick Start

### 1. Install the Service

```bash
./manage-webui-service.sh test     # Verify configuration
./manage-webui-service.sh install  # Install service
./manage-webui-service.sh start    # Start service
```

### 2. Access the Web UI

Open in your browser:
```
http://localhost:8675
```

### 3. Check Status

```bash
./manage-webui-service.sh status
```

## 📖 Usage

### Service Management

```bash
# Basic operations
./manage-webui-service.sh start      # Start the service
./manage-webui-service.sh stop       # Stop the service
./manage-webui-service.sh restart    # Restart the service
./manage-webui-service.sh status     # Show service status

# Monitoring
./manage-webui-service.sh logs       # Show last 50 log lines
./manage-webui-service.sh logs 100   # Show last 100 log lines
./manage-webui-service.sh follow     # Watch logs in real-time (Ctrl+C to exit)

# Maintenance
./manage-webui-service.sh test       # Test configuration
./manage-webui-service.sh uninstall  # Uninstall service
./manage-webui-service.sh help       # Show help
```

### Direct Systemctl Commands

```bash
sudo systemctl start ai-toolkit-webui      # Start
sudo systemctl stop ai-toolkit-webui       # Stop
sudo systemctl restart ai-toolkit-webui    # Restart
sudo systemctl status ai-toolkit-webui     # Status
sudo systemctl enable ai-toolkit-webui     # Enable auto-start
sudo systemctl disable ai-toolkit-webui    # Disable auto-start

sudo journalctl -u ai-toolkit-webui -f     # Follow logs
sudo journalctl -u ai-toolkit-webui -n 50  # Last 50 lines
```

## 🔧 Configuration

### Service Configuration
Edit `ai-toolkit-webui.service` to customize:
- Memory limits (default: 4GB)
- CPU limits (default: 200% / 2 cores)
- Restart behavior (default: always, 10s delay)
- Security settings
- Environment variables

After editing, reinstall:
```bash
./manage-webui-service.sh uninstall
./manage-webui-service.sh install
./manage-webui-service.sh restart
```

### Startup Script
Edit `start-webui.sh` to customize:
- Logging behavior
- Build process
- Startup checks
- Environment setup

### Environment Variables
Add to `.env` file in ai-toolkit root:
```bash
# HuggingFace token
HF_TOKEN=your_token_here

# Web UI authentication (optional)
AI_TOOLKIT_AUTH=your_secure_password

# Custom Node environment
NODE_ENV=production
```

## 🔍 Monitoring & Logs

### View Logs

```bash
# Management script (recommended)
./manage-webui-service.sh logs 100    # Last 100 lines
./manage-webui-service.sh follow      # Live logs

# Local log file
tail -f webui.log

# Systemd journal
sudo journalctl -u ai-toolkit-webui -f
sudo journalctl -u ai-toolkit-webui --since "1 hour ago"
sudo journalctl -u ai-toolkit-webui | grep -i error
```

### Check Service Health

```bash
# Service status
./manage-webui-service.sh status

# Is it running?
systemctl is-active ai-toolkit-webui

# Will it auto-start?
systemctl is-enabled ai-toolkit-webui

# Resource usage
systemctl status ai-toolkit-webui --no-pager
```

## 🛠️ Troubleshooting

### Service Won't Start

1. **Check logs:**
   ```bash
   ./manage-webui-service.sh logs 50
   ```

2. **Test manually:**
   ```bash
   ./start-webui.sh
   ```

3. **Common issues:**
   - Virtual environment missing → Run `./setup_venv.sh`
   - Port 8675 in use → Check `sudo lsof -i :8675`
   - npm dependencies missing → Script installs automatically
   - Permission errors → Check file ownership: `ls -la`

### Service Crashes Immediately

```bash
# Check startup logs
tail -f webui.log

# Check system logs
sudo journalctl -u ai-toolkit-webui -n 100

# Test configuration
./manage-webui-service.sh test
```

### Cannot Access Web UI

```bash
# Is service running?
./manage-webui-service.sh status

# Is port open?
sudo lsof -i :8675

# Check firewall
sudo ufw status
sudo ufw allow 8675/tcp  # If needed
```

### Auto-Restart Not Working

Check service configuration:
```bash
# Should show: Restart=always
systemctl cat ai-toolkit-webui | grep Restart

# Check if max restarts exceeded
sudo journalctl -u ai-toolkit-webui | grep "Start request repeated"
```

## 🔄 Updates & Maintenance

### After Code Updates

```bash
git pull
cd ui && npm run build && cd ..
./manage-webui-service.sh restart
```

### After Python Package Updates

```bash
./quick_rebuild_venv.sh
./manage-webui-service.sh restart
```

### After Service File Changes

```bash
./manage-webui-service.sh uninstall
./manage-webui-service.sh install
./manage-webui-service.sh start
```

## 📊 Service Information

| Property | Value |
|----------|-------|
| **Service Name** | ai-toolkit-webui |
| **Service File** | /etc/systemd/system/ai-toolkit-webui.service |
| **Startup Script** | /home/jay/Documents/ai-toolkit/start-webui.sh |
| **Working Directory** | /home/jay/Documents/ai-toolkit/ui |
| **User** | jay |
| **Port** | 8675 |
| **Auto-start** | Yes (after enable) |
| **Restart** | Always (10s delay) |
| **Memory Limit** | 4GB |
| **CPU Limit** | 200% (2 cores) |

## 🔐 Security

The service includes security hardening:
- ✓ Runs as non-root user (`jay`)
- ✓ No privilege escalation allowed
- ✓ Private /tmp directory
- ✓ Protected system files (read-only)
- ✓ Read-only home directory (except ai-toolkit)
- ✓ CUDA device access permitted

### Enable Authentication

For remote/production access, enable authentication:

```bash
# Add to .env
echo "AI_TOOLKIT_AUTH=your_secure_password" >> .env

# Restart service
./manage-webui-service.sh restart
```

Access will require the password.

## 🌐 Remote Access

### Local Network Access

```
http://YOUR_IP:8675
```

### Firewall Configuration

```bash
# Allow port 8675
sudo ufw allow 8675/tcp

# Check status
sudo ufw status
```

### Reverse Proxy (Production)

For production, use nginx or Apache as reverse proxy with SSL:

```nginx
# Example nginx config
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8675;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📚 Documentation

- **Full Guide:** `WEBUI_SERVICE.md`
- **Quick Reference:** `WEBUI_SERVICE_QUICKREF.md`
- **Setup Scripts:** `SETUP_SCRIPTS.md`
- **Installation:** `INSTALLATION_SUMMARY.md`
- **Project Docs:** `CLAUDE.md`

## 🆘 Getting Help

### Check Configuration
```bash
./manage-webui-service.sh test
```

### View Recent Errors
```bash
./manage-webui-service.sh logs 100 | grep -i error
```

### Debug Mode
```bash
# Stop service
./manage-webui-service.sh stop

# Run manually to see output
./start-webui.sh

# When done, restart service
./manage-webui-service.sh start
```

## ✅ Verification

After installation, verify everything works:

```bash
# 1. Service is running
./manage-webui-service.sh status

# 2. Web UI is accessible
curl http://localhost:8675

# 3. Service will auto-start
systemctl is-enabled ai-toolkit-webui

# 4. Logs are clean
./manage-webui-service.sh logs 20
```

## 🎓 Examples

### Daily Operations

```bash
# Morning: Check if service is running
./manage-webui-service.sh status

# During work: Monitor for issues
./manage-webui-service.sh follow

# After code update: Restart
git pull && ./manage-webui-service.sh restart

# Evening: Check for errors during the day
./manage-webui-service.sh logs 100 | grep -i error
```

### Debugging Session

```bash
# Stop the service
./manage-webui-service.sh stop

# Run manually to see output
./start-webui.sh

# Make changes, test, repeat...

# When done, restart service
./manage-webui-service.sh start
./manage-webui-service.sh follow  # Watch for issues
```

### Scheduled Maintenance

```bash
# Add to crontab for weekly restart
0 3 * * 0 /home/jay/Documents/ai-toolkit/manage-webui-service.sh restart

# Monthly cleanup of old logs
0 0 1 * * sudo journalctl --vacuum-time=30d
```

## 🚨 Important Notes

1. **First-time setup**: Run `./setup_venv.sh` before installing service
2. **Port conflicts**: Ensure port 8675 is not in use
3. **Authentication**: Enable for remote/production access
4. **Updates**: Restart service after code or dependency updates
5. **Logs**: Check regularly for errors or warnings
6. **Testing**: Always test configuration before installing

---

## 🎉 Success!

If you see this when checking status:
```
● ai-toolkit-webui.service - AI Toolkit Web UI
   Loaded: loaded (/etc/systemd/system/ai-toolkit-webui.service; enabled)
   Active: active (running)
```

And you can access http://localhost:8675, you're all set! 🚀

---

**Created:** 2025-11-14
**Version:** 1.0
**Author:** AI Toolkit Setup Scripts
**License:** Same as AI Toolkit project
