# AI Toolkit Web UI Service - Quick Reference

## 🚀 Installation (First Time)

```bash
# 1. Test configuration
./manage-webui-service.sh test

# 2. Install service
./manage-webui-service.sh install

# 3. Start service
./manage-webui-service.sh start

# Access at: http://localhost:8675
```

## 📋 Common Commands

```bash
# Service control
./manage-webui-service.sh start      # Start service
./manage-webui-service.sh stop       # Stop service
./manage-webui-service.sh restart    # Restart service
./manage-webui-service.sh status     # Check status

# Logs
./manage-webui-service.sh logs       # Show last 50 lines
./manage-webui-service.sh logs 100   # Show last 100 lines
./manage-webui-service.sh follow     # Watch logs live

# Maintenance
./manage-webui-service.sh test       # Test configuration
./manage-webui-service.sh uninstall  # Remove service
```

## 🔍 Troubleshooting

```bash
# Service won't start?
./manage-webui-service.sh logs 50

# Check what's wrong
./manage-webui-service.sh status

# Test manually
./start-webui.sh

# Check detailed logs
tail -f webui.log
sudo journalctl -u ai-toolkit-webui -n 100
```

## ⚡ Quick Checks

```bash
# Is it running?
systemctl is-active ai-toolkit-webui

# Will it start on boot?
systemctl is-enabled ai-toolkit-webui

# What's using port 8675?
sudo lsof -i :8675
```

## 🔄 After Updates

```bash
# After code update
git pull
cd ui && npm run build && cd ..
./manage-webui-service.sh restart

# After venv update
./quick_rebuild_venv.sh
./manage-webui-service.sh restart
```

## 🌐 URLs

- **Local:** http://localhost:8675
- **Remote:** http://YOUR_IP:8675

## 📝 Files

- Service: `/etc/systemd/system/ai-toolkit-webui.service`
- Startup: `/home/jay/Documents/ai-toolkit/start-webui.sh`
- Logs: `/home/jay/Documents/ai-toolkit/webui.log`
- Journal: `sudo journalctl -u ai-toolkit-webui`

## 💡 Pro Tips

```bash
# Watch logs + status in one command
watch -n 2 'systemctl status ai-toolkit-webui --no-pager'

# Search logs for errors
sudo journalctl -u ai-toolkit-webui | grep -i error

# Restart on code changes (during development)
sudo systemctl stop ai-toolkit-webui  # Stop service
./start-webui.sh  # Run manually for hot reload

# Auto-restart every hour (add to crontab if needed)
0 * * * * /usr/bin/systemctl restart ai-toolkit-webui
```

## 🆘 Emergency

```bash
# Service completely broken?
sudo systemctl stop ai-toolkit-webui
sudo systemctl disable ai-toolkit-webui
./manage-webui-service.sh uninstall

# Start fresh
./manage-webui-service.sh install
./manage-webui-service.sh start
```

---
**Full docs:** `WEBUI_SERVICE.md`
