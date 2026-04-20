#!/usr/bin/env python3.11
import sys
import os
from pathlib import Path

# Set working directory
os.chdir(Path(__file__).parent)
sys.path.insert(0, 'src')

from app import app, init_client

if __name__ == '__main__':
    # Kill any existing process on 8080 first
    os.system('lsof -ti:8080 | xargs kill -9 2>/dev/null || true')
    
    print("🚀 Initializing BTP Integration Suite client...")
    if not init_client():
        print("❌ Failed to initialize BTP client!")
        sys.exit(1)
    
    print("✓ Client initialized successfully")
    print("📱 Open your browser at: http://localhost:8081")
    print("⏹️  Press Ctrl+C to stop the server\n")
    app.run(debug=False, host='0.0.0.0', port=8081)
