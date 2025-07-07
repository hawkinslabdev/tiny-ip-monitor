# 🔐 Tiny IP Monitor

A lightweight, containerized VPN monitoring solution that automatically alerts you when your public IP address falls outside your VPN's expected range.

## Features

- **🎯 Simple Setup** - Single Docker container with web interface
- **⚡ Lightweight** - Alpine Linux based, minimal resource usage
- **🔔 Smart Alerts** - Webhook notifications to Home Assistant, Discord, Slack, or any HTTP endpoint
- **⏰ Flexible Scheduling** - Configurable CRON-based monitoring intervals
- **🌐 Web Dashboard** - Real-time status, logs, and manual testing
- **🔧 Zero Config** - Works out of the box with sensible defaults
- **📊 Multiple IP Services** - Redundant IP detection for reliability

## Quick Start

```bash
# Clone and setup
git clone https://github.com/hawkinslabdev/tiny-ip-monitor
cd tiny-ip-monitor
mkdir logs

# Configure your settings in docker-compose.yml
# Start monitoring
docker compose up -d

# Access dashboard
open http://localhost:8081
```

## Configuration

Set your VPN's IP range and webhook endpoint:

```yaml
environment:
  - ALLOWED_IP_RANGE=217.190.0.0/16  # Your VPN provider's IP range
  - WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/your-id
  - CRON_SCHEDULE=0 */12 * * *        # Check every 12 hours
```

## Webhook Integrations

- **Home Assistant** - Native webhook automation support
- **Discord** - Direct webhook notifications  
- **Slack** - Instant team alerts
- **Ntfy.sh** - Simple push notifications
- **Custom** - Any HTTP endpoint

## Web Interface

- **Live Status** - Current IP and VPN status
- **Manual Testing** - Test VPN checks and webhook delivery
- **Log Viewer** - Real-time monitoring logs
- **Configuration** - View current settings

## Use Cases

- **Home Network Security** - Alert when home devices bypass VPN
- **Remote Worker Monitoring** - Ensure corporate traffic stays protected  
- **Server Monitoring** - Verify VPS/server VPN connections
- **Family Safety** - Monitor kids' devices for VPN compliance

## What's Included

- Lightweight Python monitoring daemon
- Modern web dashboard with live updates
- Configurable CRON scheduling
- Multi-service IP detection (ipinfo.io, ipify.org, etc.), but only as fallback!
- Comprehensive logging and error handling
- Docker health checks and auto-restart

Perfect for home labs, small offices, or personal VPN monitoring needs!