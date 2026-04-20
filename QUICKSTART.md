# Quick Start Guide: List iflows from BTP Integration Suite

## Step 1: Configure BTP Credentials

1. Get your SAP BTP credentials from your service key or API client:
   - Client ID
   - Client Secret
   - OAuth Token URL
   - Base URL for Integration Suite

2. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and fill in your credentials:
   ```
   SAP_BTP_BASE_URL=https://your-tenant.hana.ondemand.com
   SAP_BTP_TOKEN_URL=https://your-auth.authentication.sap.hana.ondemand.com/oauth/token
   SAP_BTP_CLIENT_ID=your-client-id
   SAP_BTP_CLIENT_SECRET=your-client-secret
   ```

## Step 2: List All iflows

Run the helper script:
```bash
python3.11 list_iflows.py
```

This will:
- ✓ Connect to your BTP tenant
- ✓ Fetch all integration packages
- ✓ Fetch all integration artifacts (iflows, mappings, etc.)
- ✓ Filter and display all iflows
- 📄 Export results to `iflows.json`

## Step 3: Alternative - Use the MCP Server

If you want to use the full MCP server with all available tools:

```bash
python3.11 -m btp_mcp.server --transport stdio
```

Available tools:
- `ping_sap_btp()` - Verify connectivity
- `list_integration_packages()` - List all packages
- `list_artifacts()` - List artifacts (filter by package or type)
- `get_artifact_details()` - Get single artifact details
- `get_message_processing_logs()` - Get integration logs
- `get_custom_header_properties()` - Get message properties

## Troubleshooting

If you get a 404 error mentioning "Requested route":
- The runtime URL was used instead of the Cloud Integration tenant API host
- Check your BTP service key and use the correct API host for `SAP_BTP_BASE_URL`

If authentication fails:
- Verify client ID and secret are correct
- Ensure the API client has permissions for Integration Suite APIs
