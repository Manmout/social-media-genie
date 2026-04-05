#!/usr/bin/env node
/**
 * WordPress.com OAuth2 Token Helper
 *
 * Two modes:
 *   1. Browser flow (recommended):
 *      node get-token.js --browser
 *      → Opens browser for authorization → prints token
 *
 *   2. Password grant (quick, personal use only):
 *      node get-token.js --username YOU --password YOUR_APP_PASSWORD
 *      → Gets token directly (no browser)
 *
 * Prerequisites:
 *   1. Create an app at https://developer.wordpress.com/apps/new/
 *   2. Set redirect URI to: http://localhost:3891/callback
 *   3. Note your Client ID and Client Secret
 */

import http from "node:http";
import { URL } from "node:url";
import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ENV_PATH = resolve(__dirname, "..", ".env");

const REDIRECT_PORT = 3891;
const REDIRECT_URI = `http://localhost:${REDIRECT_PORT}/callback`;

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--client-id") opts.clientId = args[++i];
    else if (args[i] === "--client-secret") opts.clientSecret = args[++i];
    else if (args[i] === "--username") opts.username = args[++i];
    else if (args[i] === "--password") opts.password = args[++i];
    else if (args[i] === "--browser") opts.browser = true;
    else if (args[i] === "--help") opts.help = true;
  }
  return opts;
}

async function passwordGrant(clientId, clientSecret, username, password) {
  const resp = await fetch("https://public-api.wordpress.com/oauth2/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: "password",
      username,
      password,
    }),
  });

  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(`OAuth error: ${data.error_description || data.error || JSON.stringify(data)}`);
  }
  return data;
}

async function browserFlow(clientId, clientSecret) {
  return new Promise((resolveToken, reject) => {
    const authUrl =
      `https://public-api.wordpress.com/oauth2/authorize?` +
      `client_id=${clientId}&` +
      `redirect_uri=${encodeURIComponent(REDIRECT_URI)}&` +
      `response_type=code&` +
      `scope=global`;

    console.log("\n  Opening browser for authorization...\n");
    console.log(`  If browser doesn't open, visit:\n  ${authUrl}\n`);

    // Open browser
    const open =
      process.platform === "win32"
        ? "start"
        : process.platform === "darwin"
          ? "open"
          : "xdg-open";
    import("node:child_process").then(({ exec }) => {
      exec(`${open} "${authUrl}"`);
    });

    // Local server to catch redirect
    const server = http.createServer(async (req, res) => {
      const url = new URL(req.url, `http://localhost:${REDIRECT_PORT}`);

      if (url.pathname === "/callback") {
        const code = url.searchParams.get("code");
        if (!code) {
          res.writeHead(400);
          res.end("Missing authorization code");
          reject(new Error("No authorization code received"));
          server.close();
          return;
        }

        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(
          "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>" +
            "<h1>&#x2705; Authorization successful!</h1>" +
            "<p>You can close this tab and return to your terminal.</p>" +
            "</body></html>"
        );

        try {
          // Exchange code for token
          const tokenResp = await fetch(
            "https://public-api.wordpress.com/oauth2/token",
            {
              method: "POST",
              headers: { "Content-Type": "application/x-www-form-urlencoded" },
              body: new URLSearchParams({
                client_id: clientId,
                client_secret: clientSecret,
                code,
                grant_type: "authorization_code",
                redirect_uri: REDIRECT_URI,
              }),
            }
          );
          const data = await tokenResp.json();
          if (!tokenResp.ok) {
            throw new Error(data.error_description || data.error);
          }
          resolveToken(data);
        } catch (err) {
          reject(err);
        }

        server.close();
      }
    });

    server.listen(REDIRECT_PORT, () => {
      console.log(`  Waiting for authorization callback on port ${REDIRECT_PORT}...\n`);
    });

    // Timeout after 5 minutes
    setTimeout(() => {
      server.close();
      reject(new Error("Authorization timed out after 5 minutes"));
    }, 300_000);
  });
}

function saveToken(token, blogId, blogUrl) {
  // Append to .env
  if (existsSync(ENV_PATH)) {
    let env = readFileSync(ENV_PATH, "utf-8");
    // Replace existing or append
    if (env.includes("WPCOM_TOKEN=")) {
      env = env.replace(/WPCOM_TOKEN=.*/, `WPCOM_TOKEN=${token}`);
    } else {
      env += `\n# --- WordPress.com OAuth Token ---\nWPCOM_TOKEN=${token}\n`;
    }
    if (env.includes("WPCOM_SITE_ID=")) {
      env = env.replace(/WPCOM_SITE_ID=.*/, `WPCOM_SITE_ID=${blogId}`);
    } else {
      env += `WPCOM_SITE_ID=${blogId}\n`;
    }
    writeFileSync(ENV_PATH, env);
  } else {
    writeFileSync(
      ENV_PATH,
      `# --- WordPress.com OAuth Token ---\nWPCOM_TOKEN=${token}\nWPCOM_SITE_ID=${blogId}\n`
    );
  }
  console.log(`  Token saved to .env`);
  console.log(`  Blog: ${blogUrl} (ID: ${blogId})\n`);
}

async function main() {
  const opts = parseArgs();

  if (opts.help || (!opts.browser && !opts.username)) {
    console.log(`
  WordPress.com OAuth Token Helper

  First, create an app at: https://developer.wordpress.com/apps/new/
    - Name: Trend Signal MCP
    - Redirect URI: http://localhost:${REDIRECT_PORT}/callback
    - Type: Web

  Then run one of:

  Browser flow (recommended):
    node get-token.js --browser --client-id ID --client-secret SECRET

  Password grant (quick):
    node get-token.js --username YOU --password APP_PASSWORD --client-id ID --client-secret SECRET
`);
    process.exit(0);
  }

  if (!opts.clientId || !opts.clientSecret) {
    console.error("\n  Error: --client-id and --client-secret are required");
    console.error("  Create an app at: https://developer.wordpress.com/apps/new/\n");
    process.exit(1);
  }

  try {
    let data;
    if (opts.browser) {
      data = await browserFlow(opts.clientId, opts.clientSecret);
    } else {
      data = await passwordGrant(
        opts.clientId,
        opts.clientSecret,
        opts.username,
        opts.password
      );
    }

    console.log(`\n  ✅ Token obtained successfully!\n`);
    console.log(`  Access Token: ${data.access_token.substring(0, 20)}...`);
    console.log(`  Blog ID:      ${data.blog_id}`);
    console.log(`  Blog URL:     ${data.blog_url}\n`);

    saveToken(data.access_token, data.blog_id, data.blog_url);

  } catch (err) {
    console.error(`\n  ❌ Error: ${err.message}\n`);
    process.exit(1);
  }
}

main();
