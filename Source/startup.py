#!/usr/bin/env python3

import os
import sys
import time
import signal
import subprocess
import logging
from datetime import datetime
from threading import Thread
import multiprocessing

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] STARTUP: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class VPNMonitorContainer:
    def __init__(self):
        self.log_file = '/var/log/vpn-monitor.log'
        self.cron_process = None
        self.web_process = None
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Ensure log directory exists
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging infrastructure"""
        try:
            os.makedirs('/var/log', exist_ok=True)
            
            # Create log file if it doesn't exist
            if not os.path.exists(self.log_file):
                with open(self.log_file, 'w') as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: VPN Monitor log file created\n")
            
            # Make log file world-writable for the container
            os.chmod(self.log_file, 0o666)
            
            logger.info(f"Log file ready: {self.log_file}")
            
            # Write startup to log file
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Container startup initiated\n")
                
        except Exception as e:
            logger.error(f"Failed to setup logging: {e}")
    
    def setup_cron(self):
        """Setup cron for scheduled monitoring"""
        try:
            cron_schedule = os.getenv('CRON_SCHEDULE', '0 */12 * * *')
            logger.info(f"Setting up cron with schedule: {cron_schedule}")
            
            # Write startup log
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Setting up cron schedule: {cron_schedule}\n")
            
            # Create crontab content
            cron_entry = f"{cron_schedule} cd /app && python monitor.py\n"
            
            # Write crontab
            with open('/etc/crontabs/root', 'w') as f:
                f.write(cron_entry)
            
            logger.info("Crontab created successfully")
            
            # Start cron daemon
            self.cron_process = subprocess.Popen(
                ['crond', '-f', '-l', '2'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Cron daemon started with PID: {self.cron_process.pid}")
            
            # Log to file
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Cron daemon started (PID: {self.cron_process.pid})\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup cron: {e}")
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to setup cron: {e}\n")
            return False
    
    def run_initial_check(self):
        """Run initial IP check"""
        try:
            logger.info("Running initial IP check...")
            
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Running initial IP check\n")
            
            # Import and run monitor
            from monitor import VPNMonitor
            monitor = VPNMonitor()
            monitor.run_check()
            
            logger.info("Initial check completed")
            
        except Exception as e:
            logger.error(f"Initial check failed: {e}")
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Initial check failed: {e}\n")
    
    def start_web_server(self):
        """Start the web server in a separate process"""
        try:
            web_port = int(os.getenv('WEB_PORT', 8080))
            logger.info(f"Starting web server on port {web_port}")
            
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Starting web server on port {web_port}\n")
            
            # Start web server with proper output handling
            self.web_process = subprocess.Popen([
                sys.executable, 'app.py'
            ], 
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
            )
            
            logger.info(f"Web server started with PID: {self.web_process.pid}")
            
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Web server started (PID: {self.web_process.pid})\n")
            
            # Give it a moment to start
            time.sleep(1)
            
            # Check if it's still running
            if self.web_process.poll() is None:
                return True
            else:
                # Process died immediately, get the error
                output, _ = self.web_process.communicate(timeout=1)
                logger.error(f"Web server died immediately: {output}")
                with open(self.log_file, 'a') as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Web server died immediately: {output}\n")
                return False
            
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to start web server: {e}\n")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        
        with open(self.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Received shutdown signal {signum}\n")
        
        self.running = False
        self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of all processes"""
        logger.info("Shutting down container...")
        
        with open(self.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Container shutdown initiated\n")
        
        # Stop web server
        if self.web_process and self.web_process.poll() is None:
            logger.info("Stopping web server...")
            self.web_process.terminate()
            try:
                self.web_process.wait(timeout=5)
                logger.info("Web server stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Web server didn't stop gracefully, killing...")
                self.web_process.kill()
        
        # Stop cron
        if self.cron_process and self.cron_process.poll() is None:
            logger.info("Stopping cron daemon...")
            self.cron_process.terminate()
            try:
                self.cron_process.wait(timeout=5)
                logger.info("Cron daemon stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Cron didn't stop gracefully, killing...")
                self.cron_process.kill()
        
        with open(self.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Container shutdown completed\n")
        
        logger.info("Container shutdown completed")
    
    def monitor_processes(self):
        """Monitor running processes and restart if needed"""
        restart_count = 0
        max_restarts = 5
        restart_window = 300  # 5 minutes
        last_restart = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Reset restart count if enough time has passed
                if current_time - last_restart > restart_window:
                    restart_count = 0
                
                # Check cron process
                if self.cron_process and self.cron_process.poll() is not None:
                    logger.error("Cron process died, restarting...")
                    with open(self.log_file, 'a') as f:
                        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Cron process died, restarting\n")
                    self.setup_cron()
                
                # Check web process
                if self.web_process and self.web_process.poll() is not None:
                    if restart_count < max_restarts:
                        logger.error(f"Web process died, restarting... (attempt {restart_count + 1}/{max_restarts})")
                        with open(self.log_file, 'a') as f:
                            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Web process died, restarting (attempt {restart_count + 1})\n")
                        
                        restart_count += 1
                        last_restart = current_time
                        
                        # Wait a bit before restarting
                        time.sleep(5)
                        
                        if self.start_web_server():
                            logger.info("Web server restarted successfully")
                        else:
                            logger.error("Failed to restart web server")
                    else:
                        logger.error(f"Web process died too many times ({max_restarts} restarts in {restart_window}s), giving up")
                        with open(self.log_file, 'a') as f:
                            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Web process died too many times, giving up\n")
                        self.running = False
                        break
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Process monitor error: {e}")
                time.sleep(10)
    
    def run(self):
        """Main container run method"""
        logger.info("=" * 60)
        logger.info("VPN Monitor Container Starting")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        try:
            # Setup cron
            if not self.setup_cron():
                logger.error("Failed to setup cron, exiting")
                return 1
            
            # Run initial check
            self.run_initial_check()
            
            # Start web server
            if not self.start_web_server():
                logger.error("Failed to start web server, exiting")
                return 1
            
            # Wait a bit for services to start
            time.sleep(3)
            
            # Verify web server is still running after startup
            if self.web_process and self.web_process.poll() is not None:
                logger.error("Web server died immediately after startup")
                # Try to get any error output
                try:
                    output, _ = self.web_process.communicate(timeout=1)
                    logger.error(f"Web server error output: {output}")
                except:
                    pass
                return 1
            
            logger.info("All services started successfully")
            logger.info("Container is now running and monitoring...")
            
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: All services started, container fully operational\n")
            
            # Start process monitoring in background thread
            monitor_thread = Thread(target=self.monitor_processes, daemon=True)
            monitor_thread.start()
            
            # Main loop - just keep container alive
            while self.running:
                time.sleep(10)
            
            logger.info("Main loop exited")
            return 0
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            self.shutdown()
            return 130
        except Exception as e:
            logger.error(f"Container startup failed: {e}")
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Container startup failed: {e}\n")
            return 1

def main():
    """Main entry point"""
    container = VPNMonitorContainer()
    exit_code = container.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
