import os
import json
import logging
from typing import Optional, Dict, Any

class Config:
    """Production-ready configuration class for ip monitor"""
    
    def __init__(self):
        self.config_file = '/app/data/config.json'
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Load configuration
        self.load_config()
        
        # Validate configuration
        self._validate_config()
    
    def load_config(self):
        """Load configuration with priority: file > environment > defaults"""
        
        # Load from file if it exists
        file_config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                self.logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                self.logger.error(f"Failed to load config file: {e}")
                file_config = {}
        
        # Configuration with priority: file > env > defaults
        self.SAFE_IP_RANGE = (
            file_config.get('safe_ip_range') or
            self._get_env_var('SAFE_IP_RANGE', '192.168.1.0/24')
        )
        
        self.WEBHOOK_URL = (
            file_config.get('webhook_url') or
            self._get_env_var('WEBHOOK_URL', 'http://your-home-assistant:8123/api/webhook/your_webhook_id')
        )
        
        self.WEBHOOK_METHOD = (
            file_config.get('webhook_method') or
            self._get_env_var('WEBHOOK_METHOD', 'POST')
        ).upper()
        
        self.WEBHOOK_USER = (
            file_config.get('webhook_user') or
            self._get_env_var('WEBHOOK_USER', '')
        )
        
        self.WEBHOOK_PASS = (
            file_config.get('webhook_pass') or
            self._get_env_var('WEBHOOK_PASS', '')
        )
        
        self.CHECK_INTERVAL = (
            file_config.get('check_interval') or
            self._get_env_var('CHECK_INTERVAL', '12h')
        )
        
        self.ALERT_COOLDOWN = (
            file_config.get('alert_cooldown') or
            self._get_env_var('ALERT_COOLDOWN', '1h')
        )
        
        self.APP_NAME = (
            file_config.get('app_name') or
            self._get_env_var('APP_NAME', 'ip monitor')
        )
        
        # Determine config source
        self.config_source = 'file' if os.path.exists(self.config_file) and file_config else 'environment'
        
        self.logger.info(f"Configuration source: {self.config_source}")
    
    def _get_env_var(self, key: str, default: str) -> str:
        """Get environment variable with default value"""
        return os.getenv(key, default)
    
    def _validate_config(self):
        """Validate configuration values"""
        if not self.WEBHOOK_URL.startswith(('http://', 'https://')):
            raise ValueError("WEBHOOK_URL must start with http:// or https://")
        
        # Validate safe IP ranges (can be comma-separated)
        ranges = self.get_safe_ranges()
        for range_str in ranges:
            if '/' not in range_str:
                raise ValueError(f"IP range must be in CIDR format: {range_str}")
        
        if self.WEBHOOK_METHOD not in ['GET', 'POST', 'PUT', 'PATCH', 'HEAD']:
            raise ValueError("WEBHOOK_METHOD must be one of: GET, POST, PUT, PATCH, HEAD")
    
    def get_safe_ranges(self):
        """Get list of protected IP ranges (ranges where VPN is disabled/alert should trigger)"""
        return [r.strip() for r in self.SAFE_IP_RANGE.split(',') if r.strip()]
    
    def is_editable(self):
        """Check if configuration can be edited via web interface"""
        return self.config_source == 'file' or not os.path.exists(self.config_file)
    
    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            'safe_ip_range': self.SAFE_IP_RANGE,
            'webhook_url': self.WEBHOOK_URL,
            'webhook_method': self.WEBHOOK_METHOD,
            'webhook_user': self.WEBHOOK_USER,
            'webhook_pass': self.WEBHOOK_PASS,
            'check_interval': self.CHECK_INTERVAL,
            'alert_cooldown': self.ALERT_COOLDOWN,
            'app_name': self.APP_NAME,
            'config_source': self.config_source,
            'is_editable': self.is_editable()
        }
    
    def save_config(self, new_config: Dict[str, Any]):
        """Save configuration to file"""
        if not self.is_editable():
            raise ValueError("Configuration is locked by environment variables")
        
        try:
            # Validate new config
            config_to_save = {
                'safe_ip_range': new_config.get('safe_ip_range', self.SAFE_IP_RANGE),
                'webhook_url': new_config.get('webhook_url', self.WEBHOOK_URL),
                'webhook_method': new_config.get('webhook_method', self.WEBHOOK_METHOD).upper(),
                'webhook_user': new_config.get('webhook_user', self.WEBHOOK_USER),
                'webhook_pass': new_config.get('webhook_pass', self.WEBHOOK_PASS),
                'check_interval': new_config.get('check_interval', self.CHECK_INTERVAL),
                'alert_cooldown': new_config.get('alert_cooldown', self.ALERT_COOLDOWN),
                'app_name': new_config.get('app_name', self.APP_NAME)
            }
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            
            # Reload configuration
            self.load_config()
            self._validate_config()
            
            self.logger.info("Configuration saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def migrate_from_env(self):
        """Migrate configuration from environment variables to file"""
        env_config = {
            'safe_ip_range': self._get_env_var('SAFE_IP_RANGE', ''),
            'webhook_url': self._get_env_var('WEBHOOK_URL', ''),
            'webhook_method': self._get_env_var('WEBHOOK_METHOD', 'POST'),
            'webhook_user': self._get_env_var('WEBHOOK_USER', ''),
            'webhook_pass': self._get_env_var('WEBHOOK_PASS', ''),
            'check_interval': self._get_env_var('CHECK_INTERVAL', '12h'),
            'alert_cooldown': self._get_env_var('ALERT_COOLDOWN', '1h')
        }
        
        # Only save non-empty values
        config_to_save = {k: v for k, v in env_config.items() if v}
        
        if config_to_save:
            with open(self.config_file, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            
            self.load_config()
            self.logger.info("Configuration migrated from environment variables")
            return True
        
        return False
    
    def __str__(self):
        """String representation (safe for logging)"""
        auth_status = "enabled" if self.WEBHOOK_USER and self.WEBHOOK_PASS else "disabled"
        return f"""ip monitor Configuration:
  Source: {self.config_source}
  Editable: {self.is_editable()}
  Safe IP Ranges: {self.SAFE_IP_RANGE}
  Webhook URL: {self.WEBHOOK_URL}
  Webhook Method: {self.WEBHOOK_METHOD}
  Basic Auth: {auth_status}
  Check Interval: {self.CHECK_INTERVAL}
  Alert Cooldown: {self.ALERT_COOLDOWN}"""