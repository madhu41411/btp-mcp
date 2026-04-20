# BTP Integration Suite - Web UI

A modern, interactive web interface for querying and managing integration flows in SAP BTP Integration Suite.

## Features

✨ **Chat-like Interface** - Ask natural language questions about your iflows
📊 **Statistics Dashboard** - View message processing statistics
📦 **Package Management** - Browse integration packages
🔍 **Error Tracking** - Monitor failed messages and errors
🚀 **Deployment Status** - Check which iflows are active
⚡ **Real-time Data** - Get fresh data from your BTP tenant

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/madhu/Downloads/btp-mcp
pip install -e ".[dev]"
pip install flask
```

### 2. Configure Credentials

Make sure your `.env` file has valid BTP credentials:

```bash
cat .env
```

Should contain:
```
SAP_BTP_BASE_URL=https://dev-cpi-carr.it-cpi001.cfapps.eu10.hana.ondemand.com
SAP_BTP_TOKEN_URL=https://dev-cpi-carr.authentication.eu10.hana.ondemand.com/oauth/token
SAP_BTP_CLIENT_ID=your-client-id
SAP_BTP_CLIENT_SECRET=your-client-secret
```

### 3. Start the Web Server

```bash
python3.11 app.py
```

You'll see:
```
Initializing BTP Integration Suite client...
✓ Client initialized successfully
🚀 Starting web server at http://localhost:5000
```

### 4. Open in Browser

Navigate to: **http://localhost:5000**

## Usage

### Asking Questions

Try asking natural language questions like:

- **"List all iflows"** - Shows all active integration flows
- **"Show statistics"** - Displays message processing stats
- **"List packages"** - Shows all integration packages
- **"Check deployment status"** - Shows active deployments
- **"Show errors"** - Lists failed messages
- **"Search for [name]"** - Find specific iflows

### API Endpoints

You can also use the HTTP API directly:

**Get all iflows:**
```bash
curl http://localhost:5000/api/iflows
```

**Get statistics:**
```bash
curl http://localhost:5000/api/stats
```

**Health check:**
```bash
curl http://localhost:5000/api/health
```

**Chat interface:**
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List all iflows"}'
```

## Architecture

### Backend (`app.py`)
- Flask web server
- BTP Integration Suite client integration
- Natural language query processing
- Statistics aggregation
- Error tracking

### Frontend (`templates/index.html`)
- Modern, responsive UI
- Chat-like conversation interface
- Real-time message streaming
- Data visualization
- Suggestion buttons

## Data Processing

The application processes queries by:

1. **Understanding Intent** - Analyzes user query keywords
2. **Fetching Data** - Retrieves message processing logs from BTP
3. **Extracting Information** - Parses iflow details from logs
4. **Formatting Response** - Presents data in easy-to-read format
5. **Displaying Results** - Shows results with suggestions for next questions

## What Information is Available

### iFlow Details
- Name and ID
- Package information
- Type (always INTEGRATION_FLOW)

### Statistics
- Total messages processed
- Status breakdown (COMPLETED, FAILED, ERROR, etc.)
- Message count per iflow

### Error Information
- Count of failed/errored messages
- Error details and timestamps
- Failed iflow names

### Package Information
- Package ID and name
- Number of iflows per package

## Limitations

⚠️ **Design-time APIs Not Available**
- Cannot list ALL iflows (only those with recent message activity)
- Cannot deploy new iflows via API
- Cannot modify iflow configurations

This is due to service key permissions. Only runtime monitoring APIs are accessible with current permissions.

## Troubleshooting

### "Failed to initialize client"
- Check `.env` file has correct credentials
- Verify BTP tenant URL is correct
- Ensure service key has runtime monitoring permissions

### No iflows showing up
- Make sure iflows have processed messages recently
- Run integration flows to generate message logs

### Connection timeout
- Check internet connection
- Verify BTP tenant is reachable
- Check firewall rules

## Advanced Usage

### Environment Variables

```bash
# Change port
FLASK_ENV=development FLASK_PORT=3000 python3.11 app.py

# Enable debug mode
FLASK_ENV=development python3.11 app.py
```

### Extending the Application

Add new query handlers in `app.py`:

```python
def process_query(user_query):
    query_lower = user_query.lower()
    
    if 'my_keyword' in query_lower:
        response["type"] = "custom"
        response["data"] = my_data
        response["summary"] = "My custom response"
    
    return response
```

## Files

```
btp-mcp/
├── app.py                      # Flask application
├── templates/
│   └── index.html             # Web UI frontend
├── list_iflows.py             # CLI script (if preferred)
├── src/
│   └── btp_mcp/
│       ├── client.py          # BTP API client
│       ├── server.py          # MCP server
│       └── config.py          # Configuration
└── .env                       # BTP credentials
```

## Support

For issues or questions:
1. Check the logs in terminal
2. Verify `.env` configuration
3. Test credentials with `list_iflows.py` script
4. Check BTP Integration Suite documentation

---

**Happy integrating!** 🚀
