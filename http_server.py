"""
HTTP wrapper for BTP MCP Server with authentication and health checks.
Provides REST endpoints for external access to MCP tools.
"""

import os
import json
from functools import wraps
from flask import Flask, request, jsonify
from datetime import datetime

from btp_mcp.client import SapBtpClient
from btp_mcp.config import get_settings

app = Flask(__name__)

# Initialize BTP client
client = None
api_key = os.getenv('API_KEY')

def init_client():
    """Initialize BTP client"""
    global client
    try:
        settings = get_settings()
        client = SapBtpClient(settings)
        # Test connection
        client._get_token()
        return True
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        return False

def require_api_key(f):
    """Decorator to require API key for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not api_key:
            # If no API key configured, allow access (development mode)
            return f(*args, **kwargs)
        
        token = request.headers.get('X-API-Key')
        if not token or token != api_key:
            return jsonify({"error": "Unauthorized"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Test BTP connection
        if client:
            client._get_token()
            status = "healthy"
        else:
            status = "unhealthy"
    except Exception as e:
        status = "unhealthy"
        error = str(e)
        return jsonify({
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "error": error
        }), 503
    
    return jsonify({
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "btp-mcp-server"
    }), 200

@app.route('/api/ping', methods=['GET'])
@require_api_key
def ping():
    """Check SAP BTP connectivity"""
    try:
        result = client.ping()
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/packages', methods=['GET'])
@require_api_key
def list_packages():
    """List integration packages"""
    try:
        top = request.args.get('top', 25, type=int)
        skip = request.args.get('skip', 0, type=int)
        packages = client.list_integration_packages(top=top, skip=skip)
        return jsonify({"success": True, "data": packages, "count": len(packages)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/artifacts', methods=['GET'])
@require_api_key
def list_artifacts():
    """List integration artifacts"""
    try:
        top = request.args.get('top', 50, type=int)
        skip = request.args.get('skip', 0, type=int)
        package_id = request.args.get('package_id', None, type=str)
        
        artifacts = client.list_artifacts(top=top, skip=skip, package_id=package_id)
        return jsonify({"success": True, "data": artifacts, "count": len(artifacts)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logs', methods=['GET'])
@require_api_key
def get_logs():
    """Get message processing logs"""
    try:
        status = request.args.get('status', None, type=str)
        top = request.args.get('top', 100, type=int)
        skip = request.args.get('skip', 0, type=int)
        
        logs = client.get_message_processing_logs(
            status=status,
            top=top,
            skip=skip
        )
        return jsonify({"success": True, "data": logs, "count": len(logs)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """API documentation"""
    return jsonify({
        "service": "BTP Integration Suite MCP Server",
        "version": "1.0",
        "endpoints": {
            "GET /health": "Health check (no auth required)",
            "GET /api/ping": "Check BTP connectivity",
            "GET /api/packages": "List integration packages",
            "GET /api/artifacts": "List integration artifacts",
            "GET /api/logs": "Get message processing logs"
        },
        "authentication": "Use X-API-Key header for requests",
        "documentation": "https://github.com/yourusername/btp-mcp"
    }), 200

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print("🚀 Initializing BTP MCP Server...")
    if not init_client():
        print("❌ Failed to initialize client!")
        exit(1)
    
    print("✓ Client initialized successfully")
    print("📱 Starting HTTP server on port 8000")
    
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
