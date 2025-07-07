#!/usr/bin/env python3

import requests
import ipaddress
import logging
import json
import os
from datetime import datetime
from config import Config

class VPNMonitor:
    def __init__(self):
        self.config = Config()
        self.log_file = '/var/log/monitor.log'
        self.setup_logging()
    
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
        
        # File handler
        try:
            file_handler = logging.FileHandler(self.log_file, mode='a')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create file handler: {e}")
        
        # Console handler (for docker logs)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
        # Log startup
        self.logger.info("VPN Monitor logging initialized")
        self.logger.info(f"Log file: {self.log_file}")
    
    def get_public_ip(self):
        """Get current public IP address"""
        services = [
            'https://ipinfo.io/ip',
            'https://api.ipify.org',
            'https://ip.seeip.org',
            'https://ifconfig.me/ip'
        ]
        
        for service in services:
            try:
                self.logger.info(f"Checking IP via {service}")
                response = requests.get(service, timeout=10)
                response.raise_for_status()
                ip = response.text.strip()
                self.logger.info(f"Retrieved IP: {ip}")
                return ip
            except requests.RequestException as e:
                self.logger.warning(f"Failed to get IP from {service}: {e}")
                continue
        
        self.logger.error("Failed to get public IP from all services")
        return None
    
    def is_ip_in_range(self, ip_str, cidr_range):
        """Check if IP is within the specified CIDR range"""
        try:
            ip = ipaddress.ip_address(ip_str)
            network = ipaddress.ip_network(cidr_range, strict=False)
            result = ip in network
            self.logger.info(f"IP {ip_str} in range {cidr_range}: {result}")
            return result
        except (ipaddress.AddressValueError, ValueError) as e:
            self.logger.error(f"Invalid IP or CIDR range: {e}")
            return False
    
    def send_notification(self, current_ip):
        """Send HTTP notification with configurable method and optional basic auth"""
        message = f"VPN IP Alert: Current IP {current_ip} is outside allowed range {self.config.ALLOWED_IP_RANGE}"
        
        payload = {
            "message": message,
            "current_ip": current_ip,
            "allowed_range": self.config.ALLOWED_IP_RANGE,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            self.logger.info(f"Sending {self.config.WEBHOOK_METHOD} notification")
            self.logger.info(f"Webhook URL: {self.config.WEBHOOK_URL}")
            self.logger.info(f"Message: {message}")
            
            # Prepare request arguments
            request_kwargs = {
                'timeout': 10,
                'headers': {'Content-Type': 'application/json'}
            }
            
            # Add authentication if credentials are provided
            if self.config.WEBHOOK_USER and self.config.WEBHOOK_PASS:
                request_kwargs['auth'] = (self.config.WEBHOOK_USER, self.config.WEBHOOK_PASS)
                self.logger.info("Using basic authentication")
            else:
                self.logger.info("No authentication configured")
            
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
                params = {k: str(v) for k, v in payload.items()}
                url_with_params = f"{self.config.WEBHOOK_URL}?{urllib.parse.urlencode(params)}"
                response = requests.get(url_with_params, **{k: v for k, v in request_kwargs.items() if k != 'headers'})
            elif self.config.WEBHOOK_METHOD == 'HEAD':
                # HEAD requests don't send body data
                response = requests.head(self.config.WEBHOOK_URL, **{k: v for k, v in request_kwargs.items() if k not in ['headers', 'json']})
            
            if response.status_code in [200, 201, 202, 204]:
                self.logger.info(f"Notification sent successfully (HTTP {response.status_code})")
            else:
                self.logger.error(f"Failed to send notification (HTTP {response.status_code})")
                self.logger.error(f"Response: {response.text}")
                
        except requests.RequestException as e:
            self.logger.error(f"Error sending notification: {e}")
    
    def run_check(self):
        """Main monitoring logic"""
        self.logger.info("=" * 50)
        self.logger.info("Starting VPN IP check...")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        
        # Log configuration
        self.logger.info(f"Allowed IP range: {self.config.ALLOWED_IP_RANGE}")
        self.logger.info(f"Webhook URL: {self.config.WEBHOOK_URL}")
        self.logger.info(f"Webhook method: {self.config.WEBHOOK_METHOD}")
        
        # Get current public IP
        current_ip = self.get_public_ip()
        if not current_ip:
            self.logger.error("Could not retrieve current IP address - check failed")
            return False
        
        self.logger.info(f"Current public IP: {current_ip}")
        
        # Check if IP is in allowed range
        if self.is_ip_in_range(current_ip, self.config.ALLOWED_IP_RANGE):
            self.logger.info("✅ IP is within allowed range - VPN is working correctly")
            self.logger.info("No action needed")
        else:
            self.logger.warning("❌ IP is outside allowed range - VPN may not be working!")
            self.logger.warning("Sending notification...")
            self.send_notification(current_ip)
        
        self.logger.info("VPN IP check completed")
        self.logger.info("=" * 50)
        return True

def main():
    """Main entry point"""
    print("VPN Monitor starting...")
    monitor = VPNMonitor()
    
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