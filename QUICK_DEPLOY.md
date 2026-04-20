# Docker + Render Quick Start

## TL;DR - 5 Steps to Deploy

### 1️⃣ Push to GitHub

```bash
cd /Users/madhu/Downloads/btp-mcp
git init
git add .
git commit -m "BTP MCP Server"
git remote add origin https://github.com/YOUR_USERNAME/btp-mcp.git
git push -u origin main
```

### 2️⃣ Go to Render.com

- Sign up: https://render.com/signup
- Authorize GitHub

### 3️⃣ Create Web Service

- Dashboard → New → Web Service
- Select your `btp-mcp` repository
- Render auto-reads `render.yaml` ✓

### 4️⃣ Add Environment Variables

Add these in Render Dashboard (Environment tab):

```
SAP_BTP_BASE_URL = https://dev-cpi-carr.it-cpi001.cfapps.eu10.hana.ondemand.com
SAP_BTP_TOKEN_URL = https://dev-cpi-carr.authentication.eu10.hana.ondemand.com/oauth/token
SAP_BTP_CLIENT_ID = your-client-id
SAP_BTP_CLIENT_SECRET = your-client-secret
SAP_BTP_API_PATH = /api/v1
API_KEY = generate-strong-password
```

Click **Save Changes** → Auto-deploys!

### 5️⃣ Test It Works

When deployment finishes, you get a URL like:
```
https://btp-mcp-server-xxxx.onrender.com
```

Test health check:
```bash
curl https://btp-mcp-server-xxxx.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-20T12:34:56.789012",
  "service": "btp-mcp-server"
}
```

---

## Files Already Created ✅

| File | Purpose |
|------|---------|
| `Dockerfile` | Container build config |
| `.dockerignore` | Excludes unnecessary files |
| `render.yaml` | Render deployment config |
| `http_server.py` | HTTP API server |
| `DEPLOY_RENDER.md` | Full deployment guide |

---

## Test the API

```bash
API_KEY="your-api-key"
SERVICE_URL="https://your-service.onrender.com"

# List packages
curl "$SERVICE_URL/api/packages" \
  -H "X-API-Key: $API_KEY"

# Get logs
curl "$SERVICE_URL/api/logs?status=FAILED" \
  -H "X-API-Key: $API_KEY"

# Get artifacts
curl "$SERVICE_URL/api/artifacts" \
  -H "X-API-Key: $API_KEY"
```

---

## Use with Claude

**File:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "btp-mcp": {
      "url": "https://your-service.onrender.com",
      "headers": {
        "X-API-Key": "your-api-key"
      }
    }
  }
}
```

Restart Claude Desktop → You're ready!

---

## Cost

- **Free:** $0 (pauses after 15 mins idle) ✓
- **Paid:** ~$7/month (always on)

---

## What Happens After You Deploy

1. GitHub detects code push
2. Render auto-builds Docker image
3. Container starts
4. Health check confirms it works
5. Assigned public URL
6. Live for 30 days (free tier, then redeploy)

**That's it!** Your BTP server is now accessible to Claude and other clients worldwide. 🌍🚀

---

## Need Help?

- Render logs: Dashboard → Logs tab
- Test endpoint: `curl SERVICE_URL/health`
- Check env vars: Dashboard → Environment tab
- See deployment history: Dashboard → Activity

Full guide: See [DEPLOY_RENDER.md](DEPLOY_RENDER.md)
