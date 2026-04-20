#!/usr/bin/env python3
"""
Flask web application for BTP Integration Suite interaction.
Provides a chat-like UI for querying iflow information.
"""

import sys
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from collections import defaultdict, OrderedDict
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from btp_mcp.client import SapBtpClient
from btp_mcp.config import get_settings

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Global client instance
client = None

def init_client():
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

def get_all_iflows():
    """Get all active integration flows from message processing logs.
    
    Queries the MessageProcessingLogs API to extract all unique integration flows
    that have recent message activity. Returns deduplicated iflow information.
    
    Each iflow object includes:
    - Id: Unique identifier for the integration flow
    - Name: Display name of the iflow
    - PackageId: ID of the package containing this iflow
    - PackageName: Name of the package
    - Type: Always \"INTEGRATION_FLOW\" for iflows
    
    Returns:
        List of iflow dictionaries with Name, Id, PackageId, PackageName, and Type.
        Returns error dict if API call fails.
        
    Note:
        Only returns iflows with recent message activity (logs within configured window).
        Design-time API limitations mean this shows runtime-active iflows only.
    """
    try:
        print("[DEBUG] Fetching message processing logs...")
        logs = client.get_message_processing_logs(top=2000)
        print(f"[DEBUG] Got {len(logs)} logs from API")
        
        iflows_dict = OrderedDict()
        
        for log in logs:
            artifact = log.get("IntegrationArtifact")
            if artifact and artifact.get("Type") == "INTEGRATION_FLOW":
                artifact_id = artifact.get("Id")
                if artifact_id and artifact_id not in iflows_dict:
                    iflows_dict[artifact_id] = {
                        "Id": artifact_id,
                        "Name": artifact.get("Name"),
                        "PackageId": artifact.get("PackageId"),
                        "PackageName": artifact.get("PackageName"),
                        "Type": artifact.get("Type")
                    }
        
        print(f"[DEBUG] Extracted {len(iflows_dict)} unique iflows")
        result = list(iflows_dict.values())
        print(f"[DEBUG] Returning {len(result)} iflows")
        return result
    except Exception as e:
        print(f"[DEBUG] Error in get_all_iflows: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def get_iflow_stats(iflow_id=None):
    """Get statistics about iflows from message processing logs.
    
    Aggregates message processing log data to provide statistics including:
    - total_messages: Total number of messages processed
    - by_status: Count of messages grouped by status (COMPLETED, FAILED, ERROR, etc.)
    - by_iflow: Statistics per iflow including:
      * count: Total messages for this iflow
      * name: Name of the integration flow
      * statuses: Breakdown of message statuses for this iflow
    - errors: List of error details with iflow name and timestamp
    
    Each iflow entry includes runtime statistics:
    - Total message count
    - Status breakdown (successful vs failed)
    - Associated package information
    
    Args:
        iflow_id: Optional specific iflow ID to get stats for
        
    Returns:
        Dictionary with aggregated statistics about message processing by iflow.
        If iflow_id specified, returns stats for that specific iflow only.
        
    Note:
        Only includes iflows with recent message activity (within log retention).
    """
    try:
        logs = client.get_message_processing_logs(top=2000)
        
        stats = {
            "total_messages": len(logs),
            "by_status": defaultdict(int),
            "by_iflow": defaultdict(lambda: {"count": 0, "statuses": defaultdict(int)}),
            "errors": []
        }
        
        for log in logs:
            artifact = log.get("IntegrationArtifact")
            if artifact:
                artifact_id = artifact.get("Id")
                artifact_name = artifact.get("Name")
                status = log.get("Status", "UNKNOWN")
                
                stats["by_status"][status] += 1
                
                if artifact_id:
                    stats["by_iflow"][artifact_id]["count"] += 1
                    stats["by_iflow"][artifact_id]["statuses"][status] += 1
                    stats["by_iflow"][artifact_id]["name"] = artifact_name
                
                # Collect errors
                if status == "FAILED" or status == "ERROR":
                    error_info = log.get("ErrorInformation")
                    if error_info:
                        stats["errors"].append({
                            "iflow": artifact_name or artifact_id,
                            "status": status,
                            "timestamp": log.get("LogStart")
                        })
        
        # Filter by specific iflow if requested
        if iflow_id:
            if iflow_id in stats["by_iflow"]:
                return {"iflow": iflow_id, "stats": stats["by_iflow"][iflow_id]}
            else:
                return {"error": f"iFlow {iflow_id} not found"}
        
        return stats
    except Exception as e:
        return {"error": str(e)}

def process_query(user_query):
    """Process natural language queries about iflows and packages.
    
    Supports queries like:
    - \"List all iflows\" - Returns all active integration flows with:
      * Name: Display name
      * Id: Unique identifier
      * PackageId: Package containing this iflow
      * PackageName: Name of the package
      * Type: Always \"INTEGRATION_FLOW\"
      
    - \"Show statistics\" - Returns message processing statistics:
      * Total messages processed
      * Breakdown by status (COMPLETED, FAILED, ERROR, etc.)
      * Per-iflow statistics with message counts
      * Error details and timestamps
      
    - \"List packages\" - Returns packages grouped by ID:
      * PackageId: Unique package identifier
      * PackageName: Display name
      * iflows_count: Number of iflows in package
      
    - \"Check deployment status\" - Shows deployed iflows:
      * Which iflows are active in runtime
      * Package they belong to
      * Deployment details
      
    - \"Show errors\" - Returns failure information:
      * Failed/error message count
      * Status breakdown (COMPLETED vs FAILED vs ERROR)
      * Details of failed messages with timestamps
    
    Args:
        user_query: Natural language question from user
        
    Returns:
        Dictionary with:
        - type: Response type (iflows_list, statistics, packages, errors, deployment, help, error)
        - data: Response data appropriate for the type
        - summary: Human-readable summary of findings
    """
    query_lower = user_query.lower()
    print(f"[DEBUG] Processing query: {user_query}")
    response = {"type": "text", "data": None}
    
    try:
        # List all iflows
        if any(keyword in query_lower for keyword in ["list", "show", "all", "iflows", "flows"]):
            print("[DEBUG] Matched 'list iflows' pattern")
            iflows = get_all_iflows()
            print(f"[DEBUG] Got iflows: type={type(iflows)}, len={len(iflows) if isinstance(iflows, list) else 'N/A'}")
            
            # Handle error response
            if isinstance(iflows, dict) and "error" in iflows:
                response["type"] = "error"
                response["data"] = iflows
                response["summary"] = f"Error: {iflows['error']}"
            else:
                response["type"] = "iflows_list"
                response["data"] = iflows if isinstance(iflows, list) else []
                count = len(iflows) if isinstance(iflows, list) else 0
                response["summary"] = f"Found {count} active iflows"
            print(f"[DEBUG] Response summary: {response['summary']}")
        
        # Get statistics
        elif any(keyword in query_lower for keyword in ["statistics", "stats", "summary", "count", "how many"]):
            stats = get_iflow_stats()
            response["type"] = "statistics"
            response["data"] = stats
            response["summary"] = f"Total messages: {stats['total_messages']}, Status breakdown: {dict(stats['by_status'])}"
        
        # Get package details
        elif any(keyword in query_lower for keyword in ["package", "packages"]):
            iflows = get_all_iflows()
            packages = defaultdict(list)
            for iflow in iflows:
                pkg_id = iflow.get("PackageId", "Unknown")
                packages[pkg_id].append(iflow)
            
            response["type"] = "packages"
            response["data"] = dict(packages)
            response["summary"] = f"Found {len(packages)} packages"
        
        # Get deployment status
        elif any(keyword in query_lower for keyword in ["deployment", "deploy", "status"]):
            iflows = get_all_iflows()
            response["type"] = "deployment"
            response["data"] = iflows
            response["summary"] = f"{len(iflows)} iflows deployed and active"
        
        # Get error information
        elif any(keyword in query_lower for keyword in ["error", "failed", "failure", "issues"]):
            stats = get_iflow_stats()
            errors = stats.get("errors", [])
            failed_count = stats["by_status"].get("FAILED", 0) + stats["by_status"].get("ERROR", 0)
            response["type"] = "errors"
            response["data"] = {"failed_count": failed_count, "errors": errors, "by_status": dict(stats["by_status"])}
            response["summary"] = f"Found {failed_count} failed/error messages"
        
        # Search specific iflow
        elif "iflow" in query_lower or "flow" in query_lower:
            iflows = get_all_iflows()
            keywords = query_lower.split()
            matching = [i for i in iflows if any(k in i.get("Name", "").lower() or k in i.get("Id", "").lower() for k in keywords)]
            response["type"] = "iflows_list"
            response["data"] = matching
            response["summary"] = f"Found {len(matching)} matching iflows"
        
        # Default: show help
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
        return {
            "type": "error",
            "data": {"error": str(e)},
            "summary": f"Error processing query: {str(e)}"
        }

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({"error": "Empty message"}), 400
        
        # Process the query
        result = process_query(user_message)
        
        return jsonify({
            "user_message": user_message,
            "response": result
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "connected": client is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/iflows', methods=['GET'])
def get_iflows():
    """API endpoint to get all iflows"""
    try:
        iflows = get_all_iflows()
        return jsonify({"success": True, "data": iflows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """API endpoint to get statistics"""
    try:
        stats = get_iflow_stats()
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("Initializing BTP Integration Suite client...")
    if init_client():
        print("✓ Client initialized successfully")
        print("🚀 Starting web server at http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("✗ Failed to initialize client")
        sys.exit(1)
