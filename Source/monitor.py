#!/usr/bin/env python3

import requests
import ipaddress
import logging
import json
import os
import time
from datetime import datetime, timedelta
from config import Config

class IPMonitor:
    def __init__(self):
        self.config = Config()
        self.log_file = '/var/log/ip-monitor.log'
        self.state_file = '/app/data/monitor_state.json'
        self.setup_logging()
        self.load_state()
    
    def setup_logging(self):
        """Setup logging to both file and console"""
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create rotating file handler: {e}")
            # Fallback to regular file handler
            try:
                file_handler = logging.FileHandler(self.log_file, mode='a')
                file_handler.setLevel(logging.INFO)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e2:
                print(f"Warning: Could not create file handler: {e2}")
        
        # Console handler (for docker logs)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
        # Log startup
        self.logger.info("ip monitor logging initialized")
        self.logger.info(f"Log file: {self.log_file}")
    
    def load_state(self):
        """Load monitor state from file"""
        self.state = {
            'last_alert_time': None,
            'consecutive_alerts': 0,
            'last_known_ip': None,
            'total_checks': 0,
            'alerts_sent': 0
        }
        
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state.update(json.load(f))
                self.logger.info("Loaded monitor state")
            except Exception as e:
                self.logger.warning(f"Could not load state file: {e}")
    
    def save_state(self):
        """Save monitor state to file"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Could not save state: {e}")
    
    def get_public_ip(self):
        """Get current public IP address with retry logic"""
        services = [
            'https://ipinfo.io/ip',
            'https://api.ipify.org',
            'https://ip.seeip.org',
            'https://ifconfig.me/ip',
            'https://checkip.amazonaws.com'
        ]
        
        for attempt, service in enumerate(services, 1):
            try:
                self.logger.info(f"Attempt {attempt}: Checking IP via {service}")
                response = requests.get(service, timeout=10)
                response.raise_for_status()
                ip = response.text.strip()
                
                # Validate IP format
                ipaddress.ip_address(ip)
                
                self.logger.info(f"Retrieved IP: {ip}")
                return ip
                
            except requests.RequestException as e:
                self.logger.warning(f"Failed to get IP from {service}: {e}")
                continue
            except ipaddress.AddressValueError as e:
                self.logger.warning(f"Invalid IP format from {service}: {ip}")
                continue
        
        self.logger.error("Failed to get public IP from all services")
        return None
    
    def is_ip_safe(self, ip_str):
        """Check if IP is within any protected CIDR range - returns False if IP needs protection (alert should be triggered)"""
        try:
            ip = ipaddress.ip_address(ip_str)
            safe_ranges = self.config.get_safe_ranges()
            
            for cidr_range in safe_ranges:
                try:
                    network = ipaddress.ip_network(cidr_range.strip(), strict=False)
                    if ip in network:
                        self.logger.warning(f"IP {ip_str} is in protected range {cidr_range} - VPN may be disabled")
                        return False, cidr_range  # Alert needed - IP is in protected range
                except ValueError as e:
                    self.logger.error(f"Invalid CIDR range {cidr_range}: {e}")
                    continue
            
            self.logger.info(f"IP {ip_str} is not in any protected ranges - VPN appears active")
            return True, None  # No alert needed - IP is outside protected ranges
            
        except (ipaddress.AddressValueError, ValueError) as e:
            self.logger.error(f"Invalid IP address: {e}")
            return False, None
    
    def should_send_alert(self):
        """Check if we should send an alert based on cooldown"""
        if not self.state['last_alert_time']:
            return True
        
        try:
            last_alert = datetime.fromisoformat(self.state['last_alert_time'])
            cooldown_str = self.config.ALERT_COOLDOWN
            
            # Parse cooldown (e.g., "1h", "30m", "2h30m")
            cooldown_seconds = self.parse_time_string(cooldown_str)
            cooldown_delta = timedelta(seconds=cooldown_seconds)
            
            return datetime.now() - last_alert >= cooldown_delta
            
        except Exception as e:
            self.logger.error(f"Error checking alert cooldown: {e}")
            return True  # Err on the side of sending alerts
    
    def parse_time_string(self, time_str):
        """Parse time string like '1h', '30m', '2h30m' into seconds"""
        import re
        
        # Default to seconds if no unit
        if time_str.isdigit():
            return int(time_str)
        
        # Parse h/m/s format
        total_seconds = 0
        
        # Hours
        hours = re.findall(r'(\d+)h', time_str)
        if hours:
            total_seconds += int(hours[0]) * 3600
        
        # Minutes
        minutes = re.findall(r'(\d+)m', time_str)
        if minutes:
            total_seconds += int(minutes[0]) * 60
        
        # Seconds
        seconds = re.findall(r'(\d+)s', time_str)
        if seconds:
            total_seconds += int(seconds[0])
        
        return total_seconds if total_seconds > 0 else 3600  # Default 1 hour
    
    def send_notification(self, current_ip, protected_range):
        """Send HTTP notification when IP is in a protected range (VPN disabled)"""
        if not self.should_send_alert():
            self.logger.info("Alert suppressed due to cooldown period")
            return
        
        message = f"VPN ALERT: Current IP {current_ip} is in protected range {protected_range}. VPN may be disabled - you are not protected!"
        
        payload = {
            "message": message,
            "current_ip": current_ip,
            "protected_ranges": self.config.get_safe_ranges(),
            "matched_range": protected_range,
            "timestamp": datetime.now().isoformat(),
            "alert_type": "vpn_disabled",
            "consecutive_alerts": self.state['consecutive_alerts'] + 1,
            "monitor_stats": {
                "total_checks": self.state['total_checks'],
                "alerts_sent": self.state['alerts_sent'] + 1
            }
        }
        
        try:
            self.logger.info(f"Sending {self.config.WEBHOOK_METHOD} notification")
            self.logger.info(f"Webhook URL: {self.config.WEBHOOK_URL}")
            self.logger.info(f"Message: {message}")
            
            # Prepare request arguments
            request_kwargs = {
                'timeout': 30,
                'headers': {'Content-Type': 'application/json'}
            }
            
            # Add authentication if credentials are provided
            if self.config.WEBHOOK_USER and self.config.WEBHOOK_PASS:
                request_kwargs['auth'] = (self.config.WEBHOOK_USER, self.config.WEBHOOK_PASS)
                self.logger.info("Using basic authentication")
            
            # Handle different HTTP methods
            if self.config.WEBHOOK_METHOD in ['POST', 'PUT', 'PATCH']:
                request_kwargs['json'] = payload
                response = getattr(requests, self.config.WEBHOOK_METHOD.lower())(
                    self.config.WEBHOOK_URL,
                    **request_kwargs
                )
            elif self.config.WEBHOOK_METHOD == 'GET':
                # For GET requests, send data as URL parameters
                import urllib.parse
                params = {k: str(v) for k, v in payload.items() if k not in ['safe_ranges', 'monitor_stats']}
                url_with_params = f"{self.config.WEBHOOK_URL}?{urllib.parse.urlencode(params)}"
                response = requests.get(url_with_params, **{k: v for k, v in request_kwargs.items() if k != 'headers'})
            elif self.config.WEBHOOK_METHOD == 'HEAD':
                # HEAD requests don't send body data
                response = requests.head(self.config.WEBHOOK_URL, **{k: v for k, v in request_kwargs.items() if k not in ['headers', 'json']})
            
            if response.status_code in [200, 201, 202, 204]:
                self.logger.info(f"Notification sent successfully (HTTP {response.status_code})")
                
                # Update state
                self.state['last_alert_time'] = datetime.now().isoformat()
                self.state['consecutive_alerts'] += 1
                self.state['alerts_sent'] += 1
                self.save_state()
                
            else:
                self.logger.error(f"Failed to send notification (HTTP {response.status_code})")
                self.logger.error(f"Response: {response.text}")
                
        except requests.RequestException as e:
            self.logger.error(f"Error sending notification: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending notification: {e}")
    
    def get_status(self):
        """Get current monitor status"""
        current_ip = self.get_public_ip()
        if not current_ip:
            return {
                "error": "Could not retrieve current IP",
                "timestamp": datetime.now().isoformat()
            }
        
        is_safe, safe_range = self.is_ip_safe(current_ip)
        
        return {
            "current_ip": current_ip,
            "protected_ranges": self.config.get_safe_ranges(),
            "is_safe": is_safe,
            "protected_range": safe_range,
            "status": "Protected" if is_safe else "Alert",
            "timestamp": datetime.now().isoformat(),
            "config_source": self.config.config_source,
            "monitor_stats": self.state,
            "next_alert_allowed": self.should_send_alert()
        }
    
    def run_check(self):
        """Main monitoring logic"""
        self.logger.info("=" * 50)
        self.logger.info("Starting IP check...")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        
        # Update check counter
        self.state['total_checks'] += 1
        
        # Log configuration
        self.logger.info(f"Protected IP ranges (VPN off alert): {', '.join(self.config.get_safe_ranges())}")
        self.logger.info(f"Webhook URL: {self.config.WEBHOOK_URL}")
        self.logger.info(f"Config source: {self.config.config_source}")
        
        # Get current public IP
        current_ip = self.get_public_ip()
        if not current_ip:
            self.logger.error("Could not retrieve current IP address - check failed")
            return False
        
        self.logger.info(f"Current public IP: {current_ip}")
        
        # Track IP changes
        if self.state['last_known_ip'] and self.state['last_known_ip'] != current_ip:
            self.logger.info(f"IP changed from {self.state['last_known_ip']} to {current_ip}")
        
        self.state['last_known_ip'] = current_ip
        
        # Check if IP is in protected range (VPN disabled)
        is_safe, protected_range = self.is_ip_safe(current_ip)
        
        if not is_safe:
            self.logger.warning(f"⚠️  VPN ALERT: IP {current_ip} is in protected range {protected_range}")
            self.logger.warning("VPN may be disabled - you are not protected!")
            
            if self.should_send_alert():
                self.logger.warning("Sending VPN disabled notification...")
                self.send_notification(current_ip, protected_range)
            else:
                self.logger.info("Alert suppressed due to cooldown period")
        else:
            self.logger.info(f"Success; VPN Active: IP {current_ip} is outside protected ranges")
            # Reset consecutive alerts counter
            self.state['consecutive_alerts'] = 0
        
        # Save state
        self.save_state()
        
        self.logger.info(f"Total checks: {self.state['total_checks']}, Alerts sent: {self.state['alerts_sent']}")
        self.logger.info("IP check completed")
        self.logger.info("=" * 50)
        return True

def main():
    """Main entry point"""
    print("ip monitor starting...")
    monitor = IPMonitor()
    
    try:
        success = monitor.run_check()
        exit_code = 0 if success else 1
        monitor.logger.info(f"Monitor exiting with code: {exit_code}")
        exit(exit_code)
    except KeyboardInterrupt:
        monitor.logger.info("Monitor interrupted by user")
        exit(130)
    except Exception as e:
        monitor.logger.error(f"Unexpected error: {e}")
        monitor.logger.error("Monitor crashed", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()