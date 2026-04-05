#!/usr/bin/env python3
"""
Tumblr OAuth1 Token Generator — 2-step flow (no localhost callback).

Step 1: py -3.13 get-tumblr-token.py --step1 --consumer-key KEY --consumer-secret SECRET
        → Opens browser, prints instructions. Copy the redirect URL.

Step 2: py -3.13 get-tumblr-token.py --step2 --verifier CODE
        → Exchanges verifier for access tokens, saves to .tumblr_token
"""

import argparse
import json
import os
import stat
import sys
import webbrowser
from pathlib import Path

from requests_oauthlib import OAuth1Session

TOKEN_FILE = Path(__file__).resolve().parent / ".tumblr_token"

REQUEST_TOKEN_URL = "https://www.tumblr.com/oauth/request_token"
AUTHORIZE_URL = "https://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.tumblr.com/oauth/access_token"
USER_INFO_URL = "https://api.tumblr.com/v2/user/info"


def load_tokens() -> dict:
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def save_tokens(data: dict):
    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def step1(consumer_key: str, consumer_secret: str):
    """Get request token and open authorization URL."""
    print("\n  [Step 1] Requesting token...")

    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret, callback_uri="http://localhost")
    response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    request_token = response["oauth_token"]
    request_token_secret = response["oauth_token_secret"]

    # Save request tokens for step 2
    save_tokens({
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "_request_token": request_token,
        "_request_token_secret": request_token_secret,
    })

    auth_url = f"{AUTHORIZE_URL}?oauth_token={request_token}"

    print(f"        Request token OK")
    print(f"\n  Opening browser...\n")
    webbrowser.open(auth_url)

    print(f"  After authorizing, Tumblr redirects you.")
    print(f"  Look at the URL bar — it will contain:")
    print(f"  ...?oauth_verifier=XXXXXXXXX#_=_")
    print(f"\n  Copy the oauth_verifier value, then run:\n")
    print(f"  py -3.13 get-tumblr-token.py --step2 --verifier PASTE_CODE_HERE\n")


def step2(verifier: str):
    """Exchange verifier for access tokens."""
    tokens = load_tokens()
    consumer_key = tokens.get("consumer_key", "")
    consumer_secret = tokens.get("consumer_secret", "")
    request_token = tokens.get("_request_token", "")
    request_token_secret = tokens.get("_request_token_secret", "")

    if not all([consumer_key, consumer_secret, request_token, request_token_secret]):
        print("\n  Error: Run --step1 first.\n")
        sys.exit(1)

    print("\n  [Step 2] Exchanging verifier for access token...")

    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=request_token,
        resource_owner_secret=request_token_secret,
        verifier=verifier,
    )
    response = oauth.fetch_access_token(ACCESS_TOKEN_URL)
    oauth_token = response["oauth_token"]
    oauth_token_secret = response["oauth_token_secret"]

    # Save final tokens (remove temp request tokens)
    save_tokens({
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "oauth_token": oauth_token,
        "oauth_token_secret": oauth_token_secret,
    })

    print(f"        Access token OK: {oauth_token[:16]}...")

    # Verify
    print("\n  Verifying with Tumblr API...")
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
    )
    resp = oauth.get(USER_INFO_URL)
    data = resp.json()

    if resp.status_code == 200 and "response" in data:
        user = data["response"]["user"]
        blogs = user.get("blogs", [])
        print(f"\n  {'=' * 40}")
        print(f"  Connected as: {user.get('name')}")
        for blog in blogs:
            primary = " *" if blog.get("primary") else ""
            print(f"    {blog.get('name')}.tumblr.com{primary} ({blog.get('posts', 0)} posts)")
        print(f"\n  4 tokens saved to .tumblr_token")
        print(f"  {'=' * 40}\n")
    else:
        print(f"\n  API {resp.status_code}: tokens saved but verify failed.\n")


def main():
    parser = argparse.ArgumentParser(description="Tumblr OAuth1 Token Generator")
    parser.add_argument("--step1", action="store_true", help="Start: get request token + open browser")
    parser.add_argument("--step2", action="store_true", help="Finish: exchange verifier for access token")
    parser.add_argument("--consumer-key", default=None)
    parser.add_argument("--consumer-secret", default=None)
    parser.add_argument("--verifier", default=None)
    args = parser.parse_args()

    if not args.step1 and not args.step2:
        print("\n  Usage:")
        print("    py -3.13 get-tumblr-token.py --step1 --consumer-key KEY --consumer-secret SECRET")
        print("    py -3.13 get-tumblr-token.py --step2 --verifier CODE\n")
        sys.exit(0)

    if args.step1:
        ck = args.consumer_key or load_tokens().get("consumer_key", "")
        cs = args.consumer_secret or load_tokens().get("consumer_secret", "")
        if not ck or not cs:
            print("\n  Error: --consumer-key and --consumer-secret required for step1.\n")
            sys.exit(1)
        step1(ck, cs)

    elif args.step2:
        if not args.verifier:
            print("\n  Error: --verifier required for step2.\n")
            sys.exit(1)
        step2(args.verifier)


if __name__ == "__main__":
    main()
