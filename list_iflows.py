#!/usr/bin/env python3
"""
Helper script to list all iflows from SAP BTP Integration Suite.
Extracts iflows from message processing logs.
"""

import sys
import json
from pathlib import Path
from collections import OrderedDict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from btp_mcp.client import SapBtpClient
from btp_mcp.config import get_settings


def main():
    try:
        print("🔌 Connecting to SAP BTP Integration Suite...")
        settings = get_settings()
        client = SapBtpClient(settings)

        print("✓ Verifying connection...")
        
        # Get message processing logs to extract iflow info
        print("📊 Fetching message processing logs to identify iflows...\n")
        logs = client.get_message_processing_logs(top=2000)
        print(f"✓ Retrieved {len(logs)} message processing log entries")

        # Extract unique iflows from logs
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

        iflows = list(iflows_dict.values())
        print(f"✓ Found {len(iflows)} unique INTEGRATION FLOWS:\n")
        print("=" * 100)

        for i, iflow in enumerate(iflows, 1):
            name = iflow.get("Name", "N/A")
            artifact_id = iflow.get("Id", "N/A")
            package_name = iflow.get("PackageName", "N/A")
            package_id = iflow.get("PackageId", "N/A")

            print(f"\n{i}. {name}")
            print(f"   ID: {artifact_id}")
            print(f"   Package: {package_name} ({package_id})")

        print("\n" + "=" * 100)
        print(f"\n✅ Total active iflows: {len(iflows)}")

        # Export to JSON for further processing
        output_file = Path(__file__).parent / "iflows.json"
        with open(output_file, "w") as f:
            json.dump(iflows, f, indent=2)
        print(f"📄 Details exported to: {output_file}\n")
        
        print("💡 Note: This lists iflows with recent message activity.")
        print("   For a complete list of ALL iflows, design-time API access is required.")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
