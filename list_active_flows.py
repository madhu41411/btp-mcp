#!/usr/bin/env python3
"""
Alternative script: List integration flows from runtime monitoring logs.
Since design-time artifact APIs require additional permissions, this script
lists the iflows that have recently processed messages.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from btp_mcp.client import SapBtpClient
from btp_mcp.config import get_settings


def main():
    try:
        print("🔌 Connecting to SAP BTP Integration Suite...")
        settings = get_settings()
        client = SapBtpClient(settings)

        # Ping to verify connectivity
        print("✓ Verifying connection...")
        ping_result = client.ping()
        print(f"✓ Connected to: {ping_result['base_url']}\n")

        # Get message processing logs
        print("📊 Fetching message processing logs...")
        logs = client.get_message_processing_logs(top=1000)
        print(f"✓ Retrieved {len(logs)} message processing log entries\n")

        # Group by artifact to identify active iflows
        flows_dict = defaultdict(lambda: {"count": 0, "statuses": defaultdict(int)})
        
        for log in logs:
            artifact_id = log.get("ArtifactId", "Unknown")
            artifact_name = log.get("IntegrationFlowName", artifact_id)
            status = log.get("Status", "Unknown")
            
            flows_dict[artifact_id]["name"] = artifact_name
            flows_dict[artifact_id]["count"] += 1
            flows_dict[artifact_id]["statuses"][status] += 1

        # Sort by message count
        sorted_flows = sorted(flows_dict.items(), key=lambda x: x[1]["count"], reverse=True)

        print("🎯 ACTIVE INTEGRATION FLOWS (from runtime logs):\n")
        print("=" * 100)

        for i, (flow_id, flow_data) in enumerate(sorted_flows, 1):
            name = flow_data.get("name", flow_id)
            count = flow_data["count"]
            statuses = flow_data["statuses"]
            
            status_str = ", ".join([f"{status}: {cnt}" for status, cnt in statuses.items()])
            
            print(f"\n{i}. {name}")
            print(f"   ID: {flow_id}")
            print(f"   Total Messages: {count}")
            print(f"   Status Breakdown: {status_str}")

        print("\n" + "=" * 100)
        print(f"\n✅ Total active flows found: {len(sorted_flows)}")
        print("\nNote: This shows flows that have recent message processing activity.")
        print("For a complete list of ALL iflows (including inactive ones),")
        print("you'll need OData API access to the design-time artifacts.")

        # Export to JSON
        output_file = Path(__file__).parent / "active_flows.json"
        with open(output_file, "w") as f:
            json.dump([
                {"id": flow_id, **flow_data} 
                for flow_id, flow_data in sorted_flows
            ], f, indent=2)
        print(f"📄 Details exported to: {output_file}")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
