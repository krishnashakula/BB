#!/usr/bin/env python3
"""
Railway startup script that properly handles the PORT environment variable
"""
import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Start the uvicorn server with proper port handling"""
    
    # Get port from environment variable, default to 8000
    port = os.getenv("PORT", "8000")
    
    # Validate port
    try:
        port_int = int(port)
        if not (1 <= port_int <= 65535):
            raise ValueError(f"Port {port_int} is out of valid range")
    except ValueError as e:
        logger.error(f"Invalid PORT value '{port}': {e}")
        sys.exit(1)
    
    logger.info(f"🚀 Starting Binaural Beats Generator on port {port}")
    logger.info(f"🌐 Environment: {os.getenv('ENVIRONMENT', 'unknown')}")
    logger.info(f"🔑 JWT Secret configured: {'Yes' if os.getenv('JWT_SECRET') else 'No'}")
    
    # Build uvicorn command
    cmd = [
        "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--workers", "1",
        "--log-level", "info",
        "--access-log"
    ]
    
    logger.info(f"🔧 Running command: {' '.join(cmd)}")
    
    try:
        # Start uvicorn
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
