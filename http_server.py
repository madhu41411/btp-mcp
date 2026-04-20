"""
HTTP wrapper for BTP MCP Server with authentication and health checks.
Provides REST endpoints for external access to MCP tools.
"""

import json
import os
from collections import defaultdict
from functools import wraps
from flask import Flask, request, jsonify, render_template
from datetime import datetime

import anthropic
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


def get_designtime_iflows(package_id=None):
    """Get ALL iflows from design-time (regardless of deployment status)."""
    try:
        packages = client.list_integration_packages(top=200)
        iflows = []
        if isinstance(packages, list):
            for pkg in packages:
                pkg_id = pkg.get("Id")
                pkg_name = pkg.get("Name")
                if not pkg_id:
                    continue
                if package_id and pkg_id.lower() != package_id.lower():
                    continue
                try:
                    arts = client._request(
                        "GET",
                        f"IntegrationPackages('{pkg_id}')/IntegrationDesigntimeArtifacts",
                        params={"$top": 200},
                    )
                    if isinstance(arts, list):
                        for a in arts:
                            iflows.append({
                                "Id": a.get("Id"),
                                "Name": a.get("Name"),
                                "PackageId": pkg_id,
                                "PackageName": pkg_name,
                                "Version": a.get("Version"),
                                "Description": a.get("Description"),
                            })
                except Exception:
                    pass
        return iflows
    except Exception as e:
        return {"error": str(e)}


def get_deployed_iflows():
    """Get only currently deployed iflows from runtime, enriched with package info."""
    try:
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


BTP_TOOLS = [
    {
        "name": "list_all_iflows",
        "description": (
            "List all integration flows (iflows) from design-time. "
            "Returns iflows from ALL packages regardless of deployment status. "
            "Optionally filter by package_id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "package_id": {
                    "type": "string",
                    "description": "Optional package ID to filter iflows by package.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_deployed_iflows",
        "description": (
            "List only the iflows that are currently deployed and running in the SAP BTP runtime. "
            "Use this when the user asks which iflows are deployed, active, or running."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_packages",
        "description": "List all integration packages in the SAP BTP Integration Suite tenant.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_message_stats",
        "description": (
            "Get message processing statistics and logs. Returns total message count, "
            "status breakdown (COMPLETED, FAILED, ERROR), per-iflow counts, and recent messages. "
            "Use for questions about statistics, message counts, or recent activity."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_errors",
        "description": (
            "Get failed and errored messages. Returns count and details of FAILED/ERROR messages. "
            "Use when user asks about errors, failures, or issues."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "deploy_iflow",
        "description": (
            "Deploy a design-time integration flow to the SAP BTP runtime. "
            "The artifact_id is the iflow's unique Id (not the display name). "
            "Call list_all_iflows first to get the correct Id if you only have a name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "artifact_id": {
                    "type": "string",
                    "description": "The unique iflow Id to deploy.",
                }
            },
            "required": ["artifact_id"],
        },
    },
    {
        "name": "undeploy_iflow",
        "description": (
            "Undeploy (stop and remove) a currently deployed integration flow from the SAP BTP runtime. "
            "The artifact_id is the iflow's unique Id. "
            "Call get_deployed_iflows first to confirm it is deployed and get the correct Id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "artifact_id": {
                    "type": "string",
                    "description": "The unique iflow Id to undeploy.",
                }
            },
            "required": ["artifact_id"],
        },
    },
]

_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic_client


def _execute_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name == "list_all_iflows":
        data = get_designtime_iflows(package_id=tool_input.get("package_id"))
        if isinstance(data, dict) and "error" in data:
            return {"error": data["error"]}
        return {"type": "iflows_list", "data": data, "count": len(data)}

    if tool_name == "get_deployed_iflows":
        data = get_deployed_iflows()
        if isinstance(data, dict) and "error" in data:
            return {"error": data["error"]}
        return {"type": "deployment", "data": data, "count": len(data)}

    if tool_name == "list_packages":
        iflows = get_designtime_iflows()
        if isinstance(iflows, dict) and "error" in iflows:
            return {"error": iflows["error"]}
        packages = defaultdict(list)
        for iflow in iflows:
            packages[iflow.get("PackageId", "Unknown")].append(iflow)
        return {"type": "packages", "data": dict(packages), "count": len(packages)}

    if tool_name == "get_message_stats":
        stats = get_iflow_stats()
        if isinstance(stats, dict) and "error" in stats:
            return {"error": stats["error"]}
        return {
            "type": "statistics",
            "data": stats,
            "total_messages": stats.get("total_messages", 0),
            "by_status": dict(stats.get("by_status", {})),
        }

    if tool_name == "get_errors":
        stats = get_iflow_stats()
        if isinstance(stats, dict) and "error" in stats:
            return {"error": stats["error"]}
        errors = stats.get("errors", [])
        failed_count = (
            stats.get("by_status", {}).get("FAILED", 0)
            + stats.get("by_status", {}).get("ERROR", 0)
        )
        return {
            "type": "errors",
            "data": {
                "failed_count": failed_count,
                "errors": errors,
                "by_status": dict(stats.get("by_status", {})),
            },
        }

    if tool_name == "deploy_iflow":
        artifact_id = tool_input["artifact_id"]
        try:
            task_id = client.deploy_artifact(artifact_id)
            return {"success": True, "message": f"Deployment of '{artifact_id}' started.", "task_id": task_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    if tool_name == "undeploy_iflow":
        artifact_id = tool_input["artifact_id"]
        try:
            client.undeploy_artifact(artifact_id)
            return {"success": True, "message": f"'{artifact_id}' undeployed successfully."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"error": f"Unknown tool: {tool_name}"}


def process_query(user_query: str) -> dict:
    """Run user query through Claude with BTP tools and return a structured response."""
    ac = _get_anthropic_client()
    messages = [{"role": "user", "content": user_query}]
    system_prompt = (
        "You are an assistant for SAP BTP Integration Suite. "
        "You have tools to list iflows, check deployment status, deploy/undeploy iflows, "
        "and retrieve message processing statistics and errors. "
        "Always call the appropriate tool to get live data before answering. "
        "When reporting iflow lists or deployment data, include the iflow Id, Name, and PackageName. "
        "Be concise and factual."
    )

    last_tool_result = None

    while True:
        response = ac.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            system=system_prompt,
            tools=BTP_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tu in tool_uses:
                result = _execute_tool(tu.name, tu.input)
                last_tool_result = result
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result),
                })
            messages.append({"role": "user", "content": tool_results})

        else:
            text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            result_type = "text"
            result_data = None
            if last_tool_result:
                result_type = last_tool_result.get("type", "text")
                result_data = last_tool_result.get("data")
            return {"type": result_type, "data": result_data, "summary": text}

    # unreachable — loop always exits via the else branch above


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
    """List all design-time iflows, optionally filtered by package_id."""
    try:
        package_id = request.args.get('package_id', None, type=str)
        iflows = get_designtime_iflows(package_id=package_id)
        if isinstance(iflows, dict) and "error" in iflows:
            return jsonify({"success": False, "error": iflows["error"]}), 500
        return jsonify({"success": True, "data": iflows, "count": len(iflows)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/deployed', methods=['GET'])
@require_api_key
def list_deployed_api():
    """List only currently deployed (runtime) iflows."""
    try:
        iflows = get_deployed_iflows()
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

@app.route('/api/deploy/<artifact_id>', methods=['POST'])
@require_api_key
def deploy_artifact(artifact_id):
    """Deploy a design-time integration artifact."""
    try:
        task_id = client.deploy_artifact(artifact_id)
        return jsonify({"success": True, "message": f"'{artifact_id}' deployment started.", "task_id": task_id}), 202
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/undeploy/<artifact_id>', methods=['DELETE'])
@require_api_key
def undeploy_artifact(artifact_id):
    """Undeploy a runtime integration artifact."""
    try:
        client.undeploy_artifact(artifact_id)
        return jsonify({"success": True, "message": f"'{artifact_id}' undeployed successfully"}), 200
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
