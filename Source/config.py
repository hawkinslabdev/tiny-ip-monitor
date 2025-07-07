import os
from typing import Optional

class Config:
    """Configuration class for VPN Monitor"""
    
    def __init__(self):
        self.ALLOWED_IP_RANGE: str = self._get_env_var(
            'ALLOWED_IP_RANGE', 
            '198.51.100.0/24'
        )
        
        self.WEBHOOK_URL: str = self._get_env_var(
            'WEBHOOK_URL',
            'http://your-home-assistant:8123/api/webhook/your_webhook_id'
        )
        
        self.WEBHOOK_METHOD: str = self._get_env_var(
            'WEBHOOK_METHOD',
            'POST'
        ).upper()
        
        self.WEBHOOK_USER: str = self._get_env_var(
            'WEBHOOK_USER',
            ''
        )
        
        self.WEBHOOK_PASS: str = self._get_env_var(
            'WEBHOOK_PASS',
            ''
        )
        
        # Validate configuration
        self._validate_config()
    
    def _get_env_var(self, key: str, default: str) -> str:
        """Get environment variable with default value"""
        return os.getenv(key, default)
    
    def _validate_config(self):
        """Validate configuration values"""
        if not self.WEBHOOK_URL.startswith(('http://', 'https://')):
            raise ValueError("WEBHOOK_URL must start with http:// or https://")
        
        if '/' not in self.ALLOWED_IP_RANGE:
            raise ValueError("ALLOWED_IP_RANGE must be in CIDR format (e.g., 192.168.1.0/24)")
        
        if self.WEBHOOK_METHOD not in ['GET', 'POST', 'PUT', 'PATCH', 'HEAD']:
            raise ValueError("WEBHOOK_METHOD must be one of: GET, POST, PUT, PATCH, HEAD")
    
    def __str__(self):
        """String representation (safe for logging)"""
        auth_status = "enabled" if self.WEBHOOK_USER and self.WEBHOOK_PASS else "disabled"
        return f"""VPN Monitor Configuration:
  Allowed IP Range: {self.ALLOWED_IP_RANGE}
  Webhook URL: {self.WEBHOOK_URL}
  Webhook Method: {self.WEBHOOK_METHOD}
  Basic Auth: {auth_status}"""