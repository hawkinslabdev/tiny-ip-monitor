#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
import subprocess
import traceback
import logging
from datetime import datetime
from monitor import VPNMonitor
from config import Config

# Setup Flask app logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

class WebVPNMonitor:
    def __init__(self):
        self.monitor = VPNMonitor()
        self.log_file = '/var/log/vpn-monitor.log'
        self.logger = logging.getLogger(__name__)
        
        # Ensure log file exists
        self.ensure_log_file()
        
        self.logger.info("Web VPN Monitor initialized")
    
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
    
    def get_current_status(self):
        """Get current IP and status"""
        try:
            self.logger.info("Getting current status...")
            current_ip = self.monitor.get_public_ip()
            if not current_ip:
                return {"error": "Could not retrieve IP"}
            
            in_range = self.monitor.is_ip_in_range(current_ip, self.monitor.config.ALLOWED_IP_RANGE)
            
            status = {
                "current_ip": current_ip,
                "allowed_range": self.monitor.config.ALLOWED_IP_RANGE,
                "in_range": in_range,
                "status": "OK" if in_range else "ALERT",
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Status: {status['status']}, IP: {current_ip}")
            return status
            
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")
            return {"error": f"Status check failed: {str(e)}"}
    
    def get_recent_logs(self, lines=50):
        """Get recent log entries"""
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
                    self.logger.info(f"Retrieved {len(filtered_lines)} log lines via tail")
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
                    self.logger.info(f"Retrieved {len(filtered_lines)} log lines via Python")
                    return filtered_lines
            except Exception as e:
                self.logger.error(f"Failed to read log file with Python: {e}")
                return [f"Error reading log file: {str(e)}"]
                
        except Exception as e:
            self.logger.error(f"Unexpected error getting logs: {e}")
            return [f"Unexpected error: {str(e)}"]

web_monitor = WebVPNMonitor()

@app.route('/')
def dashboard():
    """Main dashboard"""
    try:
        app.logger.info("Loading dashboard")
        status = web_monitor.get_current_status()
        config = web_monitor.monitor.config
        logs = web_monitor.get_recent_logs(20)
        
        return render_template('dashboard.html', 
                             status=status, 
                             config=config, 
                             logs=logs)
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        app.logger.error(traceback.format_exc())
        return f"Dashboard error: {str(e)}", 500

@app.route('/api/status')
def api_status():
    """API endpoint for current status"""
    try:
        app.logger.info("API status request")
        return jsonify(web_monitor.get_current_status())
    except Exception as e:
        app.logger.error(f"API status error: {e}")
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

@app.route('/api/logs')
def api_logs():
    """Get recent logs"""
    try:
        lines = request.args.get('lines', 50, type=int)
        app.logger.info(f"API logs request for {lines} lines")
        logs = web_monitor.get_recent_logs(lines)
        return jsonify({"logs": logs})
    except Exception as e:
        app.logger.error(f"API logs error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/config', methods=['GET', 'POST'])
def config_page():
    """Configuration page"""
    if request.method == 'POST':
        return jsonify({"message": "Configuration update not implemented"})
    
    try:
        config = web_monitor.monitor.config
        return render_template('config.html', config=config)
    except Exception as e:
        app.logger.error(f"Config page error: {e}")
        return f"Config error: {str(e)}", 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Try to get current status to verify everything is working
        status = web_monitor.get_current_status()
        if "error" in status:
            return jsonify({"status": "unhealthy", "error": status["error"]}), 503
        
        # Check if log file is accessible
        log_accessible = os.path.exists(web_monitor.log_file) and os.access(web_monitor.log_file, os.R_OK)
        
        return jsonify({
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "log_file_accessible": log_accessible,
            "current_ip": status.get("current_ip"),
            "vpn_status": status.get("status")
        })
    except Exception as e:
        app.logger.error(f"Health check error: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

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
    app.logger.info(f"Starting VPN Monitor web server on port {port}")
    
    try:
        with open(web_monitor.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Starting web server on port {port}\n")
    except Exception as e:
        app.logger.warning(f"Could not write to log file: {e}")
    
    # Call startup log function directly
    startup_log()
    
    app.run(host='0.0.0.0', port=port, debug=False)