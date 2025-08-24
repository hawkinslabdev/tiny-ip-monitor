#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
import subprocess
import traceback
import logging
from datetime import datetime
from monitor import IPMonitor
from config import Config

# Setup Flask app logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

class WebIPMonitor:
    def __init__(self):
        self.monitor = IPMonitor()
        self.log_file = '/var/log/ip-monitor.log'
        self.logger = logging.getLogger(__name__)
        
        # Ensure log file exists
        self.ensure_log_file()
        
        self.logger.info("Web IP Monitor initialized")
    
    def ensure_log_file(self):
        """Ensure log file exists and is accessible"""
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            if not os.path.exists(self.log_file):
                with open(self.log_file, 'w') as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Log file created\n")
            self.logger.info(f"Log file ready: {self.log_file}")
        except Exception as e:
            self.logger.error(f"Could not create log file: {e}")
    
    def get_recent_logs(self, lines=50):
        """Get recent log entries with better error handling"""
        try:
            if not os.path.exists(self.log_file):
                self.logger.warning(f"Log file does not exist: {self.log_file}")
                return [f"Log file not found: {self.log_file}"]
            
            # Check if file is readable
            if not os.access(self.log_file, os.R_OK):
                self.logger.error(f"Log file not readable: {self.log_file}")
                return [f"Log file not readable: {self.log_file}"]
            
            # Try to read with tail command first
            try:
                result = subprocess.run(
                    ['tail', '-n', str(lines), self.log_file], 
                    capture_output=True, 
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    log_lines = result.stdout.split('\n')
                    filtered_lines = [line for line in log_lines if line.strip()]
                    self.logger.debug(f"Retrieved {len(filtered_lines)} log lines via tail")
                    return filtered_lines
                else:
                    self.logger.warning(f"tail command failed: {result.stderr}")
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                self.logger.warning(f"tail command not available or timed out: {e}")
            
            # Fallback to Python file reading
            try:
                with open(self.log_file, 'r') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if all_lines else []
                    filtered_lines = [line.strip() for line in recent_lines if line.strip()]
                    self.logger.debug(f"Retrieved {len(filtered_lines)} log lines via Python")
                    return filtered_lines
            except Exception as e:
                self.logger.error(f"Failed to read log file with Python: {e}")
                return [f"Error reading log file: {str(e)}"]
                
        except Exception as e:
            self.logger.error(f"Unexpected error getting logs: {e}")
            return [f"Unexpected error: {str(e)}"]

web_monitor = WebIPMonitor()

# Routes
@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/config')
def config_page():
    """Configuration page"""
    return render_template('config.html')

# API Routes
@app.route('/api/status')
def api_status():
    """API endpoint for current status"""
    try:
        app.logger.info("API status request")
        status = web_monitor.monitor.get_status()
        return jsonify(status)
    except Exception as e:
        app.logger.error(f"API status error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Configuration management API"""
    try:
        if request.method == 'GET':
            config_dict = web_monitor.monitor.config.to_dict()
            return jsonify(config_dict)
        
        elif request.method == 'POST':
            new_config = request.get_json()
            
            if not web_monitor.monitor.config.is_editable():
                return jsonify({
                    "error": "Configuration is locked by environment variables",
                    "message": "Remove environment variables and restart to enable web configuration"
                }), 403
            
            # Save new configuration
            web_monitor.monitor.config.save_config(new_config)
            
            # Reload monitor with new config
            web_monitor.monitor = IPMonitor()
            
            app.logger.info("Configuration updated via API")
            return jsonify({
                "success": True,
                "message": "Configuration updated successfully"
            })
            
    except Exception as e:
        app.logger.error(f"API config error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/migrate', methods=['POST'])
def api_migrate_config():
    """Migrate from environment variables to file-based config"""
    try:
        success = web_monitor.monitor.config.migrate_from_env()
        if success:
            # Reload monitor
            web_monitor.monitor = IPMonitor()
            return jsonify({
                "success": True,
                "message": "Configuration migrated successfully. Remove environment variables and restart for full effect."
            })
        else:
            return jsonify({
                "success": False,
                "message": "No environment variables found to migrate"
            })
    except Exception as e:
        app.logger.error(f"Config migration error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test')
def api_test():
    """Test the monitoring manually"""
    try:
        app.logger.info("Manual test requested")
        
        # Add a log entry indicating manual test
        with open(web_monitor.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Manual test initiated via web interface\n")
        
        # Run the monitor check
        success = web_monitor.monitor.run_check()
        
        if success:
            app.logger.info("Manual test completed successfully")
            return jsonify({
                "success": True, 
                "message": "Manual check completed successfully"
            })
        else:
            app.logger.error("Manual test failed")
            return jsonify({
                "success": False,
                "error": "Check failed - see logs for details"
            }), 500
            
    except Exception as e:
        app.logger.error(f"Test failed: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

@app.route('/api/webhook-test')
def api_webhook_test():
    """Test webhook endpoint"""
    try:
        app.logger.info("Webhook test requested")
        
        # Get current IP for test
        current_ip = web_monitor.monitor.get_public_ip()
        if not current_ip:
            return jsonify({
                "success": False,
                "error": "Could not retrieve current IP"
            }), 500
        
        # Send test notification
        web_monitor.monitor.send_notification(current_ip, "TEST-RANGE")
        
        app.logger.info("Webhook test completed")
        return jsonify({
            "success": True,
            "message": "Test webhook sent successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Webhook test failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/logs')
def api_logs():
    """Get recent logs"""
    try:
        lines = request.args.get('lines', 100, type=int)
        search = request.args.get('search', '', type=str)
        level = request.args.get('level', '', type=str)
        
        app.logger.info(f"API logs request for {lines} lines")
        logs = web_monitor.get_recent_logs(lines)
        
        # Filter logs if search or level specified
        if search or level:
            filtered_logs = []
            for log in logs:
                if search and search.lower() not in log.lower():
                    continue
                if level and f"] {level.upper()}:" not in log:
                    continue
                filtered_logs.append(log)
            logs = filtered_logs
        
        return jsonify({
            "logs": logs,
            "total": len(logs),
            "filters": {
                "search": search,
                "level": level,
                "lines": lines
            }
        })
    except Exception as e:
        app.logger.error(f"API logs error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Get monitor statistics"""
    try:
        stats = web_monitor.monitor.state.copy()
        stats['config_source'] = web_monitor.monitor.config.config_source
        stats['log_file_size'] = os.path.getsize(web_monitor.log_file) if os.path.exists(web_monitor.log_file) else 0
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"API stats error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Try to get current status to verify everything is working
        status = web_monitor.monitor.get_status()
        if "error" in status:
            return jsonify({"status": "unhealthy", "error": status["error"]}), 503
        
        # Check if log file is accessible
        log_accessible = os.path.exists(web_monitor.log_file) and os.access(web_monitor.log_file, os.R_OK)
        
        return jsonify({
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "log_file_accessible": log_accessible,
            "current_ip": status.get("current_ip"),
            "monitor_status": status.get("status"),
            "config_source": web_monitor.monitor.config.config_source
        })
    except Exception as e:
        app.logger.error(f"Health check error: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

# Static file serving
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

def startup_log():
    """Log when the web server starts"""
    try:
        with open(web_monitor.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Web server started on port {os.getenv('WEB_PORT', 8080)}\n")
    except Exception as e:
        app.logger.error(f"Could not write startup log: {e}")

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', 8080))
    
    # Log startup
    app.logger.info(f"Starting ip monitor web server on port {port}")
    
    try:
        with open(web_monitor.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Starting web server on port {port}\n")
    except Exception as e:
        app.logger.warning(f"Could not write to log file: {e}")
    
    # Call startup log function directly
    startup_log()
    
    app.run(host='0.0.0.0', port=port, debug=False)