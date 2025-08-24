# 🔐 ip monitor

A lightweight, production-ready IP monitoring solution that automatically alerts you when your public IP address is not within your configured safe ranges (typically indicating you're not at home or on a trusted network).

![ip monitor Dashboard](Documentation/dashboard.png)

## ✨ Features

- **🎯 Modern Interface** - Clean, responsive web dashboard with real-time updates
- **🔧 Web Configuration** - Edit settings through the browser (with environment fallback)
- **⚡ Lightweight** - Alpine Linux based, minimal resource usage
- **🔔 Smart Alerts** - Configurable cooldown periods to prevent spam
- **📊 Advanced Logging** - Searchable logs with filtering and export
- **🌐 Multiple Endpoints** - Redundant IP detection services
- **🔒 Production Ready** - Health checks, log rotation, error handling

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/ip-monitor
cd ip-monitor

# Create data directories
mkdir -p logs data

# Start the service
docker compose up -d

# Access the dashboard
open http://localhost:8081
```

## 🐳 Docker Images

Pre-built Docker images are available from GitHub Container Registry:

### Using Docker Run
```bash
# Latest version
docker run -d \
  --name ip-monitor \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/var/log \
  ghcr.io/hawkinslabdev/tiny-ip-monitor:latest

# Specific version
docker run -d \
  --name ip-monitor \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/var/log \
  ghcr.io/hawkinslabdev/tiny-ip-monitor:v1.0.0
```

### Using Docker Compose
```yaml
version: '3.8'
services:
  ip-monitor:
    image: ghcr.io/hawkinslabdev/tiny-ip-monitor:latest
    container_name: ip-monitor
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./logs:/var/log
    restart: unless-stopped
```

### Available Tags
- `latest` - Latest stable release
- `master` - Latest from master branch
- `v1.0.0`, `v1.0`, etc. - Specific version releases

## ⚙️ Configuration

### Option 1: Web Configuration (Recommended)

1. Start the container without environment variables
2. Open the web interface at `http://localhost:8081`
3. Navigate to the Configuration page
4. Set your safe IP ranges and webhook settings
5. Configuration is automatically saved to `./data/config.json`

### Option 2: Environment Variables

Edit `docker-compose.yml` and uncomment the environment variables:

```yaml
environment:
  - SAFE_IP_RANGE=192.168.1.0/24
  - WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/your-id
  - WEBHOOK_METHOD=POST
  - CHECK_INTERVAL=12h
  - ALERT_COOLDOWN=1h
```

### Migration Between Configuration Methods

You can migrate from environment variables to web configuration:

1. Go to Configuration page
2. Click "Migrate to File Configuration"
3. Remove environment variables from `docker-compose.yml`
4. Restart the container

## 📋 Configuration Options

| Setting | Description | Default | Example |
|---------|-------------|---------|---------|
| `SAFE_IP_RANGE` | Comma-separated CIDR ranges for safe/home networks | `192.168.1.0/24` | `192.168.1.0/24,10.0.1.0/24` |
| `WEBHOOK_URL` | Alert notification endpoint | None | `http://ha.local:8123/api/webhook/id` |
| `WEBHOOK_METHOD` | HTTP method for alerts | `POST` | `POST`, `PUT`, `GET` |
| `WEBHOOK_USER` | Basic auth username | None | `username` |
| `WEBHOOK_PASS` | Basic auth password | None | `password` |
| `CHECK_INTERVAL` | How often to check IP | `12h` | `6h`, `30m`, `2h30m` |
| `ALERT_COOLDOWN` | Minimum time between alerts | `1h` | `30m`, `2h` |
| `CRON_SCHEDULE` | Cron expression for checks | `0 */12 * * *` | `*/30 * * * *` |

## 🔗 Webhook Integrations

### Home Assistant
```yaml
automation:
  - alias: "IP Monitor Alert"
    trigger:
      platform: webhook
      webhook_id: your-webhook-id
    action:
      service: notify.mobile_app_your_phone
      data:
        message: "{{ trigger.json.message }}"
```

### Discord
Use Discord webhook URL directly:
```
https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
```

### Slack
Use Slack incoming webhook URL:
```
https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### Custom Webhook Payload
```json
{
  "message": "ip monitor alert: Current IP 203.0.113.1 is not in any safe range. This may indicate you are not at home or on a trusted network.",
  "current_ip": "203.0.113.1",
  "safe_ranges": ["192.168.1.0/24"],
  "timestamp": "2025-01-09T14:30:22.123456",
  "alert_type": "unsafe_ip",
  "consecutive_alerts": 1,
  "monitor_stats": {
    "total_checks": 156,
    "alerts_sent": 3
  }
}
```

## 🖥️ Web Interface

### Dashboard
- Real-time IP status and monitoring statistics
- Quick manual testing and webhook validation
- Configuration overview and recent activity

### Logs
- Searchable log viewer with filtering by level
- Export logs to file
- Auto-refresh capability
- Colored log levels for easy scanning

### Configuration
- Web-based settings editor
- Real-time configuration preview
- Migration tools between config methods
- Webhook testing capabilities

## 📁 Directory Structure

```
ip-monitor/
├── logs/                    # Log files (volume mounted)
├── data/                    # Configuration storage (volume mounted)
│   ├── config.json         # Web-managed configuration
│   └── monitor_state.json  # Runtime state and statistics
├── templates/              # Web interface templates
├── docker-compose.yml      # Container orchestration
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
├── config.py              # Configuration management
├── monitor.py             # Core monitoring logic
├── app.py                 # Web application
└── startup.py             # Container startup orchestration
```

## 🔧 Advanced Configuration

### Custom Check Intervals
```bash
# Every 30 minutes
CRON_SCHEDULE="*/30 * * * *"

# Business hours only (9 AM - 6 PM weekdays)
CRON_SCHEDULE="0 9-18 * * 1-5"

# Every 2 hours during weekdays, every 6 hours on weekends
# (requires multiple cron entries - use file-based cron configuration)
```

### Log Management
Logs are automatically rotated (10MB max, 5 files retained). Custom log retention:

```yaml
# In docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "50m"  # Increase max log size
    max-file: "10"   # Keep more log files
```

### Health Monitoring
The container includes comprehensive health checks:

- Web server responsiveness
- Log file accessibility
- IP retrieval capability
- Configuration validity

## 🚨 Troubleshooting

### Common Issues

**Configuration locked by environment variables**
- Remove environment variables from `docker-compose.yml`
- Use the migration tool in the web interface
- Restart the container

**Webhook not working**
- Test webhook from Configuration page
- Check webhook URL accessibility from container
- Verify authentication credentials
- Review logs for detailed error messages

**IP detection failing**
- Check internet connectivity from container
- Multiple IP services are used for redundancy
- Firewall may be blocking outbound requests

**Container not starting**
- Check Docker logs: `docker compose logs ip-monitor`
- Verify volume permissions: `chmod 755 logs data`
- Ensure ports are available

### Log Analysis

```bash
# View real-time logs
docker compose logs -f ip-monitor

# Search for specific issues
docker compose logs ip-monitor | grep ERROR

# Check configuration source
docker compose logs ip-monitor | grep "Configuration source"
```

## 🔒 Security Considerations

- Use HTTPS webhooks when possible
- Store sensitive credentials securely
- Regularly update the container image
- Monitor logs for unauthorized access attempts
- Use network policies to restrict container access

## 📈 Monitoring & Alerting

### Prometheus Integration
The application exposes metrics at `/health` for monitoring:

```yaml
# Add to prometheus.yml
scrape_configs:
  - job_name: 'ip-monitor'
    static_configs:
      - targets: ['ip-monitor:8080']
    metrics_path: '/health'
```

### Grafana Dashboard
Monitor key metrics:
- IP check success rate
- Alert frequency
- Configuration source
- Container health

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run web server
python app.py

# Run manual check
python monitor.py

# Test configuration
python -c "from config import Config; print(Config())"
```

### Testing
```bash
# Test log functionality
python test_logging.py

# Test webhook
curl -X POST http://localhost:8081/api/webhook-test

# Health check
curl http://localhost:8081/health
```

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup
```bash
git clone https://github.com/yourusername/ip-monitor
cd ip-monitor
pip install -r requirements.txt
python app.py  # Start development server
```

### Areas for Contribution
- Additional webhook integrations
- Enhanced logging and monitoring
- Mobile-responsive improvements
- Additional IP detection services
- Performance optimizations

## 📞 Support

- **Issues**: Report bugs or request features via GitHub Issues
- **Documentation**: Check this README and inline help in the web interface
- **Community**: Join discussions in GitHub Discussions

## 🏷️ Changelog

### v2.0.0 (Latest)
- ✨ Complete rewrite with modern web interface
- 🔧 Web-based configuration management
- 📊 Advanced log viewer with search and filtering
- 🔄 Hybrid configuration system (file + environment)
- ⚡ Improved error handling and reliability
- 🎯 Better webhook testing and validation
- 📈 Enhanced monitoring and statistics

### v1.x
- Basic VPN monitoring functionality
- Environment variable configuration only
- Simple web dashboard

## 🎯 Use Cases

### Home Presence Monitoring
Monitor when family members arrive/leave home:
```yaml
# Home network range for presence detection
SAFE_IP_RANGE: "192.168.1.0/24"
WEBHOOK_URL: "http://homeassistant.local:8123/api/webhook/presence-alert"
```

### Remote Worker Monitoring
Ensure remote workers are connecting from approved locations:
```yaml
# Allow home and office networks
SAFE_IP_RANGE: "192.168.1.0/24,10.50.0.0/24"
WEBHOOK_URL: "https://slack.com/api/webhooks/YOUR/WEBHOOK"
CHECK_INTERVAL: "1h"  # More frequent checks for work devices
```

### Security Monitoring
Detect when devices connect from unexpected locations:
```yaml
# Monitor for connections outside trusted networks
SAFE_IP_RANGE: "192.168.1.0/24,10.0.1.0/24"  # Home and trusted networks
WEBHOOK_URL: "https://api.pagerduty.com/integration/YOUR_KEY/enqueue"
ALERT_COOLDOWN: "30m"  # Faster alerts for security events
```

### IoT Device Monitoring
Monitor IoT devices that should stay on local network:
```yaml
# Monitor local IoT network
SAFE_IP_RANGE: "192.168.100.0/24"
WEBHOOK_URL: "http://nodered.local:1880/iot-alert"
CHECK_INTERVAL: "30m"  # Frequent checks for critical IoT
```

## 🔍 Advanced Examples

### Multiple Webhook Endpoints
While the current version supports one webhook URL, you can use services like n8n or Node-RED to distribute alerts:

```javascript
// Node-RED flow example
if (msg.payload.alert_type === "unsafe_ip") {
    // Send to multiple endpoints
    node.send([
        { payload: msg.payload, topic: "discord" },
        { payload: msg.payload, topic: "email" },
        { payload: msg.payload, topic: "sms" }
    ]);
}
```

### Custom Alert Logic
Process webhook data for custom alert logic:

```python
# Custom webhook processor
@app.route('/webhook/ip-monitor', methods=['POST'])
def handle_ip_alert():
    data = request.json
    
    # Custom logic based on consecutive alerts
    if data.get('consecutive_alerts', 0) > 3:
        send_emergency_alert(data)
    elif data.get('consecutive_alerts', 0) > 1:
        send_warning_alert(data)
    else:
        send_info_alert(data)
    
    return {"status": "received"}
```

### Integration with Monitoring Systems

#### Prometheus + Grafana
```yaml
# docker-compose.override.yml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

#### ELK Stack Integration
```yaml
# Filebeat configuration for log shipping
filebeat:
  inputs:
    - type: log
      paths:
        - /path/to/ip-monitor/logs/*.log
      fields:
        service: ip-monitor
        environment: production
```

## 🌐 Deployment Options

### Docker Swarm
```yaml
# docker-stack.yml
version: '3.8'
services:
  ip-monitor:
    image: your-registry/ip-monitor:latest
    ports:
      - "8081:8080"
    volumes:
      - ip-monitor-logs:/var/log
      - ip-monitor-data:/app/data
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 30s
        max_attempts: 3

volumes:
  ip-monitor-logs:
  ip-monitor-data:
```

### Kubernetes
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ip-monitor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ip-monitor
  template:
    metadata:
      labels:
        app: ip-monitor
    spec:
      containers:
      - name: ip-monitor
        image: your-registry/ip-monitor:latest
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: config-storage
          mountPath: /app/data
        - name: log-storage
          mountPath: /var/log
        env:
        - name: CRON_SCHEDULE
          value: "0 */12 * * *"
      volumes:
      - name: config-storage
        persistentVolumeClaim:
          claimName: ip-monitor-config
      - name: log-storage
        persistentVolumeClaim:
          claimName: ip-monitor-logs
```

### Systemd Service (Non-Docker)
```ini
# /etc/systemd/system/ip-monitor.service
[Unit]
Description=IP Monitor Service
After=network.target

[Service]
Type=simple
User=ip-monitor
WorkingDirectory=/opt/ip-monitor
ExecStart=/opt/ip-monitor/venv/bin/python app.py
Environment=WEB_PORT=8080
Environment=SAFE_IP_RANGE=192.168.1.0/24
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

**Made with ❤️ for network security and peace of mind.**