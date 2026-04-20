"""
HTTP wrapper for BTP MCP Server with authentication and health checks.
Provides REST endpoints for external access to MCP tools.
"""

import os
from collections import defaultdict, OrderedDict
from functools import wraps
from flask import Flask, request, jsonify, render_template
from datetime import datetime

from btp_mcp.client import SapBtpClient
from btp_mcp.config import get_settings

app = Flask(__name__, template_folder='templates')

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


def get_all_iflows():
    """Get deployed iflows enriched with package info."""
    try:
        # Build iflow_id -> package mapping from design-time
        pkg_map = {}
        packages = client.list_integration_packages(top=200)
        if isinstance(packages, list):
            for pkg in packages:
                pkg_id = pkg.get("Id")
                pkg_name = pkg.get("Name")
                if not pkg_id:
                    continue
                try:
                    arts = client._request(
                        "GET",
                        f"IntegrationPackages('{pkg_id}')/IntegrationDesigntimeArtifacts",
                        params={"$top": 200},
                    )
                    if isinstance(arts, list):
                        for a in arts:
                            pkg_map[a.get("Id")] = {"PackageId": pkg_id, "PackageName": pkg_name}
                except Exception:
                    pass

        # Get runtime status
        runtime = client._request("GET", "IntegrationRuntimeArtifacts", params={"$top": 200})
        if not isinstance(runtime, list):
            runtime = [runtime]

        iflows = []
        for a in runtime:
            if a.get("Type", "").upper() != "INTEGRATION_FLOW":
                continue
            iflow_id = a.get("Id")
            pkg_info = pkg_map.get(iflow_id, {"PackageId": None, "PackageName": None})
            iflows.append({
                "Id": iflow_id,
                "Name": a.get("Name"),
                "PackageId": pkg_info["PackageId"],
                "PackageName": pkg_info["PackageName"],
                "Type": a.get("Type"),
                "Status": a.get("Status"),
                "Version": a.get("Version"),
            })
        return iflows
    except Exception as e:
        return {"error": str(e)}


def get_iflow_stats(iflow_id=None):
    """Get runtime statistics for active integration flows."""
    try:
        logs = client.get_message_processing_logs(top=2000)
        stats = {
            "total_messages": len(logs),
            "by_status": defaultdict(int),
            "by_iflow": defaultdict(lambda: {"count": 0, "statuses": defaultdict(int)}),
            "errors": [],
            "messages": [],
        }

        for log in logs:
            artifact = log.get("IntegrationArtifact")
            status = log.get("Status", "UNKNOWN")
            stats["by_status"][status] += 1

            artifact_id = None
            artifact_name = None
            if artifact:
                artifact_id = artifact.get("Id")
                artifact_name = artifact.get("Name")
                if artifact_id:
                    stats["by_iflow"][artifact_id]["count"] += 1
                    stats["by_iflow"][artifact_id]["statuses"][status] += 1
                    stats["by_iflow"][artifact_id]["name"] = artifact_name

            stats["messages"].append({
                "MessageGuid": log.get("MessageGuid"),
                "CorrelationId": log.get("CorrelationId"),
                "Status": status,
                "IFlowName": artifact_name or artifact_id,
                "LogStart": log.get("LogStart"),
                "DurationInMs": log.get("DurationInMs"),
            })

            if status in {"FAILED", "ERROR"}:
                error_info = log.get("ErrorInformation")
                if error_info:
                    stats["errors"].append({
                        "iflow": artifact_name or artifact_id,
                        "status": status,
                        "timestamp": log.get("LogStart")
                    })

        if iflow_id:
            if iflow_id in stats["by_iflow"]:
                return {"iflow": iflow_id, "stats": stats["by_iflow"][iflow_id]}
            return {"error": f"iFlow {iflow_id} not found"}

        return stats
    except Exception as e:
        return {"error": str(e)}


def process_query(user_query):
    """Convert a user query into a response payload."""
    query_lower = user_query.lower()
    response = {"type": "text", "data": None}
    try:
        if any(keyword in query_lower for keyword in ["error", "failed", "failure", "issues"]):
            stats = get_iflow_stats()
            errors = stats.get("errors", [])
            failed_count = stats.get("by_status", {}).get("FAILED", 0) + stats.get("by_status", {}).get("ERROR", 0)
            response["type"] = "errors"
            response["data"] = {"failed_count": failed_count, "errors": errors, "by_status": dict(stats.get("by_status", {}))}
            response["summary"] = f"Found {failed_count} failed/error messages"
        elif any(keyword in query_lower for keyword in ["package", "packages"]):
            iflows = get_all_iflows()
            packages = defaultdict(list)
            if isinstance(iflows, dict) and "error" in iflows:
                response["type"] = "error"
                response["data"] = iflows
                response["summary"] = f"Error: {iflows['error']}"
            else:
                for iflow in iflows:
                    pkg_id = iflow.get("PackageId", "Unknown")
                    packages[pkg_id].append(iflow)
                response["type"] = "packages"
                response["data"] = dict(packages)
                response["summary"] = f"Found {len(packages)} packages"
        elif any(keyword in query_lower for keyword in ["statistics", "stats", "summary", "count", "how many"]):
            stats = get_iflow_stats()
            response["type"] = "statistics"
            response["data"] = stats
            response["summary"] = f"Total messages: {stats.get('total_messages', 0)}, Status breakdown: {dict(stats.get('by_status', {}))}"
        elif any(keyword in query_lower for keyword in ["deployment", "deploy", "status"]):
            iflows = get_all_iflows()
            if isinstance(iflows, dict) and "error" in iflows:
                response["type"] = "error"
                response["data"] = iflows
                response["summary"] = f"Error: {iflows['error']}"
            else:
                response["type"] = "deployment"
                response["data"] = iflows
                response["summary"] = f"{len(iflows)} iflows deployed and active"
        elif any(keyword in query_lower for keyword in ["list", "show", "all", "iflows", "flows"]):
            iflows = get_all_iflows()
            if isinstance(iflows, dict) and "error" in iflows:
                response["type"] = "error"
                response["data"] = iflows
                response["summary"] = f"Error: {iflows['error']}"
            else:
                response["type"] = "iflows_list"
                response["data"] = iflows
                response["summary"] = f"Found {len(iflows)} active iflows"
        elif "iflow" in query_lower or "flow" in query_lower:
            iflows = get_all_iflows()
            if isinstance(iflows, dict) and "error" in iflows:
                response["type"] = "error"
                response["data"] = iflows
                response["summary"] = f"Error: {iflows['error']}"
            else:
                keywords = query_lower.split()
                matching = [i for i in iflows if any(k in (i.get("Name", "") or "").lower() or k in (i.get("Id", "") or "").lower() for k in keywords)]
                response["type"] = "iflows_list"
                response["data"] = matching
                response["summary"] = f"Found {len(matching)} matching iflows"
        else:
            response["type"] = "help"
            response["data"] = {
                "suggestions": [
                    "List all iflows",
                    "Show statistics",
                    "List packages",
                    "Check deployment status",
                    "Show errors",
                    "Search for specific iflow"
                ]
            }
            response["summary"] = "I can help you with iflow information. Try asking about: iflows, statistics, packages, deployment status, or errors."

        return response
    except Exception as e:
        return {"type": "error", "data": {"error": str(e)}, "summary": f"Error processing query: {str(e)}"}


@app.route('/', methods=['GET'])
def index():
    """Serve the main UI page."""
    return render_template('index.html')


@app.route('/api/docs', methods=['GET'])
def api_docs():
    """Return API documentation for the deployed MCP service."""
    return jsonify({
        "service": "BTP Integration Suite MCP Server",
        "version": "1.0",
        "endpoints": {
            "GET /health": "Health check (no auth required)",
            "GET /api/ping": "Check BTP connectivity",
            "GET /api/packages": "List integration packages",
            "GET /api/artifacts": "List integration artifacts",
            "GET /api/logs": "Get message processing logs",
            "GET /api/iflows": "List active iflows from runtime logs",
            "GET /api/stats": "Return runtime message processing statistics",
            "GET /api/errors": "Return failed/error message details",
            "POST /api/chat": "Chat query endpoint for the UI"
        },
        "authentication": "Use X-API-Key header for API endpoints, UI is served securely from the same service."
    }), 200


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages from the web UI."""
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({"error": "Empty message"}), 400
        result = process_query(user_message)
        return jsonify({"user_message": user_message, "response": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
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

@app.route('/api/iflows', methods=['GET'])
@require_api_key
def list_iflows_api():
    """List active iflows from recent runtime logs."""
    try:
        iflows = get_all_iflows()
        if isinstance(iflows, dict) and "error" in iflows:
            return jsonify({"success": False, "error": iflows["error"]}), 500
        return jsonify({"success": True, "data": iflows, "count": len(iflows)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@require_api_key
def stats_api():
    """Return runtime message processing statistics."""
    try:
        iflow_id = request.args.get('iflow_id', None, type=str)
        stats = get_iflow_stats(iflow_id=iflow_id if iflow_id else None)
        if isinstance(stats, dict) and "error" in stats and iflow_id:
            return jsonify({"success": False, "error": stats["error"]}), 404
        return jsonify({"success": True, "data": stats}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/errors', methods=['GET'])
@require_api_key
def errors_api():
    """Return failed/error message details."""
    try:
        stats = get_iflow_stats()
        errors = stats.get("errors", []) if isinstance(stats, dict) else []
        return jsonify({"success": True, "data": {"failed_count": stats.get("by_status", {}).get("FAILED", 0) + stats.get("by_status", {}).get("ERROR", 0), "errors": errors, "by_status": dict(stats.get("by_status", {}))}}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
