# WordPress.com MCP Publishing — Skill Reference

## What This Does
Automated publishing to any WordPress.com site via REST API v1.1 + MCP server. Works on ALL WordPress.com plans including Free and Personal.

## Setup (One-Time)

### 1. Create WordPress.com OAuth App
Go to: https://developer.wordpress.com/apps/new/

```
Name:         Your App Name
Website URL:  https://your-site.com
Redirect URI: http://localhost:3891/callback
Type:         Web
```

Note: Client ID + Client Secret.

### 2. Get OAuth Token
```bash
cd mcp-wordpress
node get-token.js --browser --client-id YOUR_ID --client-secret YOUR_SECRET
```
Approve in browser → token saved to `.wpcom_token`.

### 3. Register MCP Server
```bash
claude mcp add wordpress-com --scope project -- node /path/to/mcp-wordpress/server.js
```

### 4. Configure `.mcp.json`
```json
{
  "mcpServers": {
    "wordpress-com": {
      "type": "stdio",
      "command": "node",
      "args": ["mcp-wordpress/server.js"],
      "env": {
        "WPCOM_SITE_ID": "YOUR_SITE_ID_OR_DOMAIN",
        "WPCOM_TOKEN": "${WPCOM_TOKEN}"
      }
    }
  }
}
```

## Key Differences from wp-json/wp/v2

| Feature | wp-json/wp/v2 (self-hosted) | WordPress.com API v1.1 |
|---|---|---|
| **Plan requirement** | Business ($25/mo) | ALL plans (Free, Personal) |
| **Endpoint** | `your-site.com/wp-json/wp/v2/` | `public-api.wordpress.com/rest/v1.1/sites/SITE_ID/` |
| **Auth** | Application Passwords (Basic) | OAuth2 Bearer token |
| **Categories** | Must resolve IDs first | Pass names as CSV (auto-created) |
| **Tags** | Must resolve IDs first | Pass names as CSV (auto-created) |
| **Content** | JSON body | URL-encoded form body |

## API Endpoints Used

```
POST /sites/{id}/posts/new      — Create post or page
POST /sites/{id}/posts/{id}     — Update post
POST /sites/{id}/posts/{id}/delete — Trash post
GET  /sites/{id}/posts/{id}     — Get single post
GET  /sites/{id}/posts          — List posts
GET  /sites/{id}/categories     — List categories
POST /sites/{id}/categories/new — Create category
GET  /sites/{id}                — Site info
POST /sites/{id}/settings       — Update settings
```

## Token Storage

The OAuth token contains special characters (`@`, `$`, `^`, `!`) that get mangled by bash shell escaping. Always store in a file, never in shell variables.

- **`.wpcom_token`** — Raw token file (primary, read by both Python client and MCP server)
- **`.env`** — `WPCOM_TOKEN=...` (backup, may have escaping issues)
- Both the Python client (`src/apis/wordpress.py`) and MCP server (`mcp-wordpress/server.js`) read from `.wpcom_token` as fallback

## Replicating for a New Site

1. Create a new OAuth app (or reuse the same one — global scope works)
2. Run `node get-token.js --browser ...` and approve for the new site
3. Update `WPCOM_SITE_ID` in `.mcp.json` to the new site's numeric ID or domain
4. All tools automatically target the new site

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `invalid_token` | Shell mangled special chars | Read token from `.wpcom_token` file, not `.env` |
| `404 on /wp-json/wp/v2/` | Wrong API for WordPress.com | Use `public-api.wordpress.com/rest/v1.1/` |
| `400 Bad Request` on create | Content too large for form encoding | Use `urlencode()` with utf-8 encoding |
| `redirect_uri mismatch` | App redirect URL doesn't match | Update at developer.wordpress.com/apps/ |
| Browser doesn't open | Running in background process | Run `start "URL"` separately, then catch callback |
