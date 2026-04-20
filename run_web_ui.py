#!/usr/bin/env python3.11
"""
Launcher script for BTP Integration Suite Web UI
Runs Flask app on port 8080
"""

from app import app

if __name__ == '__main__':
    print("🚀 Starting BTP Integration Suite Web UI...")
    print("📱 Open your browser at: http://localhost:8080")
    print("⏹️  Press Ctrl+C to stop the server\n")
    app.run(debug=False, host='0.0.0.0', port=8080)
