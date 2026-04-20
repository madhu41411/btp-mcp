# Deploying BTP MCP Server to Render

This guide explains how to deploy your BTP MCP server to Render for public access.

## Prerequisites

- GitHub account with this repository pushed
- Render.com account (free tier available)
- BTP credentials (client ID and secret)

## Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: BTP MCP Server"
git remote add origin https://github.com/yourusername/btp-mcp.git
git push -u origin main
```

## Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub (easier for deployment)
3. Authorize Render to access your GitHub account

## Step 3: Create New Web Service

### Option A: Using render.yaml (Recommended)

1. Render will automatically detect `render.yaml`
2. Go to Dashboard → New → Web Service
3. Select your GitHub repository
4. Render will auto-fill settings from `render.yaml`
5. Click "Create Web Service"

### Option B: Manual Configuration

1. Dashboard → New → Web Service
2. Connect GitHub repository
3. Configure:
   - **Name:** `btp-mcp-server`
   - **Runtime:** Docker
   - **Region:** Oregon (free tier)
   - **Branch:** main
   - **Dockerfile Path:** `./Dockerfile`

## Step 4: Set Environment Variables

In Render Dashboard, go to your service → Environment:

Add these variables:

```
SAP_BTP_BASE_URL = https://dev-cpi-carr.it-cpi001.cfapps.eu10.hana.ondemand.com
SAP_BTP_TOKEN_URL = https://dev-cpi-carr.authentication.eu10.hana.ondemand.com/oauth/token
SAP_BTP_CLIENT_ID = your-client-id-here
SAP_BTP_CLIENT_SECRET = your-client-secret-here
SAP_BTP_API_PATH = /api/v1
API_KEY = your-secret-api-key-here (choose a strong password)
```

**Click "Save Changes"**

## Step 5: Deploy

Once you save environment variables, Render will automatically:
1. Build the Docker image
2. Start the container
3. Run health checks
4. Assign you a public URL

You'll see something like:
```
Your service is live at: https://btp-mcp-server.onrender.com
```

## Step 6: Test the Deployment

### Health Check

```bash
curl https://btp-mcp-server.onrender.com/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-20T12:00:00.000000",
  "service": "btp-mcp-server"
}
```

### Test API Access

```bash
curl https://btp-mcp-server.onrender.com/api/packages \
  -H "X-API-Key: your-secret-api-key-here"
```

## Step 7: Configure Claude Desktop

Edit Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "btp-mcp": {
      "command": "curl",
      "args": [
        "--silent",
        "--header", "X-API-Key: your-secret-api-key-here",
        "https://btp-mcp-server.onrender.com/api"
      ]
    }
  }
}
```

**Or use the HTTP transport directly:**

```json
{
  "mcpServers": {
    "btp-mcp": {
      "url": "https://btp-mcp-server.onrender.com",
      "headers": {
        "X-API-Key": "your-secret-api-key-here"
      }
    }
  }
}
```

## Available Endpoints

All endpoints require `X-API-Key` header (except `/health`):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (no auth) |
| `/api/ping` | GET | Test BTP connectivity |
| `/api/packages` | GET | List integration packages |
| `/api/artifacts` | GET | List integration artifacts |
| `/api/logs` | GET | Get message processing logs |

### Example Requests

**List packages:**
```bash
curl https://btp-mcp-server.onrender.com/api/packages?top=10 \
  -H "X-API-Key: your-api-key"
```

**Get logs (failed only):**
```bash
curl "https://btp-mcp-server.onrender.com/api/logs?status=FAILED&top=100" \
  -H "X-API-Key: your-api-key"
```

## Monitoring & Logs

### View Logs in Render

1. Dashboard → Your Service → Logs
2. Real-time logs show:
   - Deployment status
   - Container startup
   - Request logs
   - Errors

### Enable Debug Mode

Edit `http_server.py`:
```python
app.run(host='0.0.0.0', port=port, debug=True)
```

Then redeploy (push to GitHub and Render will auto-rebuild)

## Troubleshooting

### Service won't start

Check logs for errors:
- Missing environment variables
- Invalid BTP credentials
- Port binding issues

### 503 Service Unavailable

Health check is failing. Verify:
1. BTP credentials are correct
2. BTP tenant is accessible
3. API_KEY is set

### Authentication errors

Test API key:
```bash
curl https://your-service.onrender.com/api/packages \
  -H "X-API-Key: your-api-key" \
  -v
```

### Deployment timeout

Docker build takes time. Free tier may be slow. Check logs.

## Advanced Configuration

### Custom Domain

1. Dashboard → Your Service → Settings → Custom Domain
2. Point your domain's DNS to Render
3. SSL certificate auto-generated

### Auto-Deploy on Push

Already enabled! Just commit and push to GitHub.

### Scaling

Free tier:
- Auto-pauses after 15 mins of inactivity
- Limited CPU/RAM

Paid plans:
- Always on
- Better performance
- More scaling options

## Cost

- **Free Tier:** $0 (limited, auto-pauses after 15 mins)
- **Paid Tier:** ~$7/month (always on)

## Next Steps

1. ✅ Deploy to Render
2. ✅ Test health endpoint
3. ✅ Configure Claude Desktop
4. ✅ Start asking Claude about your iflows!

## Example Claude Prompt

```
Using the BTP MCP server, can you:
1. Check connectivity to SAP BTP
2. List all integration packages
3. Show me the failed messages from the last 24 hours
```

Claude will use your deployed MCP server to execute these queries!

## Support

- Render docs: https://render.com/docs
- MCP spec: https://modelcontextprotocol.io
- SAP BTP docs: https://help.sap.com/docs/cloud-integration

---

**Your service is now live and accessible to Claude and other MCP clients!** 🚀
